"""Contracts for the prompt-first trip planning conversation."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.models.trip import TransportMode, TripRequest


QuestionInput = Literal["choice", "text", "date_range", "number"]
ClarificationStatus = Literal["questions", "ready"]


class ClarificationOption(BaseModel):
    id: str = Field(..., min_length=1, max_length=40)
    label: str = Field(..., min_length=1, max_length=140)
    description: str | None = Field(None, max_length=240)


class ClarificationQuestion(BaseModel):
    id: str = Field(..., min_length=1, max_length=60)
    prompt: str = Field(..., min_length=3, max_length=300)
    input_type: QuestionInput = "choice"
    options: list[ClarificationOption] = Field(default_factory=list, max_length=4)
    allow_custom: bool = False


class PlannerAnswer(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=60)
    option_id: str | None = Field(None, max_length=40)
    answer: str = Field(..., min_length=1, max_length=500)


class PlanningBrief(BaseModel):
    origin: str | None = Field(None, max_length=120)
    destination: str | None = Field(None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    budget: int | None = Field(None, ge=1_000, le=1_000_000)
    members: int | None = Field(None, ge=1, le=40)
    transport_mode: TransportMode | None = None
    planning_notes: str = Field("", max_length=4_000)

    def complete(self) -> bool:
        return all((
            self.origin,
            self.destination,
            self.start_date,
            self.end_date,
            self.budget,
            self.members,
        ))


class PlannerClarificationRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2_000)
    answers: list[PlannerAnswer] = Field(default_factory=list, max_length=12)


class PlannerClarificationResponse(BaseModel):
    status: ClarificationStatus
    brief: PlanningBrief
    questions: list[ClarificationQuestion] = Field(default_factory=list, max_length=3)
    trip_request: TripRequest | None = None
