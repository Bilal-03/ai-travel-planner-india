"""Shared mapping from planner progress to user-visible research events."""

from __future__ import annotations

from app.models.trip import (
    ResearchEvent,
    ResearchEventStatus,
    ResearchEventType,
)


_STEP_EVENT_TYPES: dict[str, ResearchEventType] = {
    "starting": ResearchEventType.UNDERSTANDING_REQUEST,
    "accepted": ResearchEventType.UNDERSTANDING_REQUEST,
    "geocoding": ResearchEventType.SEARCHING,
    "trip_context": ResearchEventType.SEARCHING,
    "fetching_transport": ResearchEventType.FOUND_TRANSPORT,
    "fetching_places": ResearchEventType.FOUND_PLACES,
    "fetching_weather": ResearchEventType.SEARCHING,
    "planning": ResearchEventType.VALIDATING,
    "routing": ResearchEventType.VALIDATING,
    "validating": ResearchEventType.VALIDATING,
    "saving": ResearchEventType.UPDATED_PLAN,
    "ready": ResearchEventType.COMPLETED,
    "complete": ResearchEventType.COMPLETED,
    "cached": ResearchEventType.COMPLETED,
}


def event_for_progress(step: str, message: str) -> ResearchEvent:
    """Turn an internal planner milestone into a safe UI progress record."""

    return ResearchEvent(
        event_type=_STEP_EVENT_TYPES.get(step, ResearchEventType.SEARCHING),
        status=ResearchEventStatus.COMPLETE,
        message=message,
        metadata={"step": step},
    )


def event_for_failure(message: str) -> ResearchEvent:
    return ResearchEvent(
        event_type=ResearchEventType.FAILED,
        status=ResearchEventStatus.ERROR,
        message=message,
    )


def event_for_update(instruction: str) -> ResearchEvent:
    return ResearchEvent(
        event_type=ResearchEventType.UPDATED_PLAN,
        status=ResearchEventStatus.COMPLETE,
        message="Updated your plan and kept the change within the trip guardrails.",
        metadata={"instruction": instruction[:500]},
    )


def append_unique_events(
    existing: list[ResearchEvent], additions: list[ResearchEvent]
) -> list[ResearchEvent]:
    """Preserve the event history while avoiding duplicate replay entries."""

    events = list(existing)
    seen = {event.id for event in events}
    for event in additions:
        if event.id not in seen:
            events.append(event)
            seen.add(event.id)
    return events[-64:]
