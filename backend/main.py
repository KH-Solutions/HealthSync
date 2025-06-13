import os
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from starlette.requests import Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List
from pydantic import BaseModel, ConfigDict
from datetime import datetime as dt
from collections import defaultdict

# Imports from our db module that we created
from db import models, crud, database

# Load environment variables from the .env file
# This must be at the top so other modules can use them
load_dotenv()

# --- Application and Database Configuration ---

# This line creates tables defined in db/models.py in the database,
# but only if they do not already exist.
models.Base.metadata.create_all(bind=database.engine)

# FastAPI application initialization
app = FastAPI(
    title="Health Sync API",
    description="API for synchronizing health data from external services."
)

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # List of allowed origins
    allow_credentials=True,      # Allow cookies
    allow_methods=["*"],         # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],         # Allow all headers
)

# --- Google Authorization Configuration ---

# Get configuration data from the .env file
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Check if key environment variables are set
if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI]):
    raise ValueError("Missing key Google environment variables. Check the .env file")

# Scopes (permissions) we request from Google.
# For now, we only ask for basic profile information.
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "https://www.googleapis.com/auth/fitness.activity.read",    # Activity (steps, calories, distance)
    "https://www.googleapis.com/auth/fitness.heart_rate.read",  # Heart rate
    "https://www.googleapis.com/auth/fitness.sleep.read",       # Sleep
    "https://www.googleapis.com/auth/fitness.blood_pressure.read", # Blood pressure
    "https://www.googleapis.com/auth/fitness.oxygen_saturation.read" # Poziom tlenu
]

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
                "timestamp": datetime.fromtimestamp(int(p["startTimeNanos"]) / 1e9, tz=timezone.utc),
                "value": p["value"][0].get("fpVal")
            }
        },
        "blood_pressure": {
            "dataTypeName": "com.google.blood_pressure", 
            "model": models.BloodPressure,
            "crud_function": crud.add_blood_pressure_data,
            "parser": lambda p: {
                "timestamp": datetime.fromtimestamp(int(p["startTimeNanos"]) / 1e9, tz=timezone.utc),
                "systolic": p["value"][0].get("fpVal"),
                "diastolic": p["value"][1].get("fpVal")
            }
        },
    }
}

# We create a "Flow" object from the Google library.
# It manages the entire OAuth 2.0 authorization process.
flow = Flow.from_client_config(
    client_config={
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "redirect_uris": [REDIRECT_URI],
        }
    },
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)


# --- API Endpoints ---

@app.get("/")
def read_root():
    """ Main endpoint to check if the server is running. """
    return {"message": "Welcome to Health Sync API! The system is running correctly."}


@app.get("/auth/google/login", tags=["Authentication"])
def auth_google_login():
    """
    Step 1 of Authorization: Redirect to Google.
    
    This endpoint initiates the OAuth 2.0 authorization process by redirecting
    the user to the Google login and consent page.
    """
    authorization_url, state = flow.authorization_url(
        access_type="offline",       # Request refresh_token to be able to refresh access in the background
        include_granted_scopes="true",
        prompt="consent"             # Forces the consent screen to always show, to always get a refresh_token
    )
    return RedirectResponse(authorization_url)


