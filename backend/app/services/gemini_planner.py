"""
Gemini AI Planner — the core orchestration service.
Generates day-by-day itineraries using real data from all other services,
with a propose → validate → repair loop for quality assurance.
"""

import json
import logging
import math
import re
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional

from google import genai
from google.genai import types

from app.cache.redis_cache import cached
from app.config import settings
from app.models.trip import (
    Activity,
    AccommodationPreference,
    BudgetBreakdown,
    DataProvenance,
    DataStatus,
    DayPlan,
    DayWeather,
    GeoPoint,
    Itinerary,
    CityInfo,
    MealRecommendation,
    POI,
    RouteSegment,
    TransportOption,
    TransportMode,
    TravelPreference,
    TravelVibe,
    TripRequest,
    WeatherSeverity,
    FestivalEvent,
    PackingItem,
)
from app.services.geocoding import geocode_to_city_info, haversine_distance
from app.services.poi_discovery import discover_pois
from app.services.routing import get_route_segment, validate_day_feasibility
from app.services.transport import search_transport
from app.services.weather import get_forecast
from app.services.photos import get_destination_photos
from app.services.constraint_engine import (
    RefinementAction,
    ConstraintEngine,
    apply_scoped_refinement,
    build_trip_intent,
    constraint_plan_to_raw_plan,
    max_activities_for_intent,
    parse_refinement_instruction,
    validate_transport_window,
)

logger = logging.getLogger(__name__)

MAX_REPAIR_ITERATIONS = 3
DEFAULT_ACTIVITY_START = 9 * 60
LATEST_ACTIVITY_END = 20 * 60
MIN_ROUTE_BUFFER_MINUTES = 10
COORDINATE_MATCH_RADIUS_KM = 2.0


def _planner_estimate_provenance(
    disclaimer: str,
    *,
    provider: str = "YatraAI planning estimate",
    confidence: float = 0.5,
) -> DataProvenance:
    """Attach a visible disclosure to deterministic or model-suggested values."""

    return DataProvenance(
        provider=provider,
        status=DataStatus.ESTIMATED,
        retrieved_at=datetime.now(timezone.utc),
        confidence=confidence,
        source_reference="app://yatraai-planning-estimates",
        disclaimer=disclaimer,
    )

STAY_RATE_PER_NIGHT = {
    AccommodationPreference.BUDGET: 1200,
    AccommodationPreference.STANDARD: 2500,
    AccommodationPreference.COMFORT: 5000,
}

SYSTEM_PROMPT = """You are an expert India domestic travel planner. You create detailed, practical, 
budget-conscious day-by-day itineraries for travelers within India.

IMPORTANT RULES:
1. All individual activity and meal costs must be per traveller, in INR (₹). Use realistic Indian prices.
2. Plan activities from 8:00 AM to 8:00 PM max per day.
3. Allow 30-60 min between activities for travel time.
4. Include 3 meals per day (breakfast, lunch, dinner) with estimated costs.
5. Budget meal costs realistically: street food ₹50-150, casual dining ₹200-500, fine dining ₹800-2000.
6. If weather is rainy, prioritize indoor activities and include backup options.
7. Respect the user's travel vibe preferences.
8. First and last days may have reduced activities due to travel.
9. Suggest specific, real places — not generic "visit a temple".
10. Include estimated costs for every activity and meal. Do NOT calculate totals,
    category budgets, transport, hotel, local transport, or taxes: the backend calculates them.
11. Only name a restaurant when it appears in supplied place data. Otherwise use
    "Suggested meal type: <dish or food area>" — never invent a generic restaurant.
12. Match the requested pace: relaxed means fewer, longer stops; packed means more
    stops only when the full travel-time validation can still pass.
13. Respect dietary, accessibility, and early/late travel constraints supplied in trip details.
14. The supplied deterministic candidate schedule is authoritative for place selection,
    day assignment, and exact timings. Do not move, add, or remove scheduled stops;
    enrich it with concise notes and practical wording only.

You MUST respond with valid JSON matching the exact schema provided. No markdown, no explanations — ONLY JSON."""


def _build_planning_prompt(
    request: TripRequest,
    origin: CityInfo,
    destination: CityInfo,
    pois: list[dict],
    transport_options: list[dict],
    weather: list[dict],
    distance_km: float,
    festivals: list[dict],
    selected_transport: Optional[TransportOption] = None,
    deterministic_schedule: Optional[dict] = None,
) -> str:
    """Build the grounded planning prompt with real data."""

    total_days = (request.end_date - request.start_date).days + 1

    selected_transport_data = selected_transport.model_dump() if selected_transport else None

    # Give Gemini every POI returned by the reviewed catalogue and the map
    # adapter. The trip length controls what it schedules, never what it can
    # consider; individual activities are still validated against this set.
    prompt_pois = pois

    prompt = f"""Plan a {total_days}-day trip from {origin.name} to {destination.name}.

TRIP DETAILS:
- Dates: {request.start_date} to {request.end_date} ({total_days} days)
- Total Budget: ₹{request.budget:,}
- Travellers: {request.adults} adult(s), {request.children} child(ren)
- Travel preference: {request.travel_preference.value}
- Pace: {request.pace.value}
- Dietary preference: {request.dietary_preference.value if request.dietary_preference else 'no restriction'}
- Accessibility: {request.accessibility_requirements or ('senior travellers in party' if request.senior_citizens else 'none stated')}
- Mandatory places: {', '.join(request.mandatory_places) or 'none'}
- Excluded places: {', '.join(request.excluded_places) or 'none'}
- Traveller notes: {request.free_text_notes or 'none'}
- Early-morning travel accepted: {'yes' if request.allow_early_morning_travel else 'no'}
- Late-night travel accepted: {'yes' if request.allow_late_night_travel else 'no'}
- Selected transport (budgeted both ways by the server): {json.dumps(selected_transport_data, default=str)}
- Accommodation preference: {request.accommodation_preference.value}
- Vibes: {', '.join(v.value for v in request.vibes)}
- Distance: {distance_km:.0f} km

AVAILABLE POIs AT {destination.name.upper()} (OpenStreetMap plus reviewed landmark shortlist):
{json.dumps(prompt_pois, indent=2, default=str)}

PRIORITY LANDMARKS:
POIs with an `editorial_landmark_shortlist` source are reviewed,
destination-defining landmarks and are listed in priority order. Plan coverage
by feasible daily capacity, never a fixed landmark cap:
- 1 day: schedule 3–5 major places.
- 2–3 days: schedule 6–10 major places across the available days.
- 4 or more days: schedule 10–15 curated major places, then add relevant
  local map-sourced options where daily timing and budget permit.
There is no fixed cap on the available POIs. Always account for the supplied
visit duration, transit time, daily budget, and opening constraints when known;
preserve suitable unscheduled places as alternatives.
- Never claim a landmark is open, accessible, or operating without a current source.
- Elephanta Caves is a separate ferry excursion; schedule it as a half-day at most and
  do not combine it with a dense South Mumbai day.
Use the supplied names and coordinates for priority landmarks; do not replace them
with generic or invented attractions.

WEATHER FORECAST:
{json.dumps(weather, indent=2, default=str)}

DETERMINISTIC CANDIDATE SCHEDULE:
{json.dumps(deterministic_schedule or {}, indent=2, default=str)}

The deterministic candidate schedule is the factual planning layer. Preserve
its selected places, exact start/end times, visit durations, and day numbers.
You may add concise notes, meal wording, practical tips, and explanations, but
do not invent places, move activities, or make an infeasible schedule.

Respond with ONLY valid JSON in this exact format:
{{
  "day_plans": [
    {{
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "notes": "Brief day summary",
      "activities": [
        {{
          "name": "Place name",
          "category": "museum/temple/park/etc",
          "lat": 0.0,
          "lng": 0.0,
          "start_time": "09:00",
          "end_time": "10:30",
          "estimated_cost": 200,
          "notes": "Brief note about the activity",
          "is_backup": false
        }}
      ],
      "meals": [
        {{
          "name": "Suggested meal type: regional dish or food area",
          "meal_type": "breakfast/lunch/dinner",
          "cuisine": "South Indian/etc",
          "estimated_cost": 300,
          "notes": "Brief note"
        }}
      ],
      "backup_activities": [
        {{
          "name": "Indoor alternative",
          "category": "museum",
          "lat": 0.0,
          "lng": 0.0,
          "start_time": "10:00",
          "end_time": "12:00",
          "estimated_cost": 150,
          "notes": "Good for rainy weather",
          "is_backup": true
        }}
      ]
    }}
  ],
  "tips": ["Useful travel tip 1", "Useful travel tip 2"]
}}"""

    return prompt


