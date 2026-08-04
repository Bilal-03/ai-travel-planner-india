"""Account, session, and explicit preference-memory contracts for Phase 6."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.trip import (
    AccommodationPreference,
    DietaryPreference,
    TripPace,
    TransportMode,
)


class Account(BaseModel):
    id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    is_anonymous: bool = True
    memory_enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AccountSession(BaseModel):
    access_token: str
    expires_at: datetime
    account: Account


class AccountRegistrationRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_email_shape(self) -> "AccountRegistrationRequest":
        if "@" not in self.email or self.email.startswith("@") or self.email.endswith("@"):
            raise ValueError("Enter a valid email address")
        return self


class PreferenceMemory(BaseModel):
    """Only preferences the traveller explicitly saved are represented here."""

    memory_enabled: bool = True
    preferred_transport: Optional[TransportMode] = None
    hotel_category: Optional[AccommodationPreference] = None
    typical_budget_min: Optional[int] = Field(None, ge=0, le=1_000_000)
    typical_budget_max: Optional[int] = Field(None, ge=0, le=1_000_000)
    dietary_preference: Optional[DietaryPreference] = None
    travel_pace: Optional[TripPace] = None
    accessibility_requirements: Optional[str] = Field(None, max_length=500)
    preferred_departure_times: list[str] = Field(default_factory=list, max_length=8)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_budget_range(self) -> "PreferenceMemory":
        if (
            self.typical_budget_min is not None
            and self.typical_budget_max is not None
            and self.typical_budget_min > self.typical_budget_max
        ):
            raise ValueError("Typical budget minimum cannot exceed maximum")
        return self


class PreferenceMemoryUpdate(BaseModel):
    memory_enabled: Optional[bool] = None
    preferred_transport: Optional[TransportMode] = None
    hotel_category: Optional[AccommodationPreference] = None
    typical_budget_min: Optional[int] = Field(None, ge=0, le=1_000_000)
    typical_budget_max: Optional[int] = Field(None, ge=0, le=1_000_000)
    dietary_preference: Optional[DietaryPreference] = None
    travel_pace: Optional[TripPace] = None
    accessibility_requirements: Optional[str] = Field(None, max_length=500)
    preferred_departure_times: Optional[list[str]] = Field(None, max_length=8)


class SavedTripSummary(BaseModel):
    id: str
    kind: str
    origin: str
    destination: str
    start_date: str
    end_date: str
    created_at: str

