from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

from core.config import settings
from db import models

flow = Flow.from_client_config(
    client_config={
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": settings.GOOGLE_TOKEN_URI,
            "redirect_uris": [settings.REDIRECT_URI],
        }
    },
    scopes=settings.SCOPES,
    redirect_uri=settings.REDIRECT_URI
)

def get_google_auth_url():
    """Returns the Google authorization URL."""
    return flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

def fetch_google_token(authorization_response: str) -> Credentials:
    """Exchanges the authorization code for tokens."""
    flow.fetch_token(authorization_response=authorization_response)
    return flow.credentials

def get_and_refresh_credentials(db: Session, user: models.User) -> Credentials | None:
    """
    Reconstructs the Credentials object from the database and refreshes the token if necessary.
    Saves the new token back to the database.
    """
    credentials = Credentials(
        token=user.access_token,
        refresh_token=user.refresh_token,
        token_uri=settings.GOOGLE_TOKEN_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=settings.SCOPES
    )

    # Check if the token is valid. If not or expired, refresh it.
    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            print(f"Token for user {user.id} has expired. Refreshing...")
            try:
                # This is the moment when a request is sent to Google for a new token
                credentials.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token for user {user.id}: {e}")
                # In production, you might mark the user as requiring re-authorization here.
                return None
            
            # After refreshing, save the NEW access_token to the database.
            # The refresh token usually stays the same, but update it just in case.
            user.access_token = credentials.token
            user.refresh_token = credentials.refresh_token
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Successfully refreshed token for user {user.id}")
        else:
            # No refresh token or token is not expired but invalid.
            # This indicates a problem, e.g., user revoked access in Google.
            print(f"Cannot refresh token for user {user.id}. Re-authentication needed.")
            return None

    return credentials