def _build_repair_prompt(issues: list[str], previous_plan: str) -> str:
    """Build a repair prompt when the plan has validation issues."""
    return f"""The previous itinerary plan has the following issues that need to be fixed:

ISSUES:
{chr(10).join(f'- {issue}' for issue in issues)}

PREVIOUS PLAN:
{previous_plan}

Please fix these issues and return the corrected plan in the EXACT SAME JSON format.
Only return valid JSON — no markdown, no explanations."""


def _minutes_since_midnight(value: object) -> Optional[int]:
    """Parse the compact HH:MM times returned by the itinerary model."""
    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", str(value or ""))
    return int(match.group(1)) * 60 + int(match.group(2)) if match else None


def _opening_window(value: object) -> Optional[tuple[int, int]]:
    """Handle the common OSM `09:00-17:00` shape; unknown formats stay unknown."""
    match = re.search(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", str(value or ""))
    if not match:
        return None
    start, end = (_minutes_since_midnight(part.zfill(5)) for part in match.groups())
    return (start, end) if start is not None and end is not None else None


def _summary_matches_activities(summary: object, activities: list[dict]) -> bool:
    """Catch claims such as 'shopping' when no corresponding stop exists."""
    text = str(summary or "").casefold()
    haystack = " ".join(
        f"{activity.get('name', '')} {activity.get('category', '')}".casefold()
        for activity in activities
    )
    claims = {
        "shopping": ("market", "bazaar", "shop", "mall"),
        "beach": ("beach",),
        "museum": ("museum", "gallery"),
        "temple": ("temple", "mandir", "worship"),
    }
    return all(not (word in text and not any(match in haystack for match in matches))
               for word, matches in claims.items())


def _normalize_place_name(value: object) -> str:
    """Normalize the names Gemini and map providers use for the same POI."""
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold())
    return " ".join(normalized.split())


def _activity_coordinates(activity: dict) -> Optional[GeoPoint]:
    """Read coordinates from the flat shape returned by Gemini, if present."""
    coordinates = activity.get("coordinates")
    if not isinstance(coordinates, dict):
        coordinates = activity
    try:
        lat = float(coordinates.get("lat"))
        lng = float(coordinates.get("lng"))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return GeoPoint(lat=lat, lng=lng)


def _resolve_approved_poi(
    activity: dict,
    approved_by_name: dict[str, dict],
    approved_pois: list[dict],
) -> Optional[dict]:
    """Resolve a model activity to reviewed/map data without trusting its name."""
    exact = approved_by_name.get(_normalize_place_name(activity.get("name")))
    if exact:
        return exact

    # Gemini sometimes returns a local alias or slightly different spelling.
    # Coordinates supplied in the same response let us safely map that alias to
    # a reviewed POI without accepting an arbitrary invented place.
    coordinates = _activity_coordinates(activity)
    if not coordinates:
        return None
    nearest = min(
        approved_pois,
        key=lambda poi: haversine_distance(
            coordinates,
            GeoPoint(**poi["coordinates"]),
        ),
        default=None,
    )
    if nearest and haversine_distance(coordinates, GeoPoint(**nearest["coordinates"])) <= COORDINATE_MATCH_RADIUS_KM:
        return nearest
    return None


def _default_meals(existing: object) -> list[dict]:
    """Keep the planner response usable when Gemini omits or invents meals."""
    meals = [deepcopy(meal) for meal in existing if isinstance(meal, dict)] if isinstance(existing, list) else []
    defaults = [
        ("breakfast", "local breakfast", 150),
        ("lunch", "regional lunch", 350),
        ("dinner", "local dinner", 500),
    ]
    existing_types = {str(meal.get("meal_type", "")).casefold() for meal in meals}
    for meal_type, label, cost in defaults:
        if len(meals) >= 3:
            break
        if meal_type not in existing_types:
            meals.append({
                "name": f"Suggested meal type: {label}",
                "meal_type": meal_type,
                "cuisine": "Indian",
                "estimated_cost": cost,
                "notes": "Restaurant verification unavailable",
            })
            existing_types.add(meal_type)
    while len(meals) < 2:
        meals.append({
            "name": "Suggested meal type: local meal",
            "meal_type": "meal",
            "cuisine": "Indian",
            "estimated_cost": 300,
            "notes": "Restaurant verification unavailable",
        })
    return meals


def _catalogue_activity(poi: dict, note: str = "") -> dict:
    coordinates = poi["coordinates"]
    duration = int(poi.get("estimated_visit_minutes", 60))
    return {
        "name": poi["name"],
        "category": poi.get("category", "attraction"),
        "lat": coordinates["lat"],
        "lng": coordinates["lng"],
        "start_time": "09:00",
        "end_time": f"{(9 * 60 + duration) // 60:02d}:{(9 * 60 + duration) % 60:02d}",
        "estimated_cost": int(poi.get("estimated_cost", 0)),
        "notes": note,
        "is_backup": False,
    }


