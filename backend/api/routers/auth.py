import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse 
from sqlalchemy.orm import Session

from api.deps import get_db
from services import google_fit_service
from db import crud

router = APIRouter(
    prefix="/auth/google",
    tags=["Authentication"]
)

@router.get("/login")
def auth_google_login():
    authorization_url, state = google_fit_service.get_google_auth_url()
    return RedirectResponse(authorization_url)

@router.get("/callback")
async def auth_google_callback(request: Request, db: Session = Depends(get_db)):
    if 'error' in request.query_params:
        error_details = request.query_params['error']
        return JSONResponse(status_code=400, content={"message": f"Authorization error: {error_details}"})
        
    try:
        credentials = google_fit_service.fetch_google_token(str(request.url))
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"Error fetching token: {e}"})

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"}
        )
    
    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content={"message": "Failed to fetch user data."})
        
    user_info = response.json()
    db_user = crud.create_or_update_user(
        db=db,
        google_id=user_info.get("sub"),
        email=user_info.get("email"),
        access_token=credentials.token,
        refresh_token=credentials.refresh_token
    )
    
    frontend_url = "http://localhost:3000"
    redirect_url = f"{frontend_url}?user_id={db_user.id}&email={db_user.email}"
    return RedirectResponse(url=redirect_url)