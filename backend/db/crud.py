from sqlalchemy.orm import Session
from . import models
from datetime import datetime

def get_user_by_google_id(db: Session, google_id: str):
    """ Searches for a user by their Google ID. """
    return db.query(models.User).filter(models.User.google_id == google_id).first()

def create_or_update_user(db: Session, google_id: str, email: str, access_token: str, refresh_token: str | None):
    """
    Creates a new user or updates tokens for an existing one.
    """
    db_user = get_user_by_google_id(db, google_id)
    
    if db_user:
        # User exists, update tokens
        db_user.access_token = access_token
        if refresh_token:
            # Refresh token is sent by Google only the first time,
            # so we update it only if we receive it.
            db_user.refresh_token = refresh_token
        db_user.email = email # in case it changes
    else:
        # User does not exist, create a new one
        db_user = models.User(
            google_id=google_id,
            email=email,
            access_token=access_token,
            refresh_token=refresh_token
        )
        db.add(db_user)
        
    db.commit()
    db.refresh(db_user)
    return db_user

def add_steps_data(db: Session, user_id: int, data: list[dict]): 
    """ Adds step entries for the given user. """
    objects_to_add = []
    for entry in data:
        db_entry = models.Steps(
            user_id=user_id,
            timestamp=entry["timestamp"],
            value=entry["value"]
        )
        objects_to_add.append(db_entry)
        
    db.bulk_save_objects(objects_to_add)

def add_heart_rate_data(db: Session, user_id: int, data: list[dict]):
    objects_to_add = [models.HeartRate(user_id=user_id, **entry) for entry in data]
    db.bulk_save_objects(objects_to_add)
    db.commit()

def add_sleep_data(db: Session, user_id: int, data: list[dict]):
    objects_to_add = [models.Sleep(user_id=user_id, **entry) for entry in data]
    db.bulk_save_objects(objects_to_add)
    db.commit()

def add_blood_pressure_data(db: Session, user_id: int, data: list[dict]):
    objects_to_add = [models.BloodPressure(user_id=user_id, **entry) for entry in data]
    db.bulk_save_objects(objects_to_add)
    db.commit()

def add_oxygen_saturation_data(db: Session, user_id: int, data: list[dict]):
    objects_to_add = [models.OxygenSaturation(user_id=user_id, **entry) for entry in data]
    db.bulk_save_objects(objects_to_add)
    db.commit()