def _canonicalize_plan(
    plan: object,
    request: TripRequest,
    approved_pois: list[dict],
) -> dict:
    """Make Gemini's flexible JSON safe before strict validation."""
    source = deepcopy(plan) if isinstance(plan, dict) else {}
    approved_by_name = {
        _normalize_place_name(poi.get("name")): poi
        for poi in approved_pois
        if poi.get("name")
    }
    expected_days = (request.end_date - request.start_date).days + 1
    days_by_number: dict[int, dict] = {}
    used_day_numbers: set[int] = set()

    raw_days = source.get("day_plans", [])
    if not isinstance(raw_days, list):
        raw_days = []

    for index, raw_day in enumerate(raw_days, start=1):
        if not isinstance(raw_day, dict):
            continue
        try:
            day_number = int(raw_day.get("day_number", index))
        except (TypeError, ValueError):
            day_number = index
        if day_number < 1 or day_number > expected_days or day_number in used_day_numbers:
            day_number = next(
                (candidate for candidate in range(1, expected_days + 1) if candidate not in used_day_numbers),
                index,
            )
        used_day_numbers.add(day_number)
        day = deepcopy(raw_day)
        day["day_number"] = day_number
        day["date"] = (request.start_date + timedelta(days=day_number - 1)).isoformat()
        changed = False

        for key in ("activities", "backup_activities"):
            cleaned: list[dict] = []
            raw_activities = day.get(key, [])
            if not isinstance(raw_activities, list):
                raw_activities = []
                changed = True
            for raw_activity in raw_activities:
                if not isinstance(raw_activity, dict):
                    changed = True
                    continue
                poi = _resolve_approved_poi(raw_activity, approved_by_name, approved_pois)
                if not poi:
                    logger.warning(
                        "Dropping itinerary activity not present in approved POIs: %s",
                        raw_activity.get("name"),
                    )
                    changed = True
                    continue
                activity = deepcopy(raw_activity)
                coordinates = poi["coordinates"]
                if _normalize_place_name(activity.get("name")) != _normalize_place_name(poi["name"]):
                    changed = True
                activity.update({
                    "name": poi["name"],
                    "category": poi.get("category", "attraction"),
                    "lat": coordinates["lat"],
                    "lng": coordinates["lng"],
                })
                if not isinstance(activity.get("estimated_cost"), (int, float)):
                    activity["estimated_cost"] = poi.get("estimated_cost", 0)
                cleaned.append(activity)
            day[key] = cleaned

        meals = day.get("meals", [])
        normalized_meals = _default_meals(meals)
        for meal in normalized_meals:
            name = str(meal.get("name", "")).strip()
            if name and not name.casefold().startswith("suggested meal type:"):
                if _normalize_place_name(name) not in approved_by_name:
                    meal["name"] = f"Suggested meal type: {meal.get('meal_type', 'local meal')}"
                    meal["notes"] = meal.get("notes") or "Restaurant verification unavailable"
                    changed = True
        day["meals"] = normalized_meals

        if changed:
            names = [activity["name"] for activity in day["activities"]]
            day["notes"] = f"Day {day_number}: {', '.join(names[:3])}" if names else f"Day {day_number} in {request.destination}"
        days_by_number[day_number] = day

    day_plans: list[dict] = []
    for day_number in range(1, expected_days + 1):
        day = days_by_number.get(day_number)
        if day is None:
            day = {
                "day_number": day_number,
                "date": (request.start_date + timedelta(days=day_number - 1)).isoformat(),
                "notes": f"Day {day_number} in {request.destination}",
                "activities": [],
                "meals": _default_meals([]),
                "backup_activities": [],
            }
        day_plans.append(day)

    used_names = {
        _normalize_place_name(activity.get("name"))
        for day in day_plans
        for activity in day.get("activities", [])
    }
    available_pois = [
        poi for poi in approved_pois
        if _normalize_place_name(poi.get("name")) not in used_names
    ] or approved_pois

    # An empty interior day is almost always a malformed model response. Give
    # it one reviewed stop so the user never receives a broken multi-day plan.
    for day in day_plans[1:-1]:
        if day.get("activities"):
            continue
        if not available_pois:
            break
        poi = available_pois.pop(0)
        day["activities"] = [_catalogue_activity(poi, "Added from the reviewed destination catalogue.")]
        day["notes"] = f"Day {day['day_number']}: {poi['name']}"
        used_names.add(_normalize_place_name(poi["name"]))

    source["day_plans"] = day_plans
    source["tips"] = source.get("tips", []) if isinstance(source.get("tips", []), list) else []
    return source


async def _repair_plan_schedule(
    plan: dict,
    approved_pois: list[dict],
    day_numbers: Optional[set[int]] = None,
) -> None:
    """Reflow activities around real route times before strict validation."""
    approved_by_name = {
        _normalize_place_name(poi.get("name")): poi
        for poi in approved_pois
        if poi.get("name")
    }
    for day in plan.get("day_plans", []):
        if day_numbers is not None:
            try:
                if int(day.get("day_number")) not in day_numbers:
                    continue
            except (TypeError, ValueError):
                continue
        activities = day.get("activities", [])
        if not isinstance(activities, list) or not activities:
            continue

        resolved: list[tuple[dict, dict, Optional[int], int]] = []
        for index, activity in enumerate(activities):
            if not isinstance(activity, dict):
                continue
            poi = _resolve_approved_poi(activity, approved_by_name, approved_pois)
            if poi:
                resolved.append((activity, poi, _minutes_since_midnight(activity.get("start_time")), index))
        resolved.sort(key=lambda item: (item[2] is None, item[2] or 0, item[3]))
        if not resolved:
            day["activities"] = []
            continue

        stops = [GeoPoint(**item[1]["coordinates"]) for item in resolved]
        durations = [
            max(15, int(item[0].get("duration_minutes") or item[1].get("estimated_visit_minutes", 60)))
            for item in resolved
        ]
        _, _, route_segments = await validate_day_feasibility(stops, durations)
        scheduled: list[dict] = []
        cursor = DEFAULT_ACTIVITY_START
        dropped = False

        for index, (activity, poi, original_start, _) in enumerate(resolved):
            travel_minutes = math.ceil(route_segments[index - 1].duration_minutes) if index and index - 1 < len(route_segments) else 0
            start = max(
                DEFAULT_ACTIVITY_START if index == 0 else cursor + travel_minutes + MIN_ROUTE_BUFFER_MINUTES,
                original_start or DEFAULT_ACTIVITY_START,
            )
            window = _opening_window(poi.get("opening_hours"))
            if window:
                start = max(start, window[0])
            duration = durations[index]
            end = start + duration
            if end > LATEST_ACTIVITY_END or (window and end > window[1]):
                dropped = True
                break

            updated = deepcopy(activity)
            updated["name"] = poi["name"]
            updated["start_time"] = f"{start // 60:02d}:{start % 60:02d}"
            updated["end_time"] = f"{end // 60:02d}:{end % 60:02d}"
            scheduled.append(updated)
            cursor = end

        if len(scheduled) != len(activities) or any(
            activity.get("start_time") != updated.get("start_time")
            or activity.get("end_time") != updated.get("end_time")
            for activity, updated in zip(activities, scheduled)
        ):
            day["activities"] = scheduled
            if dropped or scheduled:
                names = [activity["name"] for activity in scheduled]
                day["notes"] = f"Day {day.get('day_number')}: {', '.join(names[:3])}" if names else f"Day {day.get('day_number')}"


