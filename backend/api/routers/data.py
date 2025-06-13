from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, ConfigDict
from datetime import datetime as dt, timedelta, timezone
from collections import defaultdict

from api.deps import get_db
from db import models

router = APIRouter(
    prefix="/users/{user_id}/data",
    tags=["Data Retrieval"]
)

# --- Pydantic Schemas (API response models) ---
class StepData(BaseModel):
    timestamp: dt
    value: int
    model_config = ConfigDict(from_attributes=True)

class HeartRateData(BaseModel):
    timestamp: dt
    value: float
    model_config = ConfigDict(from_attributes=True)

class SleepSummary(BaseModel):
    data_available: bool
    total_duration_minutes: int | None = None

class DailySleepData(BaseModel):
    date: str
    total_duration_minutes: int

# --- Endpoints ---
@router.get("/steps", response_model=List[StepData])
def get_steps_data(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves step data saved in the database for the given user, sorted by time.
    """
    return db.query(models.Steps).filter(models.Steps.user_id == user_id).order_by(models.Steps.timestamp).all()

@router.get("/heart_rate", response_model=List[HeartRateData])
def get_heart_rate_data(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves heart rate data saved in the database for the given user, sorted by time.
    """
    return db.query(models.HeartRate).filter(models.HeartRate.user_id == user_id).order_by(models.HeartRate.timestamp).all()

@router.get("/sleep/summary", response_model=SleepSummary)
def get_sleep_summary(user_id: int, db: Session = Depends(get_db)):
    """
    Returns a summary of the last night's sleep.
    Finds the last recorded segment and reconstructs the entire last session based on it.
    """
    latest_segment = db.query(models.Sleep).filter(models.Sleep.user_id == user_id).order_by(models.Sleep.end_time.desc()).first()
    if not latest_segment:
        return SleepSummary(data_available=False)

    session_end_time = latest_segment.end_time
    session_start_threshold = session_end_time - timedelta(hours=16)

    session_segments = db.query(models.Sleep).filter(
        models.Sleep.user_id == user_id,
        models.Sleep.start_time >= session_start_threshold,
        models.Sleep.end_time <= session_end_time
    ).all()
    
    if not session_segments:
        return SleepSummary(data_available=False)

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

@router.get("/sleep", response_model=List[DailySleepData])
def get_daily_sleep_data(user_id: int, db: Session = Depends(get_db)):
    """
    Returns a list of daily sleep summaries from the last 30 days for charting purposes.
    """
    time_threshold = dt.now(timezone.utc) - timedelta(days=30)
    all_segments = db.query(models.Sleep).filter(models.Sleep.user_id == user_id, models.Sleep.end_time > time_threshold).order_by(models.Sleep.start_time).all()
    if not all_segments:
        return []

    daily_segments = defaultdict(list)
    for segment in all_segments:
        day_key = segment.end_time.date().isoformat()
        daily_segments[day_key].append(segment)

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