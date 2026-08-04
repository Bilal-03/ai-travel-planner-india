"""Prompt-first planning conversation endpoint."""

from fastapi import APIRouter, Depends

from app.api.trips import generation_rate_limit
from app.models.planner import PlannerClarificationRequest, PlannerClarificationResponse
from app.services.prompt_planner import clarify_planner

router = APIRouter(prefix="/api/planner", tags=["planner"])


@router.post("/clarify", response_model=PlannerClarificationResponse)
async def clarify_trip_prompt(
    request: PlannerClarificationRequest,
    _: None = Depends(generation_rate_limit),
):
    return await clarify_planner(request)