async def _validate_plan(
    plan: dict,
    request: TripRequest,
    approved_pois: list[dict],
) -> tuple[list[str], list[RouteSegment], dict[int, tuple[int, int]]]:
    """Validate real stop-to-stop travel, timings, opening windows, and summaries.

    The returned route segments and local-transport estimates are the same values
    used by the final itinerary, so the map and budget cannot drift from validation.
    """
    issues: list[str] = []
    route_segments: list[RouteSegment] = []
    local_transport: dict[int, tuple[int, int]] = {}
    approved_by_name = {
        _normalize_place_name(poi.get("name")): poi
        for poi in approved_pois if poi.get("name")
    }
    poi_names = set(approved_by_name)
    day_plans = plan.get("day_plans", [])

    expected_days = (request.end_date - request.start_date).days + 1
    pace_limit = max_activities_for_intent(build_trip_intent(request))
    if len(day_plans) != expected_days:
        issues.append(
            f"Plan has {len(day_plans)} days but trip is {expected_days} days"
        )

    for day in day_plans:
        day_number = day.get("day_number", "?")
        try:
            day_number_int = int(day_number)
        except (TypeError, ValueError):
            day_number_int = None
        meals = day.get("meals", [])
        if len(meals) < 2:
            issues.append(
                f"Day {day_number} has only {len(meals)} meals — need at least 2"
            )
        for meal in meals:
            raw_name = str(meal.get("name", "")).strip()
            name = _normalize_place_name(raw_name)
            if raw_name and not raw_name.casefold().startswith("suggested meal type:") and name not in poi_names:
                issues.append(
                    f"Day {day_number} meal '{meal.get('name')}' is not a verified place; use Suggested meal type instead"
                )

        activities = day.get("activities", [])
        if len(activities) > pace_limit:
            issues.append(
                f"Day {day_number} has {len(activities)} activities, above the {request.pace.value} pace limit of {pace_limit}"
            )
        if not activities and day_number_int not in [1, expected_days]:
            issues.append(
                f"Day {day_number} has no activities planned"
            )
        if not _summary_matches_activities(day.get("notes"), activities):
            issues.append(f"Day {day_number} summary describes something not present in its activities")

        stops: list[GeoPoint] = []
        visit_durations: list[int] = []
        previous_end: Optional[int] = None
        resolved_activities: list[tuple[dict, dict, int, int]] = []
        for activity in activities:
            poi = _resolve_approved_poi(activity, approved_by_name, approved_pois)
            if not poi:
                issues.append(f"Day {day_number} includes unverified activity '{activity.get('name')}'")
                continue
            start = _minutes_since_midnight(activity.get("start_time"))
            end = _minutes_since_midnight(activity.get("end_time"))
            if start is None or end is None or end <= start:
                issues.append(f"Day {day_number} has invalid timing for '{poi['name']}'")
                continue
            if previous_end is not None and start < previous_end:
                issues.append(f"Day {day_number} has overlapping activities around '{poi['name']}'")
            previous_end = end
            duration = max(15, int(activity.get("duration_minutes") or poi.get("estimated_visit_minutes", 60)))
            if end - start < duration:
                issues.append(f"Day {day_number} does not allow the stated visit time for '{poi['name']}'")
            window = _opening_window(poi.get("opening_hours"))
            if window and (start < window[0] or end > window[1]):
                issues.append(f"Day {day_number} schedules '{poi['name']}' outside its listed opening hours")
            coordinates = poi.get("coordinates", {})
            stops.append(GeoPoint(lat=coordinates["lat"], lng=coordinates["lng"]))
            visit_durations.append(duration)
            resolved_activities.append((activity, poi, start, end))

        feasible, total_hours, segments = await validate_day_feasibility(stops, visit_durations)
        for segment in segments:
            segment.day_number = int(day_number) if str(day_number).isdigit() else None
        route_segments.extend(segments)
        if stops and not feasible:
            issues.append(f"Day {day_number} needs {total_hours:.1f} hours including every stop-to-stop journey")
        for index, segment in enumerate(segments, start=1):
            previous = resolved_activities[index - 1]
            current = resolved_activities[index]
            earliest_arrival = previous[3] + math.ceil(segment.duration_minutes)
            if current[2] < earliest_arrival:
                issues.append(
                    f"Day {day_number} has insufficient travel time from '{previous[1]['name']}' to '{current[1]['name']}'"
                )
        if resolved_activities:
            span = resolved_activities[-1][3] - resolved_activities[0][2]
            if span > 12 * 60:
                issues.append(f"Day {day_number} exceeds the 12-hour itinerary window")
        distance = sum(segment.distance_km for segment in segments)
        minutes = math.ceil(sum(segment.duration_minutes for segment in segments))
        # Conservative local cab/auto estimate, including pickup minimums.
        local_transport[int(day_number)] = (minutes, int(math.ceil(distance * 18 + len(segments) * 30))) if str(day_number).isdigit() else (0, 0)

    return issues, route_segments, local_transport


async def _call_gemini(prompt: str, system: str = SYSTEM_PROMPT) -> Optional[dict]:
    """Call Gemini API and parse JSON response."""
    if not settings.gemini_api_key:
        logger.error("No Gemini API key configured")
        return None

    try:
        client = genai.Client(api_key=settings.gemini_api_key)

        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        text = response.text.strip()

        # Clean up potential markdown wrapping
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        if text.startswith("json"):
            text = text[4:]

        return json.loads(text.strip())

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return None


def _select_transport(
    options: list[TransportOption],
    requested_mode: Optional[TransportMode],
    distance_km: float,
    preference: TravelPreference = TravelPreference.BALANCED,
) -> Optional[TransportOption]:
    """Choose exactly one option before planning; this is also the budgeted option."""
    for option in options:
        option.is_recommended = False
    candidates = [option for option in options if not requested_mode or option.mode == requested_mode]
    if not candidates:
        return None
    if preference == TravelPreference.CHEAPEST:
        selected = min(candidates, key=lambda option: option.price)
    elif preference == TravelPreference.FASTEST:
        selected = min(candidates, key=lambda option: option.duration_minutes)
    elif requested_mode:
        selected = min(candidates, key=lambda option: option.price)
    elif distance_km < 500:
        selected = min((option for option in candidates if option.mode == TransportMode.TRAIN),
                       key=lambda option: option.price, default=min(candidates, key=lambda option: option.price))
    else:
        selected = min((option for option in candidates if option.mode == TransportMode.FLIGHT),
                       key=lambda option: option.price, default=min(candidates, key=lambda option: option.price))
    selected.is_recommended = True
    return selected


def _calculate_budget(
    day_plans: list[DayPlan], selected_transport: Optional[TransportOption], request: TripRequest
) -> BudgetBreakdown:
    """Authoritative arithmetic: LLM output never supplies a category or total."""
    travellers = request.adults + request.children
    # Transport, food, and admissions are supplied as per-traveller line items.
    outbound = selected_transport.price * travellers if selected_transport else 0
    returning = selected_transport.price * travellers if selected_transport else 0
    food = sum(meal.estimated_cost for day in day_plans for meal in day.meals) * travellers
    activities = sum(activity.estimated_cost for day in day_plans for activity in day.activities) * travellers
    between_stop_transport = sum(day.local_transport_cost for day in day_plans)
    # Return terminal transfers are not represented by POI-to-POI routes, but
    # are part of a credible trip total (station/airport/hotel pickup and drop).
    transfer_per_leg = {
        TransportMode.FLIGHT: 500,
        TransportMode.TRAIN: 250,
        TransportMode.ROAD: 150,
    }.get(selected_transport.mode if selected_transport else TransportMode.ROAD, 0)
    local_transport = between_stop_transport + transfer_per_leg * 2
    nights = max((request.end_date - request.start_date).days, 0)
    rooms = math.ceil(request.adults / 2)
    accommodation = nights * STAY_RATE_PER_NIGHT[request.accommodation_preference] * rooms
    subtotal = outbound + returning + accommodation + food + activities + local_transport
    taxes_buffer = math.ceil(subtotal * 0.05)
    total = subtotal + taxes_buffer
    return BudgetBreakdown(
        outbound_transport=outbound,
        return_transport=returning,
        transport=outbound + returning,
        food=food,
        activities=activities,
        accommodation=accommodation,
        local_transport=local_transport,
        taxes_buffer=taxes_buffer,
        miscellaneous=0,
        total_estimated=total,
        remaining=request.budget - total,
        provenance=_planner_estimate_provenance(
            "Budget totals are planning estimates assembled from transport, lodging, meal, activity, and local-transport inputs. Verify live prices, taxes, and booking fees before purchase.",
            provider="YatraAI deterministic budget calculator",
            confidence=0.9,
        ),
    )