@app.get("/auth/google/callback", tags=["Authentication"])
async def auth_google_callback(request: Request, db: Session = Depends(database.get_db)):
    """
    Step 2 of Authorization: Handle Google's response.
    
    This endpoint is called by Google after login. It captures the authorization code,
    exchanges it for tokens, fetches user data, and saves it to the database.
    """
    # Check if Google returned an error (e.g., user canceled login)
    if 'error' in request.query_params:
        error_details = request.query_params['error']
        return JSONResponse(status_code=400, content={"message": f"An error occurred during authorization: {error_details}"})
        
    authorization_response = str(request.url)
    try:
        # Exchange the authorization code for access tokens
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"Error while fetching token: {e}"})

    credentials = flow.credentials
    
    # Use the obtained access_token to fetch user data from the Google API
    user_info_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {credentials.token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(user_info_endpoint, headers=headers)
    
    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content={"message": "Failed to fetch user data from Google."})
        
    user_info = response.json()
    google_id = user_info.get("sub")  # "sub" is the standard field for the unique user ID in OpenID
    email = user_info.get("email")
    
    if not google_id or not email:
        return JSONResponse(status_code=400, content={"message": "Google response does not contain required ID or email address."})

    # Save or update the user in our database using a function from crud.py
    try:
        db_user = crud.create_or_update_user(
            db=db,
            google_id=google_id,
            email=email,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Error while saving to the database: {e}"})
    
    frontend_url = "http://localhost:3000"
    redirect_url_with_params = f"{frontend_url}?user_id={db_user.id}&email={db_user.email}"
    return RedirectResponse(url=redirect_url_with_params)

def parse_aggregate_response(response_json: dict, parser_func: callable) -> list[dict]:
    """Universal function to parse Google Fit aggregate responses."""
    parsed_data = []
    for bucket in response_json.get("bucket", []):
        timestamp = datetime.fromtimestamp(int(bucket["endTimeMillis"]) / 1000, tz=timezone.utc)
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                if point.get("value"):
                    parsed_point = parser_func(point)
                    if all(v is not None for v in parsed_point.values()):
                        parsed_data.append({"timestamp": timestamp, **parsed_point})
    return parsed_data

@app.post("/users/{user_id}/sync", tags=["Data Sync"])
async def sync_user_data(user_id: int, days: int = 7, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return JSONResponse(status_code=404, content={"message": "User not found."})
    
    access_token = db_user.access_token
    headers = {"Authorization": f"Bearer {access_token}"}
    
    end_time = dt.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    sync_results = {}
    
    async with httpx.AsyncClient() as client:
        # --- LOOP FOR AGGREGATED DATA (steps, heart_rate) ---
        aggregate_endpoint = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
        for data_key, config in DATA_TYPE_CONFIG["AGGREGATE"].items():
            db.query(config["model"]).filter(config["model"].user_id == user_id).delete()
            request_body = {
                "aggregateBy": [{"dataTypeName": config["dataTypeName"]}],
                "bucketByTime": {"durationMillis": 86400000},
                "startTimeMillis": int(start_time.timestamp() * 1000),
                "endTimeMillis": int(end_time.timestamp() * 1000)
            }
            response = await client.post(aggregate_endpoint, json=request_body, headers=headers)
            if response.status_code != 200:
                sync_results[data_key] = f"Error: {response.status_code}"
                continue
            parsed_data = parse_aggregate_response(response.json(), config["parser"])
            if parsed_data:
                config["crud_function"](db=db, user_id=user_id, data=parsed_data)
            sync_results[data_key] = f"Processed {len(parsed_data)} entries."

        # --- LOOP FOR RAW DATA (LIST) (oxygen, blood_pressure) ---
        list_endpoint_template = "https://www.googleapis.com/fitness/v1/users/me/dataSources/{data_source}/datasets/{start_ns}-{end_ns}"
        for data_key, config in DATA_TYPE_CONFIG["LIST"].items():
            db.query(config["model"]).filter(config["model"].user_id == user_id).delete()
            data_source_id = f"derived:{config['dataTypeName']}:com.google.android.gms:merged"
            endpoint_url = list_endpoint_template.format(
                data_source=data_source_id,
                start_ns=int(start_time.timestamp() * 1e9),
                end_ns=int(end_time.timestamp() * 1e9)
            )
            response = await client.get(endpoint_url, headers=headers)
            if response.status_code != 200:
                sync_results[data_key] = f"Error: {response.status_code}"
                continue
            raw_data = response.json().get("point", [])
            parsed_data = [config["parser"](point) for point in raw_data if point.get("value")]
            if parsed_data:
                config["crud_function"](db=db, user_id=user_id, data=parsed_data)
            sync_results[data_key] = f"Processed {len(parsed_data)} entries."
            
        # --- SLEEP HANDLING SECTION ---
        # db.query(models.Sleep).filter(models.Sleep.user_id == user_id).delete()  # TODO: Restore this line if you want to clear sleep data before sync
        sessions_endpoint = "https://www.googleapis.com/fitness/v1/users/me/sessions"
        params = {
            "startTime": start_time.isoformat(timespec='seconds') + "Z",
            "endTime": end_time.isoformat(timespec='seconds') + "Z",
            "activityType": 72  # Code for sleep
        }
        
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
                                parsed_sleep_segments.append({
                                    "start_time": dt.fromtimestamp(int(point["startTimeNanos"]) / 1e9, tz=timezone.utc),
                                    "end_time": dt.fromtimestamp(int(point["endTimeNanos"]) / 1e9, tz=timezone.utc),
                                    "value": point["value"][0]["intVal"]
                                })
            
            if parsed_sleep_segments:
                crud.add_sleep_data(db=db, user_id=user_id, data=parsed_sleep_segments)
            
            sync_results["sleep"] = f"Processed {len(parsed_sleep_segments)} sleep segments from {len(sleep_sessions)} sessions."

    db.commit()
    return {"message": "Synchronization completed.", "details": sync_results}


class StepData(BaseModel):
    timestamp: dt
    value: int
    
    model_config = ConfigDict(from_attributes=True)

@app.get("/users/{user_id}/data/steps", response_model=List[StepData], tags=["Data Retrieval"])
def get_steps_data(user_id: int, db: Session = Depends(database.get_db)):
    """
    Retrieves stored step data for the given user from the database.
    """
    steps = db.query(models.Steps).filter(models.Steps.user_id == user_id).order_by(models.Steps.timestamp).all()
    if not steps:
        return []
    return steps

class HeartRateData(BaseModel):
    timestamp: dt
    value: float 
    
    model_config = ConfigDict(from_attributes=True)

@app.get("/users/{user_id}/data/heart_rate", response_model=List[HeartRateData], tags=["Data Retrieval"])
def get_heart_rate_data(user_id: int, db: Session = Depends(database.get_db)):
    """
    Retrieves stored heart rate data for the given user from the database.
    """
    heart_rates = db.query(models.HeartRate).filter(models.HeartRate.user_id == user_id).order_by(models.HeartRate.timestamp).all()
    if not heart_rates:
        return []
    return heart_rates

class SleepSummary(BaseModel):
    data_available: bool
    total_duration_minutes: int | None = None
    start_time: dt | None = None
    end_time: dt | None = None

@app.get("/users/{user_id}/data/sleep/summary", response_model=SleepSummary, tags=["Data Retrieval"])
def get_sleep_summary(user_id: int, db: Session = Depends(database.get_db)):
    """
    Retrieves and analyzes sleep data for the user, returning a summary of the last night.
    """
    # 1. Find the latest sleep segment for the given user
    latest_segment = (
        db.query(models.Sleep)
        .filter(models.Sleep.user_id == user_id)
        .order_by(models.Sleep.end_time.desc())
        .first()
    )

    if not latest_segment:
        return SleepSummary(data_available=False)

    # 2. Based on the latest segment, estimate the entire session time.
    # We assume that a full sleep session does not last longer than 16 hours.
    session_end_time = latest_segment.end_time
    session_start_threshold = session_end_time - timedelta(hours=16)

    # 3. Retrieve all segments that belong to this last session.
    session_segments = (
        db.query(models.Sleep)
        .filter(
            models.Sleep.user_id == user_id,
            models.Sleep.start_time >= session_start_threshold,
            models.Sleep.end_time <= session_end_time
        )
        .all()
    )
    
    if not session_segments:
        # This situation should not occur if latest_segment was found, but it's a good safeguard
        return SleepSummary(data_available=False)

    # 4. Sum the duration of all segments that are actual sleep.
    total_sleep_duration = timedelta()
    sleep_phase_codes = [4, 5, 6]  # 4:light, 5:deep, 6:REM

    for segment in session_segments:
        if segment.value in sleep_phase_codes:
            duration = segment.end_time - segment.start_time
            total_sleep_duration += duration
    
    if total_sleep_duration.total_seconds() == 0:
        return SleepSummary(data_available=False)

    return SleepSummary(
        data_available=True,
        total_duration_minutes=int(total_sleep_duration.total_seconds() / 60)
    )

class DailySleepData(BaseModel):
    date: str
    total_duration_minutes: int

@app.get("/users/{user_id}/data/sleep", response_model=List[DailySleepData], tags=["Data Retrieval"])
def get_daily_sleep_data(user_id: int, db: Session = Depends(database.get_db)):
    """
    Returns a list of daily sleep summaries from the last 30 days for charting purposes.
    """
    # 1. Retrieve all sleep segments from the last 30 days
    time_threshold = dt.now(timezone.utc) - timedelta(days=30)
    all_segments = (
        db.query(models.Sleep)
        .filter(models.Sleep.user_id == user_id, models.Sleep.end_time > time_threshold)
        .order_by(models.Sleep.start_time)
        .all()
    )

    if not all_segments:
        return []

    # 2. Group segments by the day the user woke up
    # We use defaultdict to easily append to lists
    daily_segments = defaultdict(list)
    for segment in all_segments:
        # The key is the "wake up" date (end_time)
        day_key = segment.end_time.date().isoformat()
        daily_segments[day_key].append(segment)

    # 3. Process each group (each day) into a single entry
    daily_summaries = []
    sleep_phase_codes = [4, 5, 6]

    for day, segments in daily_segments.items():
        total_sleep_duration = timedelta()
        for segment in segments:
            if segment.value in sleep_phase_codes:
                duration = segment.end_time - segment.start_time
                total_sleep_duration += duration
        
        if total_sleep_duration.total_seconds() > 0:
            daily_summaries.append(
                DailySleepData(
                    date=day,
                    total_duration_minutes=int(total_sleep_duration.total_seconds() / 60)
                )
            )
    
    return sorted(daily_summaries, key=lambda x: x.date)