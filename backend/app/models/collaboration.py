"""Contracts for sharing, collaboration history, and privacy-safe analytics."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TripKind(StrEnum):
    SINGLE = "single"
    MULTI_CITY = "multi_city"


class CollaborationRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class ShareLinkCreateRequest(BaseModel):
    role: CollaborationRole = CollaborationRole.VIEWER
    invite_email: str | None = Field(default=None, max_length=320)
    expires_in_hours: int = Field(default=168, ge=1, le=24 * 30)


class ShareLinkResponse(BaseModel):
    id: str
    trip_id: str
    kind: TripKind
    role: CollaborationRole
    share_url: str
    invite_email: str | None = None
    expires_at: datetime
    revoked_at: datetime | None = None


class CollaboratorInviteRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    role: CollaborationRole = CollaborationRole.VIEWER


class CollaboratorResponse(BaseModel):
    id: str
    trip_id: str
    kind: TripKind
    email: str
    role: CollaborationRole
    created_at: datetime


class TripVersionResponse(BaseModel):
    id: str
    trip_id: str
    kind: TripKind
    version: int
    action: str
    actor_id: str | None
    created_at: datetime
    snapshot: dict[str, Any] | None = None


class TripActivityResponse(BaseModel):
    id: str
    trip_id: str
    kind: TripKind
    action: str
    actor_id: str | None
    version: int | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AnalyticsEventRequest(BaseModel):
    event: str = Field(..., min_length=3, max_length=64)
    trip_id: str | None = Field(default=None, max_length=64)
    kind: TripKind | None = None
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TripCopyRequest(BaseModel):
    kind: TripKind | None = None
