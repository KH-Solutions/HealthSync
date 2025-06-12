from sqlalchemy.orm import Session
from . import models

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