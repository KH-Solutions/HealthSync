from google_auth_oauthlib.flow import Flow
from core.config import settings

flow = Flow.from_client_config(
    client_config={
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "redirect_uris": [settings.REDIRECT_URI],
        }
    },
    scopes=settings.SCOPES,
    redirect_uri=settings.REDIRECT_URI
)

def get_google_auth_url():
    return flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

def fetch_google_token(authorization_response: str):
    flow.fetch_token(authorization_response=authorization_response)
    return flow.credentials