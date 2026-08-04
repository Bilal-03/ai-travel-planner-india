"""Deterministic itinerary scheduling and scoped refinement primitives.

The planner may use Gemini for language and explanations, but this module owns
the parts that must remain reproducible: which reviewed candidates are selected,
when they occur, whether a day is feasible, and whether a change is scoped.
It deliberately uses a small deterministic scheduler instead of introducing a
large optimisation dependency for the current single-destination product.
"""

from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Any, Iterable, Mapping, Optional

from pydantic import BaseModel, Field

from app.models.trip import (
    GeoPoint,
    TripIntent,
    TripPace,
    TransportOption,
    TravelVibe,
)
from app.services.geocoding import haversine_distance

DAY_START_MINUTES = 9 * 60
EARLY_DAY_START_MINUTES = 8 * 60
DAY_END_MINUTES = 20 * 60
TRANSFER_BUFFER_MINUTES = 10
SENIOR_TRAVEL_BUFFER_MINUTES = 20
ARRIVAL_BUFFER_MINUTES = 45
DEPARTURE_BUFFER_MINUTES = 90
MEAL_BREAKS = (
    ("lunch", 13 * 60, 14 * 60),
    ("dinner", 19 * 60, 20 * 60),
)

PACE_RULES: dict[TripPace, dict[str, int]] = {
    TripPace.RELAXED: {"max_activities": 2, "max_hours": 8},
    TripPace.BALANCED: {"max_activities": 3, "max_hours": 10},
    TripPace.PACKED: {"max_activities": 5, "max_hours": 12},
}

MEAL_ALLOWANCE_PER_TRAVELLER_PER_DAY = 1_000


class ConstraintSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class ConstraintIssue(BaseModel):
    code: str
    message: str
    severity: ConstraintSeverity = ConstraintSeverity.ERROR
    day_number: Optional[int] = None
    poi_name: Optional[str] = None


class MealBreak(BaseModel):
    meal_type: str
    start_minute: int
    end_minute: int


class ScheduledStop(BaseModel):
    """Machine-readable stop; it intentionally contains no AI description."""

    poi_id: str
    poi_name: str
    category: str
    coordinates: GeoPoint
    day_number: int
    start_minute: int
    end_minute: int
    visit_minutes: int
    estimated_cost: int = 0
    opening_hours: Optional[str] = None
    mandatory: bool = False
    weather_suitable: bool = True
    accessible: bool = True
    travel_from_previous_minutes: int = 0

    @property
    def start_time(self) -> str:
        return _format_minutes(self.start_minute)

    @property
    def end_time(self) -> str:
        return _format_minutes(self.end_minute)


class ConstraintDay(BaseModel):
    day_number: int
    date: date
    activities: list[ScheduledStop] = Field(default_factory=list)
    meal_breaks: list[MealBreak] = Field(default_factory=list)
    travel_minutes: int = 0
    estimated_local_transport_cost: int = 0
    estimated_activity_cost: int = 0
    max_activities: int
    max_hours: int


class ConstraintPlan(BaseModel):
    days: list[ConstraintDay]
    issues: list[ConstraintIssue] = Field(default_factory=list)
    estimated_total_cost: int = 0
    daily_budget: int = 0
    feasible: bool = True

    @property
    def activities(self) -> list[ScheduledStop]:
        return [stop for day in self.days for stop in day.activities]


class RefinementAction(str, Enum):
    REDUCE_LOAD = "reduce_load"
    REPLACE_ACTIVITY = "replace_activity"
    REDUCE_BUDGET = "reduce_budget"
    AVOID_EARLY_TRAVEL = "avoid_early_travel"
    ADD_ACTIVITY = "add_activity"
    ADD_CUSTOM_ACTIVITY = "add_custom_activity"
    MOVE_ACTIVITY = "move_activity"
    DELETE_ACTIVITY = "delete_activity"
    EDIT_DURATION = "edit_duration"
    LOCK_ACTIVITY = "lock_activity"
    UNLOCK_ACTIVITY = "unlock_activity"
    REGENERATE_DAY = "regenerate_day"
    CHANGE_TRANSPORT = "change_transport"
    UNKNOWN = "unknown"


class RefinementInstruction(BaseModel):
    action: RefinementAction
    day_number: Optional[int] = None
    target: Optional[str] = None
    replacement: Optional[str] = None
    target_day_number: Optional[int] = None
    duration_minutes: Optional[int] = None
    transport_mode: Optional[str] = None
    raw_instruction: str


def _normalize(value: object) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).split())


