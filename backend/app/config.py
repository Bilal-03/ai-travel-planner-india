"""
Application configuration — loads from environment variables with sensible defaults.
All free-tier API keys are optional; the app degrades gracefully when they're missing.
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # --- LLM ---
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"

    # --- Transport ---
    skyscanner_rapidapi_key: Optional[str] = None
    railradar_api_key: Optional[str] = None

    # --- Media ---
    unsplash_access_key: Optional[str] = None

    # --- Weather ---
    openweathermap_api_key: Optional[str] = None

    # --- Database ---
    database_url: Optional[str] = None

    # --- Cache ---
    upstash_redis_url: Optional[str] = Field(default=None, validation_alias="UPSTASH_REDIS_REST_URL")
    upstash_redis_token: Optional[str] = Field(default=None, validation_alias="UPSTASH_REDIS_REST_TOKEN")

    # --- Durable trip jobs ---
    trip_job_secret: Optional[str] = Field(default=None, validation_alias="TRIP_JOB_SECRET")

    # --- App ---
    frontend_url: str = "http://localhost:3000"
    backend_port: int = 8000

    # --- Rate limits (requests per second for public APIs) ---
    nominatim_rps: float = 1.0
    overpass_rps: float = 1.0
    osrm_rps: float = 1.0

    model_config = {
        "env_file": [".env", "../.env"],  # works from backend/ or root
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
