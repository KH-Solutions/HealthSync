import httpx
import uuid
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime as dt, timedelta, timezone
from dateutil.parser import isoparse

from api.deps import get_db
from db import models, crud

from api.routers.data import get_steps_data, get_heart_rate_data, get_sleep_summary

router = APIRouter(
    tags=["Synchronization & Export"]
)

DATA_TYPE_CONFIG = {
    "AGGREGATE": {
        "steps": {
            "dataTypeName": "com.google.step_count.delta",
            "model": models.Steps,
            "crud_function": crud.add_steps_data,
            "parser": lambda p: {"value": p["value"][0].get("intVal")}
        },
        "heart_rate": {
            "dataTypeName": "com.google.heart_rate.bpm",
            "model": models.HeartRate,
            "crud_function": crud.add_heart_rate_data,
            "parser": lambda p: {"value": p["value"][0].get("fpVal")}
        },
    },
    "LIST": {
        "oxygen_saturation": {
            "dataTypeName": "com.google.oxygen_saturation",
            "model": models.OxygenSaturation,
            "crud_function": crud.add_oxygen_saturation_data,
            "parser": lambda p: {
                "timestamp": dt.fromtimestamp(int(p["startTimeNanos"]) / 1e9, tz=timezone.utc),
                "value": p["value"][0].get("fpVal")
            }
        },
        "blood_pressure": {
            "dataTypeName": "com.google.blood_pressure",
            "model": models.BloodPressure,
            "crud_function": crud.add_blood_pressure_data,
            "parser": lambda p: {
                "timestamp": dt.fromtimestamp(int(p["startTimeNanos"]) / 1e9, tz=timezone.utc),
                "systolic": p["value"][0].get("fpVal"),
                "diastolic": p["value"][1].get("fpVal")
            }
        },
    }
}

# --- Helper functions ---
def parse_aggregate_response(response_json: dict, parser_func: callable) -> list[dict]:
    """Universal function for parsing aggregated responses from Google Fit."""
    parsed_data = []
    for bucket in response_json.get("bucket", []):
        timestamp = dt.fromtimestamp(int(bucket["endTimeMillis"]) / 1000, tz=timezone.utc)
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                if point.get("value"):
                    parsed_point = parser_func(point)
                    if all(v is not None for v in parsed_point.values()):
                        parsed_data.append({"timestamp": timestamp, **parsed_point})
    return parsed_data