def select_transport_for_itinerary(
    itinerary: Itinerary, mode: TransportMode, provider: str, code: Optional[str]
) -> Itinerary:
    """Apply a traveller choice and recalculate the authoritative trip budget."""
    selected = next(
        (
            option for option in itinerary.transport_options
            if option.mode == mode and option.provider == provider and option.code == code
        ),
        None,
    )
    if not selected:
        raise ValueError("That transport option is no longer available for this itinerary")
    for option in itinerary.transport_options:
        option.is_recommended = option is selected
    itinerary.selected_transport = selected
    if itinerary.day_plans:
        itinerary.day_plans[0].transport = selected
        itinerary.day_plans[-1].transport = selected
    request = TripRequest(
        origin=itinerary.origin.name,
        destination=itinerary.destination.name,
        start_date=itinerary.start_date,
        end_date=itinerary.end_date,
        budget=itinerary.budget.total_estimated + itinerary.budget.remaining,
        vibes=itinerary.vibes,
        transport_mode=mode,
        accommodation_preference=itinerary.accommodation_preference,
        adults=itinerary.adults,
        children=itinerary.children,
        travel_preference=itinerary.travel_preference,
        pace=itinerary.pace,
        dietary_preference=itinerary.dietary_preference,
        senior_citizens=itinerary.senior_citizens,
        accessibility_requirements=itinerary.accessibility_requirements,
        mandatory_places=itinerary.mandatory_places,
        excluded_places=itinerary.excluded_places,
        free_text_notes=itinerary.free_text_notes,
        allow_early_morning_travel=itinerary.allow_early_morning_travel,
        allow_late_night_travel=itinerary.allow_late_night_travel,
    )
    transport_issues = validate_transport_window(build_trip_intent(request), selected)
    if transport_issues:
        raise ValueError(transport_issues[0].message)
    itinerary.budget = _calculate_budget(itinerary.day_plans, selected, request)
    if itinerary.budget.remaining < 0:
        raise ValueError(
            f"That transport choice would exceed the trip budget by ₹{abs(itinerary.budget.remaining):,}."
        )
    itinerary.generation_notes = [note for note in itinerary.generation_notes if not note.startswith("Selected transport:")]
    itinerary.generation_notes.append(f"Selected transport: {selected.provider}; all transport totals use this option round trip.")
    return itinerary


def _plan_to_itinerary(
    plan: dict,
    request: TripRequest,
    origin: CityInfo,
    destination: CityInfo,
    transport_options: list[TransportOption],
    weather_forecast: list[DayWeather],
    route_segments: list[RouteSegment],
    notes: list[str],
    destination_photos: list[dict] | None = None,
    festivals: list[dict] | None = None,
    packing_list: list[dict] | None = None,
    approved_pois: list[dict] | None = None,
    selected_transport: Optional[TransportOption] = None,
    local_transport: dict[int, tuple[int, int]] | None = None,
) -> Itinerary:
    """Convert raw AI plan dict into structured Itinerary model."""

    total_days = (request.end_date - request.start_date).days + 1

    approved_by_name = {
        _normalize_place_name(poi.get("name")): poi
        for poi in approved_pois or []
        if poi.get("name")
    }

    def approved_activity(act: dict, is_backup: bool = False) -> Optional[Activity]:
        source_poi = _resolve_approved_poi(act, approved_by_name, approved_pois or [])
        if not source_poi:
            logger.warning("Discarding itinerary activity not present in approved POIs: %s", act.get("name"))
            return None
        coordinates = source_poi["coordinates"]
        cost = act.get("estimated_cost", source_poi.get("estimated_cost", 0))
        return Activity(
            poi=POI(
                name=source_poi["name"],
                category=source_poi.get("category", "attraction"),
                coordinates=GeoPoint(lat=coordinates["lat"], lng=coordinates["lng"]),
                osm_tags=source_poi.get("osm_tags"),
                estimated_visit_minutes=int(source_poi.get("estimated_visit_minutes", 60)),
                estimated_cost=cost,
                description=act.get("notes"),
                opening_hours=source_poi.get("opening_hours"),
                rating=source_poi.get("rating"),
                provenance=source_poi.get("provenance", {}),
                field_provenance=source_poi.get("field_provenance", {}),
            ),
            start_time=act.get("start_time"),
            end_time=act.get("end_time"),
            estimated_cost=cost,
            notes=act.get("notes"),
            is_backup=is_backup,
            is_locked=bool(act.get("is_locked", False)),
        )

    # Build day plans
    day_plans: list[DayPlan] = []
    for dp in plan.get("day_plans", []):
        day_num = dp.get("day_number", len(day_plans) + 1)
        day_date = request.start_date + timedelta(days=day_num - 1)

        # Match weather
        day_weather = None
        for w in weather_forecast:
            if w.date == day_date:
                day_weather = w
                break

        # Parse activities
        activities = []
        for act in dp.get("activities", []):
            activity = approved_activity(act, act.get("is_backup", False))
            if activity:
                activities.append(activity)

        # Parse backup activities
        backup_activities = []
        for act in dp.get("backup_activities", []):
            activity = approved_activity(act, True)
            if activity:
                backup_activities.append(activity)

        # Parse meals
        meals = []
        for meal in dp.get("meals", []):
            meal_name = meal.get("name", "Local food")
            source_poi = approved_by_name.get(_normalize_place_name(meal_name))
            meal_provenance = (
                source_poi.get("provenance", {})
                if source_poi
                else _planner_estimate_provenance(
                    "Meal venue, meal type, and price are estimates; verify the restaurant, dietary fit, and current menu before dining.",
                    confidence=0.45,
                ).model_dump(mode="json")
            )
            estimated_cost = meal.get("estimated_cost", 300)
            if not isinstance(estimated_cost, (int, float)):
                estimated_cost = 300
            meals.append(MealRecommendation(
                name=meal_name,
                cuisine=meal.get("cuisine"),
                meal_type=meal.get("meal_type", "lunch"),
                estimated_cost=int(estimated_cost),
                notes=meal.get("notes"),
                provenance=meal_provenance,
                field_provenance={
                    "estimated_cost": _planner_estimate_provenance(
                        "Meal cost is a per-traveller planning estimate; verify the current menu and taxes before dining.",
                        confidence=0.45,
                    ),
                },
            ))

        local_minutes, local_cost = (local_transport or {}).get(day_num, (0, 0))
        day_spent = sum(a.estimated_cost for a in activities) + sum(m.estimated_cost for m in meals) + local_cost

        day_plans.append(DayPlan(
            day_number=day_num,
            date=day_date,
            weather=day_weather,
            activities=activities,
            meals=meals,
            backup_activities=backup_activities,
            day_spent=day_spent,
            local_transport_minutes=local_minutes,
            local_transport_cost=local_cost,
            notes=dp.get("notes"),
        ))

    selected = selected_transport or next((opt for opt in transport_options if opt.is_recommended), None)
    budget_breakdown = _calculate_budget(day_plans, selected, request)
    if day_plans and selected:
        day_plans[0].transport = selected
        day_plans[-1].transport = selected

    # Tips from AI
    generation_notes = notes + plan.get("tips", [])

    return Itinerary(
        origin=origin,
        destination=destination,
        start_date=request.start_date,
        end_date=request.end_date,
        total_days=total_days,
        vibes=request.vibes,
        accommodation_preference=request.accommodation_preference,
        adults=request.adults,
        children=request.children,
        travel_preference=request.travel_preference,
        pace=request.pace,
        dietary_preference=request.dietary_preference,
        senior_citizens=request.senior_citizens,
        accessibility_requirements=request.accessibility_requirements,
        mandatory_places=request.mandatory_places,
        excluded_places=request.excluded_places,
        free_text_notes=request.free_text_notes,
        allow_early_morning_travel=request.allow_early_morning_travel,
        allow_late_night_travel=request.allow_late_night_travel,
        transport_options=transport_options,
        selected_transport=selected,
        day_plans=day_plans,
        budget=budget_breakdown,
        route_segments=route_segments,
        weather_forecast=weather_forecast,
        destination_photos=destination_photos or [],
        festivals=[FestivalEvent(**festival) for festival in festivals or []],
        packing_list=[PackingItem(**item) for item in packing_list or []],
        generation_notes=generation_notes,
    )


ProgressCallback = Callable[[str, str, int], Awaitable[None]]