def _format_minutes(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _parse_minutes(value: object) -> Optional[int]:
    text = str(value or "")
    match = re.search(r"(?:T|\s)?([01]\d|2[0-3]):([0-5]\d)", text)
    return int(match.group(1)) * 60 + int(match.group(2)) if match else None


def _opening_window(value: object) -> Optional[tuple[int, int]]:
    match = re.search(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", str(value or ""))
    if not match:
        return None
    start = _parse_minutes(match.group(1))
    end = _parse_minutes(match.group(2))
    return (start, end) if start is not None and end is not None and end > start else None


def _as_dict(candidate: object) -> dict[str, Any]:
    if isinstance(candidate, BaseModel):
        return candidate.model_dump(mode="json")
    return dict(candidate) if isinstance(candidate, Mapping) else {}


def _candidate_name(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("name") or "Unnamed place").strip()


def _candidate_coordinates(candidate: Mapping[str, Any]) -> Optional[GeoPoint]:
    raw = candidate.get("coordinates")
    if not isinstance(raw, Mapping):
        return None
    try:
        return GeoPoint.model_validate(raw)
    except ValueError:
        return None


def _candidate_duration(candidate: Mapping[str, Any]) -> int:
    try:
        return max(15, int(candidate.get("estimated_visit_minutes", 60)))
    except (TypeError, ValueError):
        return 60


def _candidate_cost(candidate: Mapping[str, Any]) -> int:
    try:
        return max(0, int(candidate.get("estimated_cost", 0)))
    except (TypeError, ValueError):
        return 0


def _candidate_category(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("category") or "attraction").strip()


def _candidate_tags(candidate: Mapping[str, Any]) -> dict[str, Any]:
    tags = candidate.get("osm_tags")
    return dict(tags) if isinstance(tags, Mapping) else {}


def _candidate_is_indoor(candidate: Mapping[str, Any]) -> bool:
    text = _normalize(" ".join([
        _candidate_name(candidate),
        _candidate_category(candidate),
        str(candidate.get("description") or ""),
    ]))
    tags = _candidate_tags(candidate)
    return (
        any(token in text for token in ("museum", "gallery", "indoor", "aquarium", "mall", "library"))
        or str(tags.get("indoor", "")).casefold() in {"yes", "true", "1"}
    )


def _candidate_is_accessible(candidate: Mapping[str, Any]) -> bool:
    tags = _candidate_tags(candidate)
    values = {
        _normalize(key): _normalize(value)
        for key, value in tags.items()
    }
    explicit = [
        values.get("wheelchair"),
        values.get("step free access"),
        values.get("accessible"),
        values.get("accessibility"),
    ]
    if any(value in {"yes", "true", "1", "limited"} for value in explicit):
        return True
    text = _normalize(str(candidate.get("description") or ""))
    return any(token in text for token in ("wheelchair", "step free", "accessible"))


def _weather_for_day(weather: Iterable[object], day_date: date) -> Optional[str]:
    for item in weather:
        data = _as_dict(item)
        value = data.get("date")
        if isinstance(value, date) and value == day_date:
            return str(data.get("severity") or "").casefold()
        if str(value or "")[:10] == day_date.isoformat():
            return str(data.get("severity") or "").casefold()
    return None


def _transport_value(transport: object, key: str) -> object:
    if isinstance(transport, BaseModel):
        return getattr(transport, key, None)
    return transport.get(key) if isinstance(transport, Mapping) else None


def _route_key(origin: Mapping[str, Any], destination: Mapping[str, Any]) -> tuple[str, str]:
    origin_id = str(origin.get("id") or origin.get("name") or "").casefold()
    destination_id = str(destination.get("id") or destination.get("name") or "").casefold()
    return origin_id, destination_id


def _score_candidate(candidate: Mapping[str, Any], intent: TripIntent, index: int) -> tuple[int, int, int]:
    text = _normalize(" ".join([
        _candidate_name(candidate),
        _candidate_category(candidate),
        str(candidate.get("description") or ""),
    ]))
    vibe_tokens: dict[TravelVibe, tuple[str, ...]] = {
        TravelVibe.ADVENTURE: ("fort", "trek", "hike", "outdoor", "beach", "water"),
        TravelVibe.CULTURE: ("museum", "fort", "palace", "heritage", "temple", "gallery"),
        TravelVibe.FOOD: ("market", "bazaar", "food", "restaurant"),
        TravelVibe.RELAXATION: ("beach", "garden", "lake", "park", "spa"),
        TravelVibe.SPIRITUAL: ("temple", "mosque", "church", "ashram", "shrine"),
        TravelVibe.NIGHTLIFE: ("night", "club", "bar", "market"),
    }
    interest_score = sum(
        1 for vibe in intent.interests
        if any(token in text for token in vibe_tokens.get(vibe, ()))
    )
    return (-interest_score, _candidate_cost(candidate), index)


def _matches_place(candidate: Mapping[str, Any], requested: str) -> bool:
    query = _normalize(requested)
    if not query:
        return False
    haystack = _normalize(f"{_candidate_name(candidate)} {_candidate_category(candidate)}")
    return query == _normalize(_candidate_name(candidate)) or query in haystack


@dataclass
class _DayState:
    day_number: int
    day_date: date
    start_minute: int
    end_minute: int
    max_activities: int
    max_hours: int
    cursor: int
    activities: list[ScheduledStop]
    meal_breaks: list[MealBreak]
    travel_minutes: int = 0
    local_cost: int = 0

    @property
    def estimated_activity_cost(self) -> int:
        return sum(activity.estimated_cost for activity in self.activities)


def _make_day_states(intent: TripIntent, transport: Optional[TransportOption]) -> list[_DayState]:
    total_days = (intent.end_date - intent.start_date).days + 1
    rules = PACE_RULES[intent.pace]
    start = EARLY_DAY_START_MINUTES if intent.early_departure_allowed else DAY_START_MINUTES
    end = DAY_END_MINUTES
    if intent.senior_travellers:
        rules = {"max_activities": max(1, rules["max_activities"] - 1), "max_hours": min(9, rules["max_hours"])}

    arrival = _parse_minutes(_transport_value(transport, "arrival_time")) if transport else None
    departure = _parse_minutes(_transport_value(transport, "departure_time")) if transport else None

    states: list[_DayState] = []
    for day_number in range(1, total_days + 1):
        day_start = start
        day_end = end
        if day_number == 1 and arrival is not None:
            if arrival > day_end and not intent.late_arrival_allowed:
                # Keep the day available for validation so the reason is machine-readable.
                day_start = day_end
            else:
                day_start = max(day_start, arrival + ARRIVAL_BUFFER_MINUTES)
        if day_number == total_days and departure is not None:
            if departure < day_start and not intent.early_departure_allowed:
                day_end = day_start
            day_end = min(day_end, departure - DEPARTURE_BUFFER_MINUTES)
        states.append(_DayState(
            day_number=day_number,
            day_date=intent.start_date + timedelta(days=day_number - 1),
            start_minute=day_start,
            end_minute=day_end,
            max_activities=rules["max_activities"],
            max_hours=rules["max_hours"],
            cursor=day_start,
            activities=[],
            meal_breaks=[MealBreak(meal_type=name, start_minute=begin, end_minute=finish) for name, begin, finish in MEAL_BREAKS],
        ))
    return states


def max_activities_for_intent(intent: TripIntent) -> int:
    """Return the deterministic per-day pace cap, including senior pacing."""

    limit = PACE_RULES[intent.pace]["max_activities"]
    return max(1, limit - 1) if intent.senior_travellers else limit


def _weather_suitable(candidate: Mapping[str, Any], severity: Optional[str]) -> bool:
    return severity != "indoor" or _candidate_is_indoor(candidate)


def _estimate_local_cost(travel_minutes: int, segments: int) -> int:
    return int(math.ceil(travel_minutes * 8 + segments * 30)) if segments else 0


def estimate_plan_cost(
    plan: ConstraintPlan,
    intent: TripIntent,
    selected_transport: Optional[TransportOption] = None,
) -> int:
    """Estimate complete trip cost using only deterministic inputs."""

    travellers = intent.travellers
    transport_cost = int(_transport_value(selected_transport, "price") or 0) * travellers * 2
    activity_cost = sum(day.estimated_activity_cost for day in plan.days) * travellers
    meal_cost = MEAL_ALLOWANCE_PER_TRAVELLER_PER_DAY * travellers * len(plan.days)
    local_cost = sum(day.estimated_local_transport_cost for day in plan.days)
    return transport_cost + activity_cost + meal_cost + local_cost


def _fits_meal_break(start: int, duration: int, meal_breaks: list[MealBreak]) -> int:
    adjusted = start
    while True:
        end = adjusted + duration
        conflict = next(
            (meal for meal in meal_breaks if adjusted < meal.end_minute and end > meal.start_minute),
            None,
        )
        if not conflict:
            return adjusted
        adjusted = conflict.end_minute


class ConstraintEngine:
    """Small deterministic scheduler for the current single-destination scope."""

    def __init__(self, route_minutes: Optional[Mapping[tuple[str, str], int]] = None):
        self.route_minutes = {
            (_normalize(origin), _normalize(destination)): int(minutes)
            for (origin, destination), minutes in (route_minutes or {}).items()
        }

    def travel_minutes(self, origin: Mapping[str, Any], destination: Mapping[str, Any]) -> int:
        origin_name, destination_name = _route_key(origin, destination)
        direct = self.route_minutes.get((_normalize(origin_name), _normalize(destination_name)))
        if direct is not None:
            return max(0, direct)
        reverse = self.route_minutes.get((_normalize(destination_name), _normalize(origin_name)))
        if reverse is not None:
            return max(0, reverse)
        origin_point = _candidate_coordinates(origin)
        destination_point = _candidate_coordinates(destination)
        if not origin_point or not destination_point:
            return 30
        distance = haversine_distance(origin_point, destination_point)
        # A conservative city sightseeing estimate; OSRM remains the final
        # route source when the planner later builds the persisted itinerary.
        return max(10, int(math.ceil(distance / 35 * 60)))

    def optimize(
        self,
        intent: TripIntent,
        candidates: Iterable[object],
        *,
        weather: Iterable[object] = (),
        selected_transport: Optional[TransportOption] = None,
    ) -> ConstraintPlan:
        issues: list[ConstraintIssue] = []
        states = _make_day_states(intent, selected_transport)
        excluded = intent.excluded_places
        normalized_candidates: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, raw_candidate in enumerate(candidates):
            candidate = _as_dict(raw_candidate)
            name = _candidate_name(candidate)
            coordinates = _candidate_coordinates(candidate)
            if not coordinates or not name or any(_matches_place(candidate, item) for item in excluded):
                continue
            key = _normalize(name)
            if key in seen:
                continue
            candidate["coordinates"] = coordinates.model_dump()
            candidate["id"] = str(candidate.get("id") or key)
            candidate["_index"] = index
            seen.add(key)
            normalized_candidates.append(candidate)

        mandatory: list[dict[str, Any]] = []
        for requested in intent.mandatory_places:
            match = next((candidate for candidate in normalized_candidates if _matches_place(candidate, requested)), None)
            if not match:
                issues.append(ConstraintIssue(
                    code="mandatory_place_unavailable",
                    message=f"Mandatory place '{requested}' is not available in the reviewed candidate data.",
                    poi_name=requested,
                ))
            elif match not in mandatory:
                mandatory.append(match)

        optional = [candidate for candidate in normalized_candidates if candidate not in mandatory]
        optional.sort(key=lambda candidate: _score_candidate(candidate, intent, int(candidate["_index"])))
        candidates_in_order = [(candidate, True) for candidate in mandatory] + [(candidate, False) for candidate in optional]

        for candidate, is_mandatory in candidates_in_order:
            name = _candidate_name(candidate)
            accessible = _candidate_is_accessible(candidate)
            severity_by_day = [
                _weather_for_day(weather, state.day_date)
                for state in states
            ]
            suitable_by_day = [
                _weather_suitable(candidate, severity)
                for severity in severity_by_day
            ]
            if intent.accessibility_requirements and not accessible:
                if is_mandatory:
                    issues.append(ConstraintIssue(
                        code="mandatory_place_accessibility_unknown",
                        message=f"Mandatory place '{name}' has no confirmed accessibility evidence.",
                        poi_name=name,
                    ))
                continue

            candidate_scheduled = False
            # Spread optional activities across the least-loaded days first.
            ordered_states = sorted(states, key=lambda state: (len(state.activities), state.day_number))
            for state in ordered_states:
                if len(state.activities) >= state.max_activities:
                    continue
                if not suitable_by_day[state.day_number - 1] and any(suitable_by_day):
                    continue
                previous = state.activities[-1] if state.activities else None
                travel = self.travel_minutes(
                    {"id": previous.poi_id, "name": previous.poi_name, "coordinates": previous.coordinates.model_dump()} if previous else candidate,
                    candidate,
                ) if previous else 0
                buffer = SENIOR_TRAVEL_BUFFER_MINUTES if intent.senior_travellers else TRANSFER_BUFFER_MINUTES
                start = state.cursor + (travel + buffer if previous else 0)
                start = _fits_meal_break(start, _candidate_duration(candidate), state.meal_breaks)
                window = _opening_window(candidate.get("opening_hours"))
                if window:
                    start = max(start, window[0])
                end = start + _candidate_duration(candidate)
                if window and end > window[1]:
                    continue
                if end > state.end_minute:
                    continue
                if end - state.start_minute > state.max_hours * 60:
                    continue
                stop = ScheduledStop(
                    poi_id=str(candidate["id"]),
                    poi_name=name,
                    category=_candidate_category(candidate),
                    coordinates=GeoPoint.model_validate(candidate["coordinates"]),
                    day_number=state.day_number,
                    start_minute=start,
                    end_minute=end,
                    visit_minutes=_candidate_duration(candidate),
                    estimated_cost=_candidate_cost(candidate),
                    opening_hours=candidate.get("opening_hours"),
                    mandatory=is_mandatory,
                    weather_suitable=suitable_by_day[state.day_number - 1],
                    accessible=accessible,
                    travel_from_previous_minutes=travel,
                )
                state.activities.append(stop)
                state.cursor = end
                state.travel_minutes += travel
                state.local_cost = _estimate_local_cost(state.travel_minutes, max(0, len(state.activities) - 1))
                candidate_scheduled = True
                break

            if not candidate_scheduled and is_mandatory:
                issues.append(ConstraintIssue(
                    code="mandatory_place_unscheduled",
                    message=f"Mandatory place '{name}' could not fit within the selected dates and constraints.",
                    poi_name=name,
                ))

        def build_days() -> list[ConstraintDay]:
            return [ConstraintDay(
                day_number=state.day_number,
                date=state.day_date,
                activities=state.activities,
                meal_breaks=state.meal_breaks,
                travel_minutes=state.travel_minutes,
                estimated_local_transport_cost=state.local_cost,
                estimated_activity_cost=state.estimated_activity_cost,
                max_activities=state.max_activities,
                max_hours=state.max_hours,
            ) for state in states]

        days = build_days()
        draft = ConstraintPlan(days=days, daily_budget=int(intent.budget / len(days)))
        draft.estimated_total_cost = estimate_plan_cost(draft, intent, selected_transport)
        while draft.estimated_total_cost > intent.budget:
            removable: list[tuple[_DayState, int, ScheduledStop]] = [
                (state, index, activity)
                for state in states
                for index, activity in enumerate(state.activities)
                if not activity.mandatory
            ]
            if not removable:
                break
            state, index, removed = max(
                removable,
                key=lambda item: (item[2].estimated_cost, item[2].end_minute, item[0].day_number),
            )
            state.activities.pop(index)
            for activity_index, activity in enumerate(state.activities):
                if activity_index == 0:
                    activity.travel_from_previous_minutes = 0
                    continue
                previous = state.activities[activity_index - 1]
                activity.travel_from_previous_minutes = self.travel_minutes(
                    {"id": previous.poi_id, "name": previous.poi_name, "coordinates": previous.coordinates.model_dump()},
                    {"id": activity.poi_id, "name": activity.poi_name, "coordinates": activity.coordinates.model_dump()},
                )
            state.travel_minutes = sum(activity.travel_from_previous_minutes for activity in state.activities)
            state.local_cost = _estimate_local_cost(state.travel_minutes, max(0, len(state.activities) - 1))
            issues.append(ConstraintIssue(
                code="optional_place_dropped_for_budget",
                message=f"Optional place '{removed.poi_name}' was left unscheduled to keep the deterministic estimate within budget.",
                severity=ConstraintSeverity.WARNING,
                day_number=state.day_number,
                poi_name=removed.poi_name,
            ))
            days = build_days()
            draft = ConstraintPlan(days=days, daily_budget=int(intent.budget / len(days)))
            draft.estimated_total_cost = estimate_plan_cost(draft, intent, selected_transport)
        plan = ConstraintPlan(days=days, issues=issues, daily_budget=int(intent.budget / len(days)))
        plan.estimated_total_cost = estimate_plan_cost(plan, intent, selected_transport)
        plan.issues.extend(validate_constraint_plan(plan, intent, selected_transport, include_existing=False))
        plan.feasible = not any(issue.severity == ConstraintSeverity.ERROR for issue in plan.issues)
        return plan


def validate_constraint_plan(
    plan: ConstraintPlan,
    intent: TripIntent,
    selected_transport: Optional[TransportOption] = None,
    *,
    include_existing: bool = True,
) -> list[ConstraintIssue]:
    """Validate a machine schedule without asking Gemini to repair it."""

    issues = list(plan.issues) if include_existing else []
    expected_days = (intent.end_date - intent.start_date).days + 1
    if len(plan.days) != expected_days:
        issues.append(ConstraintIssue(
            code="wrong_day_count",
            message=f"Schedule has {len(plan.days)} days but the trip has {expected_days} days.",
        ))
    for day in plan.days:
        if len(day.activities) > day.max_activities:
            issues.append(ConstraintIssue(
                code="pace_limit_exceeded",
                message=f"Day {day.day_number} exceeds the {intent.pace.value} pace limit.",
                day_number=day.day_number,
            ))
        previous: Optional[ScheduledStop] = None
        for activity in day.activities:
            if previous:
                required = previous.end_minute + activity.travel_from_previous_minutes
                if activity.start_minute < required:
                    issues.append(ConstraintIssue(
                        code="travel_time_missing",
                        message=f"Day {day.day_number} does not include enough travel time before '{activity.poi_name}'.",
                        day_number=day.day_number,
                        poi_name=activity.poi_name,
                    ))
            window = _opening_window(activity.opening_hours)
            if window and (activity.start_minute < window[0] or activity.end_minute > window[1]):
                issues.append(ConstraintIssue(
                    code="outside_opening_hours",
                    message=f"'{activity.poi_name}' is scheduled outside its listed opening hours.",
                    day_number=day.day_number,
                    poi_name=activity.poi_name,
                ))
            if activity.end_minute <= activity.start_minute or activity.end_minute - activity.start_minute < activity.visit_minutes:
                issues.append(ConstraintIssue(
                    code="invalid_visit_duration",
                    message=f"'{activity.poi_name}' does not have its full visit duration scheduled.",
                    day_number=day.day_number,
                    poi_name=activity.poi_name,
                ))
            if not activity.weather_suitable:
                issues.append(ConstraintIssue(
                    code="weather_unsuitable",
                    message=f"'{activity.poi_name}' is outdoors during weather marked for indoor alternatives.",
                    severity=ConstraintSeverity.WARNING,
                    day_number=day.day_number,
                    poi_name=activity.poi_name,
                ))
            if intent.accessibility_requirements and not activity.accessible:
                issues.append(ConstraintIssue(
                    code="accessibility_unverified",
                    message=f"Accessibility is not confirmed for '{activity.poi_name}'.",
                    day_number=day.day_number,
                    poi_name=activity.poi_name,
                ))
            previous = activity
        if day.activities:
            span = day.activities[-1].end_minute - day.activities[0].start_minute
            if span > day.max_hours * 60:
                issues.append(ConstraintIssue(
                    code="day_window_exceeded",
                    message=f"Day {day.day_number} exceeds its {day.max_hours}-hour pace window.",
                    day_number=day.day_number,
                ))
        daily_cost = (
            day.estimated_activity_cost * intent.travellers
            + MEAL_ALLOWANCE_PER_TRAVELLER_PER_DAY * intent.travellers
            + day.estimated_local_transport_cost
        )
        if daily_cost > plan.daily_budget:
            issues.append(ConstraintIssue(
                code="daily_budget_exceeded",
                message=f"Day {day.day_number} has a deterministic daily estimate of ₹{daily_cost:,}, above its ₹{plan.daily_budget:,} share.",
                day_number=day.day_number,
            ))
    expected_cost = estimate_plan_cost(plan, intent, selected_transport)
    plan.estimated_total_cost = expected_cost
    if expected_cost > intent.budget:
        issues.append(ConstraintIssue(
            code="budget_exceeded",
            message=f"Deterministic estimate ₹{expected_cost:,} exceeds the ₹{intent.budget:,} trip budget.",
        ))
    arrival = _parse_minutes(_transport_value(selected_transport, "arrival_time")) if selected_transport else None
    departure = _parse_minutes(_transport_value(selected_transport, "departure_time")) if selected_transport else None
    if arrival is not None and arrival > DAY_END_MINUTES and not intent.late_arrival_allowed:
        issues.append(ConstraintIssue(
            code="late_arrival_not_allowed",
            message="The selected transport arrives after the allowed sightseeing window.",
            day_number=1,
        ))
    if departure is not None and departure < EARLY_DAY_START_MINUTES and not intent.early_departure_allowed:
        issues.append(ConstraintIssue(
            code="early_departure_not_allowed",
            message="The selected transport departs before the allowed travel window.",
            day_number=len(plan.days),
        ))
    return issues


def validate_transport_window(
    intent: TripIntent,
    selected_transport: Optional[TransportOption],
) -> list[ConstraintIssue]:
    """Validate transport arrival/departure against the traveller's windows."""

    if not selected_transport:
        return []
    issues: list[ConstraintIssue] = []
    arrival = _parse_minutes(_transport_value(selected_transport, "arrival_time"))
    departure = _parse_minutes(_transport_value(selected_transport, "departure_time"))
    if arrival is not None and arrival + ARRIVAL_BUFFER_MINUTES >= DAY_END_MINUTES and not intent.late_arrival_allowed:
        issues.append(ConstraintIssue(
            code="late_arrival_not_allowed",
            message="The selected transport arrives too late for the allowed first-day travel window.",
            day_number=1,
        ))
    if departure is not None and departure - DEPARTURE_BUFFER_MINUTES < EARLY_DAY_START_MINUTES and not intent.early_departure_allowed:
        issues.append(ConstraintIssue(
            code="early_departure_not_allowed",
            message="The selected transport departs too early for the allowed last-day travel window.",
            day_number=(intent.end_date - intent.start_date).days + 1,
        ))
    return issues


def constraint_plan_to_raw_plan(plan: ConstraintPlan) -> dict[str, Any]:
    """Convert deterministic stops into the JSON shape used by Gemini narration."""

    day_plans: list[dict[str, Any]] = []
    for day in plan.days:
        day_plans.append({
            "day_number": day.day_number,
            "date": day.date.isoformat(),
            "notes": "",
            "activities": [
                {
                    "name": activity.poi_name,
                    "category": activity.category,
                    "lat": activity.coordinates.lat,
                    "lng": activity.coordinates.lng,
                    "start_time": activity.start_time,
                    "end_time": activity.end_time,
                    "estimated_cost": activity.estimated_cost,
                    "notes": "",
                    "is_backup": False,
                }
                for activity in day.activities
            ],
            "meals": [
                {"name": "Suggested meal type: local breakfast", "meal_type": "breakfast", "estimated_cost": 150},
                {"name": "Suggested meal type: regional lunch", "meal_type": "lunch", "estimated_cost": 350},
                {"name": "Suggested meal type: local dinner", "meal_type": "dinner", "estimated_cost": 500},
            ],
            "backup_activities": [],
        })
    return {"day_plans": day_plans, "tips": []}


_DAY_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
}


def _instruction_day(text: str) -> Optional[int]:
    match = re.search(r"\bday\s*(\d+|one|two|three|four|five|six|seven)\b", text)
    if not match:
        return None
    value = match.group(1)
    return int(value) if value.isdigit() else _DAY_WORDS.get(value)


def parse_refinement_instruction(instruction: str) -> RefinementInstruction:
    """Turn common traveller edits into a small deterministic change contract."""

    text = instruction.casefold().strip()
    day_number = _instruction_day(text)

    move_match = re.search(
        r"move\s+activity\s+[\"'](.+?)[\"']\s+from\s+day\s+(\d+)\s+to\s+day\s+(\d+)",
        instruction,
        re.IGNORECASE,
    )
    if move_match:
        return RefinementInstruction(
            action=RefinementAction.MOVE_ACTIVITY,
            day_number=int(move_match.group(2)),
            target=move_match.group(1).strip(),
            target_day_number=int(move_match.group(3)),
            raw_instruction=instruction,
        )

    delete_match = re.search(
        r"delete\s+activity\s+[\"'](.+?)[\"']\s+from\s+day\s+(\d+)",
        instruction,
        re.IGNORECASE,
    )
    if delete_match:
        return RefinementInstruction(
            action=RefinementAction.DELETE_ACTIVITY,
            day_number=int(delete_match.group(2)),
            target=delete_match.group(1).strip(),
            raw_instruction=instruction,
        )

    duration_match = re.search(
        r"set\s+duration\s+for\s+activity\s+[\"'](.+?)[\"']\s+on\s+day\s+(\d+)\s+to\s+(\d+)\s*(?:minutes?|mins?)?",
        instruction,
        re.IGNORECASE,
    )
    if duration_match:
        return RefinementInstruction(
            action=RefinementAction.EDIT_DURATION,
            day_number=int(duration_match.group(2)),
            target=duration_match.group(1).strip(),
            duration_minutes=max(15, min(720, int(duration_match.group(3)))),
            raw_instruction=instruction,
        )

    lock_match = re.search(
        r"(unlock|lock)\s+activity\s+[\"'](.+?)[\"']\s+on\s+day\s+(\d+)",
        instruction,
        re.IGNORECASE,
    )
    if lock_match:
        return RefinementInstruction(
            action=RefinementAction.UNLOCK_ACTIVITY if lock_match.group(1).casefold() == "unlock" else RefinementAction.LOCK_ACTIVITY,
            day_number=int(lock_match.group(3)),
            target=lock_match.group(2).strip(),
            raw_instruction=instruction,
        )

    custom_match = re.search(
        r"add\s+custom\s+activity\s+[\"'](.+?)[\"']\s+to\s+day\s+(\d+)",
        instruction,
        re.IGNORECASE,
    )
    if custom_match:
        return RefinementInstruction(
            action=RefinementAction.ADD_CUSTOM_ACTIVITY,
            day_number=int(custom_match.group(2)),
            replacement=custom_match.group(1).strip(),
            raw_instruction=instruction,
        )

    replace_activity_match = re.search(
        r"replace\s+activity\s+[\"'](.+?)[\"']\s+on\s+day\s+(\d+)\s+with\s+[\"'](.+?)[\"']",
        instruction,
        re.IGNORECASE,
    )
    if replace_activity_match:
        return RefinementInstruction(
            action=RefinementAction.REPLACE_ACTIVITY,
            day_number=int(replace_activity_match.group(2)),
            target=replace_activity_match.group(1).strip(),
            replacement=replace_activity_match.group(3).strip(),
            raw_instruction=instruction,
        )

    regenerate_match = re.search(r"regenerate\s+day\s+(\d+)", instruction, re.IGNORECASE)
    if regenerate_match:
        return RefinementInstruction(
            action=RefinementAction.REGENERATE_DAY,
            day_number=int(regenerate_match.group(1)),
            raw_instruction=instruction,
        )

    transport_matches = re.findall(r"\b(flight|train|road)\b", text)
    transport_mode = transport_matches[-1] if transport_matches else None
    if transport_mode and any(token in text for token in ("change", "switch", "prefer", "take")):
        return RefinementInstruction(
            action=RefinementAction.CHANGE_TRANSPORT,
            day_number=day_number,
            transport_mode=transport_mode,
            raw_instruction=instruction,
        )
    if any(token in text for token in ("less crowded", "less busy", "fewer activities", "less packed", "slow down")):
        return RefinementInstruction(action=RefinementAction.REDUCE_LOAD, day_number=day_number, raw_instruction=instruction)
    if any(token in text for token in ("reduce the budget", "lower the budget", "cheaper", "spend less")):
        return RefinementInstruction(action=RefinementAction.REDUCE_BUDGET, day_number=day_number, raw_instruction=instruction)
    if any(token in text for token in ("avoid early", "no early", "not early", "later morning")):
        return RefinementInstruction(action=RefinementAction.AVOID_EARLY_TRAVEL, day_number=day_number, raw_instruction=instruction)
    add_match = re.search(r"\badd\s+(?:a|an)?\s*(temple|museum|beach|nature|park|fort|market|garden)\b", text)
    if add_match:
        return RefinementInstruction(
            action=RefinementAction.ADD_ACTIVITY,
            day_number=day_number,
            replacement=add_match.group(1),
            raw_instruction=instruction,
        )
    replace_match = re.search(r"replace\s+(?:the\s+)?([a-z ]+?)\s+with\s+(?:a\s+|an\s+)?([a-z ]+)", text)
    if replace_match:
        return RefinementInstruction(
            action=RefinementAction.REPLACE_ACTIVITY,
            day_number=day_number,
            target=replace_match.group(1).strip(),
            replacement=replace_match.group(2).strip(),
            raw_instruction=instruction,
        )
    return RefinementInstruction(action=RefinementAction.UNKNOWN, day_number=day_number, raw_instruction=instruction)


def apply_scoped_refinement(
    plan: dict[str, Any],
    refinement: RefinementInstruction,
) -> tuple[dict[str, Any], set[int], bool]:
    """Apply safe local edits while preserving all non-target days byte-for-byte."""

    updated = deepcopy(plan)
    day_plans = updated.get("day_plans", [])
    target_days = {
        int(day.get("day_number"))
        for day in day_plans
        if isinstance(day, Mapping) and str(day.get("day_number", "")).isdigit()
    }
    if refinement.action == RefinementAction.MOVE_ACTIVITY:
        target_days &= {refinement.day_number or 0, refinement.target_day_number or 0}
    elif refinement.day_number is not None:
        target_days &= {refinement.day_number}
    elif refinement.action in {RefinementAction.ADD_ACTIVITY, RefinementAction.ADD_CUSTOM_ACTIVITY}:
        first_day = min(target_days, default=0)
        target_days = {first_day} if first_day else set()
    changed_days: set[int] = set()
    if not target_days:
        return updated, changed_days, False

    if refinement.action == RefinementAction.MOVE_ACTIVITY:
        source_day = next((day for day in day_plans if isinstance(day, dict) and int(day.get("day_number", 0) or 0) == refinement.day_number), None)
        target_day = next((day for day in day_plans if isinstance(day, dict) and int(day.get("day_number", 0) or 0) == refinement.target_day_number), None)
        if source_day is None or target_day is None or source_day is target_day:
            return updated, changed_days, False
        activities = source_day.get("activities", [])
        if not isinstance(activities, list):
            return updated, changed_days, False
        target = _normalize(refinement.target)
        activity_index = next(
            (index for index, activity in enumerate(activities) if isinstance(activity, dict) and target in _normalize(activity.get("name"))),
            None,
        )
        if activity_index is None:
            return updated, changed_days, False
        activity = activities[activity_index]
        if activity.get("is_locked"):
            return updated, changed_days, False
        activities.pop(activity_index)
        target_activities = target_day.get("activities", [])
        if not isinstance(target_activities, list):
            target_activities = []
            target_day["activities"] = target_activities
        target_activities.append(activity)
        source_day["notes"] = f"Day {source_day.get('day_number')}: stop moved to day {target_day.get('day_number')}."
        target_day["notes"] = f"Day {target_day.get('day_number')}: added {activity.get('name', 'a stop')}."
        changed_days.update({int(source_day.get("day_number")), int(target_day.get("day_number"))})
        return updated, changed_days, True

    if refinement.action == RefinementAction.REGENERATE_DAY:
        return updated, changed_days, False

    for day in day_plans:
        if not isinstance(day, dict) or int(day.get("day_number", 0) or 0) not in target_days:
            continue
        day_number = int(day["day_number"])
        activities = day.get("activities", [])
        if not isinstance(activities, list):
            activities = []
            day["activities"] = activities
        backups = day.get("backup_activities", [])
        if not isinstance(backups, list):
            backups = []
            day["backup_activities"] = backups
        if refinement.action in {RefinementAction.DELETE_ACTIVITY, RefinementAction.EDIT_DURATION, RefinementAction.LOCK_ACTIVITY, RefinementAction.UNLOCK_ACTIVITY}:
            target = _normalize(refinement.target)
            target_index = next(
                (index for index, activity in enumerate(activities) if isinstance(activity, dict) and target in _normalize(activity.get("name"))),
                None,
            )
            if target_index is None:
                continue
            target_activity = activities[target_index]
            if refinement.action == RefinementAction.DELETE_ACTIVITY:
                if target_activity.get("is_locked"):
                    continue
                activities.pop(target_index)
                changed_days.add(day_number)
            elif refinement.action == RefinementAction.EDIT_DURATION:
                if target_activity.get("is_locked") or not refinement.duration_minutes:
                    continue
                start = _parse_minutes(target_activity.get("start_time")) or DAY_START_MINUTES
                target_activity["duration_minutes"] = refinement.duration_minutes
                target_activity["start_time"] = _format_minutes(start)
                target_activity["end_time"] = _format_minutes(start + refinement.duration_minutes)
                changed_days.add(day_number)
            else:
                target_activity["is_locked"] = refinement.action == RefinementAction.LOCK_ACTIVITY
                changed_days.add(day_number)
        elif refinement.action in {RefinementAction.ADD_CUSTOM_ACTIVITY, RefinementAction.ADD_ACTIVITY}:
            replacement = (refinement.replacement or "custom activity").strip()
            activities.append({
                "name": replacement,
                "category": "custom activity",
                "start_time": None,
                "end_time": None,
                "estimated_cost": 0,
                "notes": "Added by traveller; verify details before visiting.",
                "is_backup": False,
                "is_locked": False,
            })
            changed_days.add(day_number)
        elif refinement.action == RefinementAction.REDUCE_LOAD and len(activities) > 1:
            removed = activities.pop()
            backups.append({**removed, "is_backup": True})
            day["notes"] = f"Day {day_number}: a lighter schedule after your refinement."
            changed_days.add(day_number)
        elif refinement.action == RefinementAction.REDUCE_BUDGET and activities:
            removed = max(activities, key=lambda item: int(item.get("estimated_cost", 0) or 0))
            activities.remove(removed)
            backups.append({**removed, "is_backup": True})
            day["notes"] = f"Day {day_number}: lower-cost options retained for flexibility."
            changed_days.add(day_number)
        elif refinement.action == RefinementAction.AVOID_EARLY_TRAVEL:
            for activity in activities:
                start = _parse_minutes(activity.get("start_time"))
                end = _parse_minutes(activity.get("end_time"))
                if start is not None and start < DAY_START_MINUTES:
                    duration = (end or start + 60) - start
                    activity["start_time"] = _format_minutes(DAY_START_MINUTES)
                    activity["end_time"] = _format_minutes(DAY_START_MINUTES + duration)
                    changed_days.add(day_number)
            if day_number in changed_days:
                day["notes"] = f"Day {day_number}: morning travel begins later as requested."
        elif refinement.action == RefinementAction.REPLACE_ACTIVITY:
            replacement = _normalize(refinement.replacement)
            backup_index = next(
                (
                    index for index, candidate in enumerate(backups)
                    if replacement and replacement in _normalize(f"{candidate.get('name', '')} {candidate.get('category', '')}")
                ),
                None,
            )
            if backup_index is not None:
                candidate = backups.pop(backup_index)
                if refinement.action == RefinementAction.REPLACE_ACTIVITY and refinement.target:
                    target = _normalize(refinement.target)
                    target_index = next(
                        (index for index, activity in enumerate(activities) if target in _normalize(f"{activity.get('name', '')} {activity.get('category', '')}")),
                        None,
                    )
                    if target_index is not None and not activities[target_index].get("is_locked"):
                        replaced = activities.pop(target_index)
                        backups.append({**replaced, "is_backup": True})
                activities.append({**candidate, "is_backup": False})
                changed_days.add(day_number)
            elif refinement.target and refinement.replacement:
                target = _normalize(refinement.target)
                target_index = next(
                    (index for index, activity in enumerate(activities) if target in _normalize(activity.get("name"))),
                    None,
                )
                if target_index is not None and not activities[target_index].get("is_locked"):
                    activities.pop(target_index)
                    activities.append({
                        "name": refinement.replacement.strip(),
                        "category": "custom activity",
                        "start_time": None,
                        "end_time": None,
                        "estimated_cost": 0,
                        "notes": "Replacement requested by traveller; verify details before visiting.",
                        "is_backup": False,
                        "is_locked": False,
                    })
                    changed_days.add(day_number)
    return updated, changed_days, bool(changed_days)


def build_trip_intent(request: object) -> TripIntent:
    """Convenience wrapper used by orchestration and tests."""

    if isinstance(request, TripIntent):
        return request
    return TripIntent.from_request(request)
