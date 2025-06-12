import os
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from starlette.requests import Request
from sqlalchemy.orm import Session

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
    "openid"
]

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
    
    # Return a response confirming success
    return JSONResponse(
        status_code=200,
        content={
            "message": "User successfully logged in and saved to the database.",
            "user_id_internal": db_user.id,
            "email": db_user.email
        }
    )