async def generate_itinerary(
    request: TripRequest, progress: Optional[ProgressCallback] = None
) -> Itinerary:
    """
    Main orchestration function — generates a complete itinerary.

    1. Geocode cities
    2. Calculate distance → decide transport bias
    3. Search transport options (flights + trains)
    4. Discover POIs at destination
    5. Get weather forecast
    6. Call Gemini with real data
    7. Validate → repair loop
    8. Get route segments for map
    9. Return structured itinerary
    """
    import asyncio
    notes: list[str] = []

    async def report(step: str, message: str, percent: int) -> None:
        if progress:
            await progress(step, message, percent)

    # ── Step 1: Geocode (parallel) ────────────────────────────────────
    await report("geocoding", "Finding your origin and destination…", 12)
    logger.info(f"🗺️ Geocoding: {request.origin} → {request.destination}")

    origin_task = geocode_to_city_info(request.origin)
    dest_task = geocode_to_city_info(request.destination)
    origin, destination = await asyncio.gather(origin_task, dest_task)

    if not origin:
        raise ValueError(f"Could not find city: {request.origin}")
    if not destination:
        raise ValueError(f"Could not find city: {request.destination}")

    # ── Step 2: Distance ──────────────────────────────────────────────
    distance_km = haversine_distance(origin.coordinates, destination.coordinates)
    logger.info(f"📏 Distance: {distance_km:.0f} km")

    # ── Step 3: Parallel data fetching (transport + POI + weather + images) ─
    await report("trip_context", "Gathering transport, places, weather, and stay context…", 30)
    logger.info("🚂✈️📍🌤️🖼️ Fetching trip context in parallel...")

    await report("fetching_transport", "Checking flights, trains, and road options…", 32)
    transport_task = search_transport(
        origin=request.origin,
        destination=request.destination,
        date=request.start_date.isoformat(),
        budget=request.budget,
        distance_km=distance_km,
    )
    await report("fetching_places", "Finding places matching your interests…", 34)
    poi_task = discover_pois(
        lat=destination.coordinates.lat,
        lng=destination.coordinates.lng,
        vibes=[v.value for v in request.vibes],
        city=destination.name,
    )
    await report("fetching_weather", "Checking the forecast for your travel dates…", 36)
    weather_task = get_forecast(
        lat=destination.coordinates.lat,
        lng=destination.coordinates.lng,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
    )
    photos_task = get_destination_photos(destination.name)

    transport_result, pois, weather_data, photos = await asyncio.gather(
        transport_task, poi_task, weather_task, photos_task, return_exceptions=True,
    )
    # Festival intelligence is intentionally deferred until it can be backed by
    # a comprehensive, maintained source. Do not present partial dates as trip facts.
    festivals: list[dict] = []

    # Handle transport results
    if isinstance(transport_result, Exception):
        logger.warning(f"Transport search failed: {transport_result}")
        transport_options = []
    else:
        transport_options = transport_result

    if not transport_options:
        notes.append("No transport options found — plan covers destination activities only")
    else:
        fallback_count = sum(1 for t in transport_options if t.is_fallback)
        if fallback_count > 0:
            notes.append(f"{fallback_count} transport option(s) from estimated data")

    selected_transport = _select_transport(
        transport_options, request.transport_mode, distance_km, request.travel_preference
    )
    if request.transport_mode and not selected_transport:
        raise ValueError(f"No {request.transport_mode.value} option is available for this route")

    # Handle POI results
    if isinstance(pois, Exception):
        logger.warning(f"POI discovery failed: {pois}")
        pois = []
    if not pois:
        notes.append("Limited POI data — only reviewed or map-sourced places can be scheduled")

    # Handle weather results
    if isinstance(weather_data, Exception):
        logger.warning(f"Weather fetch failed: {weather_data}")
        weather_data = []

    weather_forecast = [DayWeather(**w) for w in weather_data] if weather_data else []
    if not weather_forecast:
        notes.append("Weather forecast unavailable — plan assumes good weather")

    if isinstance(photos, Exception):
        logger.warning(f"Destination photo search failed: {photos}")
        photos = []
    if not photos:
        notes.append("Destination photography is unavailable — add an Unsplash key to enable it")

    # ── Step 3.5: Deterministic constraint planning ────────────────────
    # This produces a machine-readable feasible candidate before Gemini is
    # asked to add language. The existing response contract remains intact;
    # Gemini's output is still canonicalized and independently validated below.
    intent = build_trip_intent(request)
    constraint_plan = ConstraintEngine().optimize(
        intent,
        pois,
        weather=weather_data or [],
        selected_transport=selected_transport,
    )
    deterministic_schedule = constraint_plan_to_raw_plan(constraint_plan)
    constraint_errors = [
        issue.message
        for issue in constraint_plan.issues
        if issue.severity.value == "error"
    ]
    if constraint_errors:
        notes.append(
            "The deterministic planner found constraints to review: "
            + "; ".join(constraint_errors[:2])
        )

    # ── Step 4: AI Planning ───────────────────────────────────────────
    await report("planning", "Building your day-by-day itinerary…", 58)
    logger.info("🤖 Generating itinerary with Gemini AI...")

    prompt = _build_planning_prompt(
        request=request,
        origin=origin,
        destination=destination,
        pois=pois,
        transport_options=[t.model_dump() for t in transport_options],
        weather=weather_data or [],
        distance_km=distance_km,
        festivals=festivals,
        selected_transport=selected_transport,
        deterministic_schedule=deterministic_schedule,
    )

    plan = await _call_gemini(prompt)

    if not plan:
        # Fallback: construct a basic plan without AI
        logger.warning("⚠️ Gemini unavailable — generating basic itinerary")
        notes.append("Generated without AI — basic itinerary from available data")
        plan = deterministic_schedule if constraint_plan.activities else _build_fallback_plan(request, pois, weather_data or [])

    # The model may return aliases, string day numbers, omitted meals, or an
    # empty interior day. Normalize those cases before strict validation, then
    # reflow each stop around the actual route times.
    plan = _canonicalize_plan(plan, request, pois)
    await _repair_plan_schedule(plan, pois)

    # ── Step 5: Validate & Repair ─────────────────────────────────────
    await report("validating", "Checking every stop, timing, and local journey…", 76)
    for iteration in range(MAX_REPAIR_ITERATIONS):
        issues, route_segments, local_transport = await _validate_plan(plan, request, pois)
        if not issues:
            logger.info(f"✅ Plan validated on iteration {iteration + 1}")
            break

        logger.info(f"🔧 Repair iteration {iteration + 1}: {len(issues)} issues")
        repair_prompt = _build_repair_prompt(issues, json.dumps(plan, default=str))
        repaired = await _call_gemini(repair_prompt)
        if repaired:
            plan = _canonicalize_plan(repaired, request, pois)
            await _repair_plan_schedule(plan, pois)
        else:
            notes.append(f"Plan has minor issues that couldn't be auto-fixed: {', '.join(issues[:3])}")
            break

    # A repaired plan needs its own complete route validation.  We retain the
    # segments from that same validation for the map and local transport budget.
    await report("routing", "Finalising routes and a fully calculated budget…", 90)
    issues, route_segments, local_transport = await _validate_plan(plan, request, pois)
    if issues:
        # A deterministic plan is preferable to showing a validation error
        # when the AI response remains malformed after its repair attempts.
        logger.warning("AI itinerary remained invalid; using deterministic fallback: %s", issues)
        fallback_plan = _canonicalize_plan(
            _build_fallback_plan(request, pois, weather_data or []),
            request,
            pois,
        )
        await _repair_plan_schedule(fallback_plan, pois)
        fallback_issues, fallback_segments, fallback_local_transport = await _validate_plan(
            fallback_plan,
            request,
            pois,
        )
        if fallback_issues:
            logger.warning("Deterministic itinerary also failed validation: %s", fallback_issues)
            raise ValueError("Could not generate a feasible itinerary: " + "; ".join(fallback_issues[:3]))
        plan = fallback_plan
        route_segments = fallback_segments
        local_transport = fallback_local_transport
        notes.append("The first AI draft needed correction, so a verified itinerary was generated instead.")

    # ── Step 7: Build Itinerary ───────────────────────────────────────
    itinerary = _plan_to_itinerary(
        plan=plan,
        request=request,
        origin=origin,
        destination=destination,
        transport_options=transport_options,
        weather_forecast=weather_forecast,
        route_segments=route_segments,
        notes=notes,
        destination_photos=photos,
        festivals=festivals,
        approved_pois=pois,
        selected_transport=selected_transport,
        local_transport=local_transport,
    )

    if itinerary.budget.remaining < 0:
        itinerary.generation_notes.append(
            f"The deterministic estimate is ₹{abs(itinerary.budget.remaining):,} above the requested budget; "
            "remove an optional stop or choose a lower-cost transport option before booking."
        )

    logger.info(f"✨ Itinerary generated: {itinerary.total_days} days, "
                f"₹{itinerary.budget.total_estimated:,} estimated")
    await report("ready", "Your itinerary is ready.", 98)

    return itinerary


