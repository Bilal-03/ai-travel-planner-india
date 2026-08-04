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

    # --- Provider gateway ---
    # Defaults preserve the current integrations. Unsupported live choices
    # fail closed and let the service-level fallback respond safely.
    flight_provider: str = Field(default="legacy", validation_alias="FLIGHT_PROVIDER")
    places_provider: str = Field(default="overpass", validation_alias="PLACES_PROVIDER")
    routes_provider: str = Field(default="osrm", validation_alias="ROUTES_PROVIDER")
    rail_provider: str = Field(default="legacy", validation_alias="RAIL_PROVIDER")
    weather_provider: str = Field(default="openweather", validation_alias="WEATHER_PROVIDER")
    provider_timeout_seconds: float = Field(default=20.0, ge=0.1, le=120, validation_alias="PROVIDER_TIMEOUT_SECONDS")
    provider_max_retries: int = Field(default=1, ge=0, le=5, validation_alias="PROVIDER_MAX_RETRIES")
    provider_retry_backoff_seconds: float = Field(default=0.25, ge=0, le=30, validation_alias="PROVIDER_RETRY_BACKOFF_SECONDS")
    provider_circuit_failure_threshold: int = Field(default=3, ge=1, le=20, validation_alias="PROVIDER_CIRCUIT_FAILURE_THRESHOLD")
    provider_circuit_cooldown_seconds: float = Field(default=30.0, ge=0, le=3600, validation_alias="PROVIDER_CIRCUIT_COOLDOWN_SECONDS")

    # --- Media ---
    unsplash_access_key: Optional[str] = None

    # --- Weather ---
    openweathermap_api_key: Optional[str] = None

    # --- Database ---
    database_url: Optional[str] = None

    # --- Cache ---
    upstash_redis_url: Optional[str] = Field(default=None, validation_alias="UPSTASH_REDIS_REST_URL")
    upstash_redis_token: Optional[str] = Field(default=None, validation_alias="UPSTASH_REDIS_REST_TOKEN")
    require_redis: bool = Field(default=False, validation_alias="REQUIRE_REDIS")

    # --- Durable trip jobs ---
    trip_job_secret: Optional[str] = Field(default=None, validation_alias="TRIP_JOB_SECRET")

    # --- Production hardening ---
    environment: str = Field(default="development", validation_alias="APP_ENV")
    require_durable_storage: bool = Field(default=False, validation_alias="REQUIRE_DURABLE_STORAGE")
    max_request_body_bytes: int = Field(
        default=1_000_000,
        ge=16_384,
        le=10_000_000,
        validation_alias="MAX_REQUEST_BODY_BYTES",
    )
    analytics_hash_salt: str = Field(default="yatraai-local-analytics-salt", validation_alias="ANALYTICS_HASH_SALT")

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

    @property
    def is_production(self) -> bool:
        return self.environment.strip().casefold() in {"production", "prod"}


settings = Settings()
