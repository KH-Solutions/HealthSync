from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):   
    # --- Application Variables ---
    API_TITLE: str = "Health Sync API"
    API_DESCRIPTION: str = "API for synchronizing health data from external services."
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # --- Database Variables ---
    DATABASE_URL: str

    # --- Google OAuth Variables ---
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    REDIRECT_URI: str
    GOOGLE_TOKEN_URI: str = "https://accounts.google.com/o/oauth2/token" #  URI for refreshing tokens

    # We set the default value to "0", so if the variable does not exist,
    # insecure mode will be disabled.
    OAUTHLIB_INSECURE_TRANSPORT: str = "0"

    # --- Google Fit Configuration ---
    SCOPES: list[str] = [
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
        "https://www.googleapis.com/auth/fitness.activity.read",
        "https://www.googleapis.com/auth/fitness.heart_rate.read",
        "https://www.googleapis.com/auth/fitness.sleep.read",
        "https://www.googleapis.com/auth/fitness.blood_pressure.read",
        "https://www.googleapis.com/auth/fitness.oxygen_saturation.read"
    ]
    
    # Pydantic configuration to load variables from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

settings = Settings()