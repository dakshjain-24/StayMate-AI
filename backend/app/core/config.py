from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # APP
    app_name: str = "StayMate AI"
    app_env: str = "development"


    # DATABASE
    database_url: str = (
        "postgresql+psycopg://"
        "staymate:staymate@localhost:5432/staymate"
    )


    # GEMINI
    gemini_api_key: str = ""
    gemini_chat_model: str = ("gemini-3.5-flash-lite")
    gemini_embedding_model: str = ("gemini-embedding-001")


    # HOTEL
    default_hotel_id: int = 1


    # FRONTEND / CORS
    frontend_origin: str = "http://localhost:5173"


    # EMAIL / RESEND
    resend_api_key: str = ""
    email_from: str = "StayMate <onboarding@resend.dev>"


    # HOTEL DEPARTMENT EMAILS
    housekeeping_email: str = ""
    maintenance_email: str = ""
    room_service_email: str = ""
    front_desk_email: str = ""


    # OTP SECURITY
    otp_secret: str = ""


    # STAFF JWT AUTH
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480


    # PYDANTIC SETTINGS
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()