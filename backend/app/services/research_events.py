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


def event_for_place_update(action: str, place_name: str, day_number: int | None = None) -> ResearchEvent:
    """Create a concise workspace checkpoint for saved-place mutations."""

    messages = {
        "saved": f"Saved {place_name} to your trip workspace.",
        "removed": f"Removed {place_name} from Saved Places; scheduled visits stay intact.",
        "added": f"Added {place_name} to day {day_number or '?'} and rechecked its timing and budget.",
    }
    return ResearchEvent(
        event_type=ResearchEventType.UPDATED_PLAN,
        status=ResearchEventStatus.COMPLETE,
        message=messages.get(action, f"Updated your saved places with {place_name}."),
        metadata={"action": action, "place_name": place_name, **({"day_number": day_number} if day_number else {})},
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