def _build_fallback_plan(
    request: TripRequest,
    pois: list[dict],
    weather: list[dict],
) -> dict:
    """Build a basic plan without AI when Gemini is unavailable."""
    total_days = (request.end_date - request.start_date).days + 1

    day_plans = []
    poi_idx = 0

    for day_num in range(1, total_days + 1):
        day_date = request.start_date + timedelta(days=day_num - 1)
        activities = []
        next_start = 9 * 60

        # Add 3-4 POIs per day
        for _ in range(min(4, len(pois) - poi_idx)):
            if poi_idx >= len(pois):
                break
            poi = pois[poi_idx]
            poi_idx += 1
            visit_minutes = int(poi.get("estimated_visit_minutes", 60))
            end_minutes = next_start + visit_minutes
            activities.append({
                "name": poi.get("name", "Unknown"),
                "category": poi.get("category", "attraction"),
                "lat": poi.get("coordinates", {}).get("lat", 0),
                "lng": poi.get("coordinates", {}).get("lng", 0),
                "start_time": f"{next_start // 60:02d}:{next_start % 60:02d}",
                "end_time": f"{end_minutes // 60:02d}:{end_minutes % 60:02d}",
                "estimated_cost": poi.get("estimated_cost", 100),
                "notes": "",
                "is_backup": False,
            })
            next_start = end_minutes + 30

        meals = [
            {"name": "Suggested meal type: local breakfast", "meal_type": "breakfast", "cuisine": "Indian", "estimated_cost": 150, "notes": "Restaurant verification unavailable"},
            {"name": "Suggested meal type: regional lunch", "meal_type": "lunch", "cuisine": "Indian", "estimated_cost": 350, "notes": "Restaurant verification unavailable"},
            {"name": "Suggested meal type: local dinner", "meal_type": "dinner", "cuisine": "Indian", "estimated_cost": 500, "notes": "Restaurant verification unavailable"},
        ]

        day_plans.append({
            "day_number": day_num,
            "date": day_date.isoformat(),
            "notes": f"Day {day_num} in {request.destination}",
            "activities": activities,
            "meals": meals,
            "backup_activities": [],
        })

    return {
        "day_plans": day_plans,
        "tips": ["This is a basic itinerary — add your Gemini API key for AI-powered planning"],
    }


def _itinerary_to_plan(itinerary: Itinerary) -> dict:
    """Convert a persisted itinerary into the Gemini plan shape for refinement."""

    def activity_payload(activity: Activity, *, is_backup: bool) -> dict:
        start = _minutes_since_midnight(activity.start_time)
        end = _minutes_since_midnight(activity.end_time)
        duration = end - start if start is not None and end is not None and end > start else activity.poi.estimated_visit_minutes
        return {
            "name": activity.poi.name,
            "category": activity.poi.category,
            "lat": activity.poi.coordinates.lat,
            "lng": activity.poi.coordinates.lng,
            "start_time": activity.start_time,
            "end_time": activity.end_time,
            "duration_minutes": max(15, int(duration or 60)),
            "estimated_cost": activity.estimated_cost,
            "notes": activity.notes,
            "is_backup": is_backup,
            "is_locked": activity.is_locked,
        }

    return {
        "day_plans": [
            {
                "day_number": day.day_number,
                "date": day.date.isoformat(),
                "notes": day.notes,
                "activities": [activity_payload(activity, is_backup=activity.is_backup) for activity in day.activities],
                "meals": [meal.model_dump() for meal in day.meals],
                "backup_activities": [activity_payload(activity, is_backup=True) for activity in day.backup_activities],
            }
            for day in itinerary.day_plans
        ],
        "tips": itinerary.generation_notes,
    }


def _merge_scoped_plan_days(
    original: dict,
    candidate: dict,
    affected_days: set[int],
) -> dict:
    """Merge a model edit without allowing unrelated days to drift."""

    merged = deepcopy(original)
    candidate_by_day: dict[int, dict] = {}
    for index, day in enumerate(candidate.get("day_plans", []) if isinstance(candidate, dict) else [], start=1):
        if not isinstance(day, dict):
            continue
        try:
            day_number = int(day.get("day_number", index))
        except (TypeError, ValueError):
            day_number = index
        candidate_by_day[day_number] = day
    for day in merged.get("day_plans", []):
        if not isinstance(day, dict):
            continue
        try:
            day_number = int(day.get("day_number", 0))
        except (TypeError, ValueError):
            continue
        if day_number in affected_days and day_number in candidate_by_day:
            replacement = deepcopy(candidate_by_day[day_number])
            replacement["day_number"] = day_number
            day.clear()
            day.update(replacement)
    if isinstance(candidate, dict) and isinstance(candidate.get("tips"), list):
        merged["tips"] = candidate["tips"]
    return merged


