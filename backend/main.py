from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from db import database, models
from api.routers import auth, data, sync

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Health Sync API!"}

app.include_router(auth.router)
app.include_router(data.router)
app.include_router(sync.router)