# --- Endpoints ---
@router.post("/users/{user_id}/sync")
async def sync_user_data(
    user_id: int, 
    days: int = 30, 
    db: Session = Depends(get_db),
    exclude: Optional[List[str]] = Query(None)
):
    """
    Starts data synchronization. You can exclude certain data types
    using the 'exclude' query parameter, e.g. ?exclude=sleep
    """
    exclude = exclude or []
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return JSONResponse(status_code=404, content={"message": "User not found."})
    
    access_token = db_user.access_token
    headers = {"Authorization": f"Bearer {access_token}"}
    end_time = dt.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    sync_results = {}
    
    async with httpx.AsyncClient() as client:
        # Loops for AGGREGATE and LIST data
        for data_category, data_configs in DATA_TYPE_CONFIG.items():
            endpoint_template = ""
            if data_category == "AGGREGATE":
                endpoint_template = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
            elif data_category == "LIST":
                endpoint_template = "https://www.googleapis.com/fitness/v1/users/me/dataSources/{data_source}/datasets/{start_ns}-{end_ns}"

            for data_key, config in data_configs.items():
                if data_key in exclude:
                    sync_results[data_key] = "Skipped on request."
                    continue
                
                db.query(config["model"]).filter(config["model"].user_id == user_id).delete()
                
                if data_category == "AGGREGATE":
                    request_body = {
                        "aggregateBy": [{"dataTypeName": config["dataTypeName"]}],
                        "bucketByTime": {"durationMillis": 86400000},
                        "startTimeMillis": int(start_time.timestamp() * 1000),
                        "endTimeMillis": int(end_time.timestamp() * 1000)
                    }
                    response = await client.post(endpoint_template, json=request_body, headers=headers)
                else: # data_category == "LIST"
                    data_source_id = f"derived:{config['dataTypeName']}:com.google.android.gms:merged"
                    endpoint_url = endpoint_template.format(data_source=data_source_id, start_ns=int(start_time.timestamp() * 1e9), end_ns=int(end_time.timestamp() * 1e9))
                    response = await client.get(endpoint_url, headers=headers)
                
                if response.status_code != 200:
                    sync_results[data_key] = f"Error: {response.status_code}"
                    continue
                
                if data_category == "AGGREGATE":
                    parsed_data = parse_aggregate_response(response.json(), config["parser"])
                else: # data_category == "LIST"
                    raw_data = response.json().get("point", [])
                    parsed_data = [config["parser"](point) for point in raw_data if point.get("value")]
                
                if parsed_data:
                    config["crud_function"](db=db, user_id=user_id, data=parsed_data)
                sync_results[data_key] = f"Processed {len(parsed_data)} entries."
        
        # Section for sleep (handled separately)
        if "sleep" not in exclude:
            # db.query(models.Sleep).filter(models.Sleep.user_id == user_id).delete() // TODO: Uncomment if you want to clear sleep data before sync
            sessions_endpoint = "https://www.googleapis.com/fitness/v1/users/me/sessions"
            params = {"startTime": start_time.isoformat(timespec='seconds') + "Z", "endTime": end_time.isoformat(timespec='seconds') + "Z", "activityType": 72}
            response = await client.get(sessions_endpoint, headers=headers, params=params)
            
            if response.status_code != 200:
                sync_results["sleep"] = f"Error: {response.status_code}, Details: {response.text}"
            else:
                sleep_sessions = response.json().get("session", [])
                parsed_sleep_segments = []
                for session in sleep_sessions:
                    for dataset in session.get("dataset", []):
                        if "sleep.segment" in dataset.get("dataSourceId", ""):
                            for point in dataset.get("point", []):
                                if point.get("value") and point["value"][0].get("intVal"):
                                    parsed_sleep_segments.append({"start_time": dt.fromtimestamp(int(point["startTimeNanos"]) / 1e9, tz=timezone.utc), "end_time": dt.fromtimestamp(int(point["endTimeNanos"]) / 1e9, tz=timezone.utc), "value": point["value"][0]["intVal"]})
                if parsed_sleep_segments:
                    crud.add_sleep_data(db=db, user_id=user_id, data=parsed_sleep_segments)
                sync_results["sleep"] = f"Processed {len(parsed_sleep_segments)} sleep segments from {len(sleep_sessions)} sessions."
        else:
            sync_results["sleep"] = "Skipped on request."

    db.commit()
    return {"message": "Synchronization completed.", "details": sync_results}


# --- HL7/JSON export logic ---
def create_msh_segment():
    return {"segment": "MSH", "sending_application": "HealthSyncApp", "sending_facility": "HealthSyncFacility", "datetime_of_message": dt.now(timezone.utc).strftime('%Y%m%d%H%M%S'), "message_type": "ORU^R01", "message_control_id": str(uuid.uuid4()), "processing_id": "P", "version_id": "2.3"}

def create_pid_segment(user: models.User):
    return {"segment": "PID", "patient_id": user.id, "external_patient_id": user.google_id, "patient_name": "User^Anonymized", "patient_email": user.email}

def create_obx_segment(seq_id: int, obs_id: str, obs_text: str, value: any, unit: str, timestamp: dt):
    return {"segment": "OBX", "set_id": seq_id, "value_type": "NM", "observation_identifier": f"{obs_id}^{obs_text}", "observation_value": str(value), "units": unit, "observation_result_status": "F", "observation_datetime": timestamp.strftime('%Y%m%d%H%M%S')}

@router.get("/users/{user_id}/export/hl7")
def export_user_data_as_hl7_json(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"message": "User not found."})

    hl7_message = [create_msh_segment(), create_pid_segment(user)]
    obx_sequence_id = 1

    # Steps
    for entry in get_steps_data(user_id=user_id, db=db)[-7:]:
        hl7_message.append(create_obx_segment(obx_sequence_id, "88942-2", "Number of steps in 24 hour Measured", entry.value, "steps", entry.timestamp))
        obx_sequence_id += 1
    # Heart rate
    for entry in get_heart_rate_data(user_id=user_id, db=db)[-10:]:
        hl7_message.append(create_obx_segment(obx_sequence_id, "8867-4", "Heart rate", entry.value, "bpm", entry.timestamp))
        obx_sequence_id += 1
    # Sleep
    sleep_summary = get_sleep_summary(user_id=user_id, db=db)
    if sleep_summary.data_available and sleep_summary.total_duration_minutes is not None:
        # We use now() as timestamp, because the summary does not have a specific time
        hl7_message.append(create_obx_segment(obx_sequence_id, "2482-2", "Sleep duration", sleep_summary.total_duration_minutes, "min", dt.now(timezone.utc)))
        obx_sequence_id += 1
        
    return JSONResponse(content={"hl7_message": hl7_message})