async def refine_itinerary(itinerary: Itinerary, instruction: str) -> Itinerary:
    """Apply a scoped, revalidated change without regenerating unrelated days."""
    request = TripRequest(
        origin=itinerary.origin.name,
        destination=itinerary.destination.name,
        start_date=itinerary.start_date,
        end_date=itinerary.end_date,
        budget=itinerary.budget.total_estimated + itinerary.budget.remaining,
        vibes=itinerary.vibes,
        transport_mode=itinerary.selected_transport.mode if itinerary.selected_transport else None,
        accommodation_preference=itinerary.accommodation_preference,
        adults=itinerary.adults,
        children=itinerary.children,
        travel_preference=itinerary.travel_preference,
        pace=itinerary.pace,
        dietary_preference=itinerary.dietary_preference,
        senior_citizens=itinerary.senior_citizens,
        accessibility_requirements=itinerary.accessibility_requirements,
        mandatory_places=itinerary.mandatory_places,
        excluded_places=itinerary.excluded_places,
        free_text_notes=itinerary.free_text_notes,
        allow_early_morning_travel=itinerary.allow_early_morning_travel,
        allow_late_night_travel=itinerary.allow_late_night_travel,
    )
    existing_plan = _itinerary_to_plan(itinerary)
    refinement = parse_refinement_instruction(instruction)

    if refinement.action == RefinementAction.CHANGE_TRANSPORT and refinement.transport_mode:
        try:
            mode = TransportMode(refinement.transport_mode)
        except ValueError:
            mode = None
        if mode:
            option = next((item for item in itinerary.transport_options if item.mode == mode), None)
            if option:
                updated = select_transport_for_itinerary(itinerary, mode, option.provider, option.code)
                updated.generation_notes.append(f"Transport changed by refinement: {mode.value}.")
                return updated
        itinerary.generation_notes.append(
            f"Could not apply the requested transport change: {refinement.transport_mode}."
        )
        return itinerary

    approved_pois = [
        activity.poi.model_dump()
        for day_plan in itinerary.day_plans
        for activity in [*day_plan.activities, *day_plan.backup_activities]
    ]

    if refinement.action in {
        RefinementAction.ADD_ACTIVITY,
        RefinementAction.ADD_CUSTOM_ACTIVITY,
        RefinementAction.REPLACE_ACTIVITY,
    } and refinement.replacement:
        replacement_name = refinement.replacement.strip()
        if not any(_normalize_place_name(poi.get("name")) == _normalize_place_name(replacement_name) for poi in approved_pois):
            custom_provenance = _planner_estimate_provenance(
                "This is a traveller-added place or activity without provider verification; confirm its location, hours, and cost before visiting.",
                confidence=0.2,
            ).model_dump(mode="json")
            approved_pois.append({
                "id": f"custom-{_normalize_place_name(replacement_name).replace(' ', '-')[:40]}",
                "name": replacement_name,
                "category": "custom activity",
                "coordinates": itinerary.destination.coordinates.model_dump(),
                "estimated_visit_minutes": 60,
                "estimated_cost": 0,
                "description": "Added by the traveller.",
                "opening_hours": None,
                "provenance": custom_provenance,
                "field_provenance": {},
            })

    deterministic_plan, changed_days, changed = apply_scoped_refinement(existing_plan, refinement)
    if changed:
        await _repair_plan_schedule(deterministic_plan, approved_pois, changed_days)
        issues, route_segments, local_transport = await _validate_plan(
            deterministic_plan,
            request,
            approved_pois,
        )
        if not issues:
            refined = _plan_to_itinerary(
                plan=deterministic_plan,
                request=request,
                origin=itinerary.origin,
                destination=itinerary.destination,
                transport_options=itinerary.transport_options,
                weather_forecast=itinerary.weather_forecast,
                route_segments=route_segments,
                notes=[*itinerary.generation_notes, f"Deterministic refinement applied: {instruction}"],
                destination_photos=[photo.model_dump() for photo in itinerary.destination_photos],
                festivals=[festival.model_dump() for festival in itinerary.festivals],
                packing_list=[item.model_dump() for item in itinerary.packing_list],
                approved_pois=approved_pois,
                selected_transport=itinerary.selected_transport,
                local_transport=local_transport,
            )
            if refined.budget.remaining < 0:
                itinerary.generation_notes.append(
                    "The requested refinement exceeded the trip budget, so the previous itinerary was preserved."
                )
                return itinerary
            refined.id = itinerary.id
            return refined

    affected_days = changed_days or (
        {refinement.day_number}
        if refinement.action == RefinementAction.REGENERATE_DAY and refinement.day_number is not None
        else {
        int(day.get("day_number", index))
        for index, day in enumerate(existing_plan.get("day_plans", []), start=1)
        if isinstance(day, dict)
        }
    )
    prompt = f"""Update this India itinerary according to the traveller's request.

TRAVELLER REQUEST: {instruction}

CURRENT ITINERARY JSON:
{json.dumps(existing_plan, indent=2, default=str)}

Only modify day(s) {sorted(affected_days)}. Copy every other day exactly,
including activity order, times, costs, meals, notes, and backups. Keep dates and
the overall JSON schema unchanged. Preserve useful activities unless the request
asks to replace them. Keep costs realistic in INR, retain three meals per day,
and return ONLY a valid JSON object matching the current itinerary schema.
"""
    refined_plan = await _call_gemini(prompt)
    if not refined_plan:
        itinerary.generation_notes.append("Could not apply that AI refinement right now. Please try again.")
        return itinerary

    refined_plan = _canonicalize_plan(refined_plan, request, approved_pois)
    refined_plan = _merge_scoped_plan_days(existing_plan, refined_plan, affected_days)
    await _repair_plan_schedule(refined_plan, approved_pois, affected_days)
    issues, route_segments, local_transport = await _validate_plan(refined_plan, request, approved_pois)
    if issues:
        repaired = await _call_gemini(_build_repair_prompt(issues, json.dumps(refined_plan, default=str)))
        if repaired:
            repaired = _canonicalize_plan(repaired, request, approved_pois)
            refined_plan = _merge_scoped_plan_days(existing_plan, repaired, affected_days)
            await _repair_plan_schedule(refined_plan, approved_pois, affected_days)
            issues, route_segments, local_transport = await _validate_plan(refined_plan, request, approved_pois)

    if issues:
        itinerary.generation_notes.append(
            "The requested refinement was not feasible, so the previous itinerary was preserved."
        )
        return itinerary

    refined = _plan_to_itinerary(
        plan=refined_plan,
        request=request,
        origin=itinerary.origin,
        destination=itinerary.destination,
        transport_options=itinerary.transport_options,
        weather_forecast=itinerary.weather_forecast,
        route_segments=route_segments,
        notes=[*itinerary.generation_notes, f"AI refinement applied: {instruction}"],
        destination_photos=[photo.model_dump() for photo in itinerary.destination_photos],
        festivals=[festival.model_dump() for festival in itinerary.festivals],
        packing_list=[item.model_dump() for item in itinerary.packing_list],
        approved_pois=approved_pois,
        selected_transport=itinerary.selected_transport,
        local_transport=local_transport,
    )
    if refined.budget.remaining < 0:
        itinerary.generation_notes.append(
            "The requested refinement exceeded the trip budget, so the previous itinerary was preserved."
        )
        return itinerary
    refined.id = itinerary.id
    return refined


async def generate_packing_list(itinerary: Itinerary) -> list[PackingItem]:
    """Generate a concise, context-aware packing checklist with an offline fallback."""
    prompt = f"""Create a practical packing list for this India trip.
Destination: {itinerary.destination.name}, {itinerary.destination.state or 'India'}
Dates: {itinerary.start_date} to {itinerary.end_date}
Vibes: {', '.join(v.value for v in itinerary.vibes)}
Weather: {json.dumps([weather.model_dump(mode='json') for weather in itinerary.weather_forecast], default=str)}

Return ONLY JSON: {{"items": [{{"item": "", "reason": "", "category": "essentials|clothing|health|activity"}}]}}.
Include 8–14 specific, practical items; avoid generic filler."""
    response = await _call_gemini(prompt)
    if response and isinstance(response.get("items"), list):
        items = [PackingItem(**item) for item in response["items"][:14] if item.get("item")]
        if items:
            return items

    month = itinerary.start_date.month
    seasonal_item = (
        PackingItem(item="Light rain jacket", reason="Monsoon showers are common during this season.", category="clothing")
        if month in {6, 7, 8, 9}
        else PackingItem(item="Sunscreen and cap", reason="Useful for long daytime sightseeing.", category="health")
    )
    return [
        PackingItem(item="Government photo ID", reason="Required for transport and many hotels."),
        PackingItem(item="Reusable water bottle", reason="Stay hydrated while sightseeing."),
        PackingItem(item="Comfortable walking shoes", reason="Most itineraries involve substantial walking.", category="clothing"),
        PackingItem(item="Power bank and charging cable", reason="Maps, tickets, and photos use battery.", category="essentials"),
        seasonal_item,
    ]
