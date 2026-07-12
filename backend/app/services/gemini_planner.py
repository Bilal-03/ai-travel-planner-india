"""
Gemini AI Planner — the core orchestration service.
Generates day-by-day itineraries using real data from all other services,
with a propose → validate → repair loop for quality assurance.
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

from google import genai
from google.genai import types

from app.cache.redis_cache import cached
from app.config import settings
from app.models.trip import (
    Activity,
    BudgetBreakdown,
    DayPlan,
    DayWeather,
    GeoPoint,
    Itinerary,
    CityInfo,
    MealRecommendation,
    POI,
    RouteSegment,
    TransportOption,
    TravelVibe,
    TripRequest,
    WeatherSeverity,
)
from app.services.geocoding import geocode_to_city_info, haversine_distance
from app.services.poi_discovery import discover_pois
from app.services.routing import get_route_segment, validate_day_feasibility
from app.services.transport import search_transport
from app.services.weather import get_forecast

logger = logging.getLogger(__name__)

MAX_REPAIR_ITERATIONS = 0

SYSTEM_PROMPT = """You are an expert India domestic travel planner. You create detailed, practical, 
budget-conscious day-by-day itineraries for travelers within India.

IMPORTANT RULES:
1. All costs must be in INR (₹). Use realistic Indian prices.
2. Plan activities from 8:00 AM to 8:00 PM max per day.
3. Allow 30-60 min between activities for travel time.
4. Include 3 meals per day (breakfast, lunch, dinner) with estimated costs.
5. Budget meal costs realistically: street food ₹50-150, casual dining ₹200-500, fine dining ₹800-2000.
6. If weather is rainy, prioritize indoor activities and include backup options.
7. Respect the user's travel vibe preferences.
8. First and last days may have reduced activities due to travel.
9. Suggest specific, real places — not generic "visit a temple".
10. Include estimated costs for every activity and meal.

You MUST respond with valid JSON matching the exact schema provided. No markdown, no explanations — ONLY JSON."""


def _build_planning_prompt(
    request: TripRequest,
    origin: CityInfo,
    destination: CityInfo,
    pois: list[dict],
    transport_options: list[dict],
    weather: list[dict],
    distance_km: float,
) -> str:
    """Build the grounded planning prompt with real data."""

    total_days = (request.end_date - request.start_date).days + 1

    # Estimate transport cost from best option
    transport_cost = 0
    if transport_options:
        cheapest = min(transport_options, key=lambda t: t.get("price", 99999))
        transport_cost = cheapest.get("price", 0) * 2  # Round trip

    daily_budget = (request.budget - transport_cost) // max(total_days, 1)

    prompt = f"""Plan a {total_days}-day trip from {origin.name} to {destination.name}.

TRIP DETAILS:
- Dates: {request.start_date} to {request.end_date} ({total_days} days)
- Total Budget: ₹{request.budget:,}
- Transport Budget (round trip estimate): ₹{transport_cost:,}
- Daily Budget for activities + food: ₹{daily_budget:,}
- Vibes: {', '.join(v.value for v in request.vibes)}
- Distance: {distance_km:.0f} km

AVAILABLE POIs AT {destination.name.upper()} (real data from OpenStreetMap):
{json.dumps(pois[:20], indent=2, default=str)}

TRANSPORT OPTIONS (real data):
{json.dumps(transport_options[:5], indent=2, default=str)}

WEATHER FORECAST:
{json.dumps(weather, indent=2, default=str)}

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
          "name": "Restaurant/food spot name",
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
  "budget_breakdown": {{
    "transport": {transport_cost},
    "food": 0,
    "activities": 0,
    "accommodation": 0,
    "miscellaneous": 0
  }},
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


def _validate_plan(plan: dict, request: TripRequest) -> list[str]:
    """Validate the generated plan for budget and feasibility issues."""
    issues = []

    day_plans = plan.get("day_plans", [])
    budget = plan.get("budget_breakdown", {})

    # Check total cost vs budget
    total_cost = sum(budget.values())
    if total_cost > request.budget * 1.1:  # 10% tolerance
        issues.append(
            f"Total estimated cost (₹{total_cost:,}) exceeds budget (₹{request.budget:,}) by more than 10%"
        )

    # Check day count
    expected_days = (request.end_date - request.start_date).days + 1
    if len(day_plans) != expected_days:
        issues.append(
            f"Plan has {len(day_plans)} days but trip is {expected_days} days"
        )

    # Check each day has meals
    for day in day_plans:
        meals = day.get("meals", [])
        if len(meals) < 2:
            issues.append(
                f"Day {day.get('day_number', '?')} has only {len(meals)} meals — need at least 2"
            )

        activities = day.get("activities", [])
        if not activities and day.get("day_number", 1) not in [1, expected_days]:
            issues.append(
                f"Day {day.get('day_number', '?')} has no activities planned"
            )

    return issues


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


def _plan_to_itinerary(
    plan: dict,
    request: TripRequest,
    origin: CityInfo,
    destination: CityInfo,
    transport_options: list[TransportOption],
    weather_forecast: list[DayWeather],
    route_segments: list[RouteSegment],
    notes: list[str],
) -> Itinerary:
    """Convert raw AI plan dict into structured Itinerary model."""

    total_days = (request.end_date - request.start_date).days + 1

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
            activities.append(Activity(
                poi=POI(
                    name=act.get("name", "Unknown"),
                    category=act.get("category", "attraction"),
                    coordinates=GeoPoint(
                        lat=act.get("lat", destination.coordinates.lat),
                        lng=act.get("lng", destination.coordinates.lng),
                    ),
                    estimated_cost=act.get("estimated_cost", 0),
                    description=act.get("notes"),
                ),
                start_time=act.get("start_time"),
                end_time=act.get("end_time"),
                estimated_cost=act.get("estimated_cost", 0),
                notes=act.get("notes"),
                is_backup=act.get("is_backup", False),
            ))

        # Parse backup activities
        backup_activities = []
        for act in dp.get("backup_activities", []):
            backup_activities.append(Activity(
                poi=POI(
                    name=act.get("name", "Unknown"),
                    category=act.get("category", "attraction"),
                    coordinates=GeoPoint(
                        lat=act.get("lat", destination.coordinates.lat),
                        lng=act.get("lng", destination.coordinates.lng),
                    ),
                    estimated_cost=act.get("estimated_cost", 0),
                    description=act.get("notes"),
                ),
                start_time=act.get("start_time"),
                end_time=act.get("end_time"),
                estimated_cost=act.get("estimated_cost", 0),
                notes=act.get("notes"),
                is_backup=True,
            ))

        # Parse meals
        meals = []
        for meal in dp.get("meals", []):
            meals.append(MealRecommendation(
                name=meal.get("name", "Local food"),
                cuisine=meal.get("cuisine"),
                meal_type=meal.get("meal_type", "lunch"),
                estimated_cost=meal.get("estimated_cost", 300),
                notes=meal.get("notes"),
            ))

        # Calculate day spending
        day_spent = sum(a.estimated_cost for a in activities) + sum(m.estimated_cost for m in meals)

        day_plans.append(DayPlan(
            day_number=day_num,
            date=day_date,
            weather=day_weather,
            activities=activities,
            meals=meals,
            backup_activities=backup_activities,
            day_spent=day_spent,
            notes=dp.get("notes"),
        ))

    # Build budget breakdown
    budget_data = plan.get("budget_breakdown", {})
    total_food = sum(dp.day_spent for dp in day_plans)
    budget_breakdown = BudgetBreakdown(
        transport=budget_data.get("transport", 0),
        food=budget_data.get("food", total_food),
        activities=budget_data.get("activities", 0),
        accommodation=budget_data.get("accommodation", 0),
        miscellaneous=budget_data.get("miscellaneous", 0),
    )
    budget_breakdown.total_estimated = (
        budget_breakdown.transport + budget_breakdown.food +
        budget_breakdown.activities + budget_breakdown.accommodation +
        budget_breakdown.miscellaneous
    )
    budget_breakdown.remaining = request.budget - budget_breakdown.total_estimated

    # Select recommended transport
    selected = None
    for opt in transport_options:
        if opt.is_recommended:
            selected = opt
            break
    if not selected and transport_options:
        selected = transport_options[0]

    # Tips from AI
    generation_notes = notes + plan.get("tips", [])

    return Itinerary(
        origin=origin,
        destination=destination,
        start_date=request.start_date,
        end_date=request.end_date,
        total_days=total_days,
        vibes=request.vibes,
        transport_options=transport_options,
        selected_transport=selected,
        day_plans=day_plans,
        budget=budget_breakdown,
        route_segments=route_segments,
        weather_forecast=weather_forecast,
        generation_notes=generation_notes,
    )


async def generate_itinerary(request: TripRequest) -> Itinerary:
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

    # ── Step 1: Geocode (parallel) ────────────────────────────────────
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

    # ── Step 3: Parallel data fetching (transport + POI + weather) ────
    logger.info("🚂✈️📍🌤️ Fetching transport, POIs, and weather in parallel...")

    transport_task = search_transport(
        origin=request.origin,
        destination=request.destination,
        date=request.start_date.isoformat(),
        budget=request.budget,
        distance_km=distance_km,
    )
    poi_task = discover_pois(
        lat=destination.coordinates.lat,
        lng=destination.coordinates.lng,
        vibes=[v.value for v in request.vibes],
    )
    weather_task = get_forecast(
        lat=destination.coordinates.lat,
        lng=destination.coordinates.lng,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
    )

    transport_result, pois, weather_data = await asyncio.gather(
        transport_task, poi_task, weather_task, return_exceptions=True,
    )

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

    # Handle POI results
    if isinstance(pois, Exception):
        logger.warning(f"POI discovery failed: {pois}")
        pois = []
    if not pois:
        notes.append("Limited POI data from OpenStreetMap — AI will supplement with knowledge")

    # Handle weather results
    if isinstance(weather_data, Exception):
        logger.warning(f"Weather fetch failed: {weather_data}")
        weather_data = []

    weather_forecast = [DayWeather(**w) for w in weather_data] if weather_data else []
    if not weather_forecast:
        notes.append("Weather forecast unavailable — plan assumes good weather")

    # ── Step 4: AI Planning ───────────────────────────────────────────
    logger.info("🤖 Generating itinerary with Gemini AI...")

    prompt = _build_planning_prompt(
        request=request,
        origin=origin,
        destination=destination,
        pois=pois,
        transport_options=[t.model_dump() for t in transport_options],
        weather=weather_data or [],
        distance_km=distance_km,
    )

    plan = await _call_gemini(prompt)

    if not plan:
        # Fallback: construct a basic plan without AI
        logger.warning("⚠️ Gemini unavailable — generating basic itinerary")
        notes.append("Generated without AI — basic itinerary from available data")
        plan = _build_fallback_plan(request, pois, weather_data or [])

    # ── Step 5: Validate & Repair ─────────────────────────────────────
    for iteration in range(MAX_REPAIR_ITERATIONS):
        issues = _validate_plan(plan, request)
        if not issues:
            logger.info(f"✅ Plan validated on iteration {iteration + 1}")
            break

        logger.info(f"🔧 Repair iteration {iteration + 1}: {len(issues)} issues")
        repair_prompt = _build_repair_prompt(issues, json.dumps(plan, default=str))
        repaired = await _call_gemini(repair_prompt)
        if repaired:
            plan = repaired
        else:
            notes.append(f"Plan has minor issues that couldn't be auto-fixed: {', '.join(issues[:3])}")
            break

    # ── Step 6: Route Segments (limited, parallel) ────────────────────
    logger.info("🗺️ Computing route segments...")
    route_pairs: list[tuple[GeoPoint, GeoPoint]] = []

    for dp in plan.get("day_plans", []):
        activities = dp.get("activities", [])
        if len(activities) >= 2:
            first = activities[0]
            last = activities[-1]
            if first.get("lat") and last.get("lat"):
                route_pairs.append((
                    GeoPoint(lat=first["lat"], lng=first["lng"]),
                    GeoPoint(lat=last["lat"], lng=last["lng"]),
                ))
        if len(route_pairs) >= 5:
            break

    # Fetch route segments in parallel
    if route_pairs:
        route_tasks = [
            get_route_segment(from_pt, to_pt)
            for from_pt, to_pt in route_pairs
        ]
        route_results = await asyncio.gather(*route_tasks, return_exceptions=True)
        route_segments = [
            seg for seg in route_results
            if isinstance(seg, RouteSegment)
        ]
    else:
        route_segments = []

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
    )

    logger.info(f"✨ Itinerary generated: {itinerary.total_days} days, "
                f"₹{itinerary.budget.total_estimated:,} estimated")

    return itinerary


def _build_fallback_plan(
    request: TripRequest,
    pois: list[dict],
    weather: list[dict],
) -> dict:
    """Build a basic plan without AI when Gemini is unavailable."""
    total_days = (request.end_date - request.start_date).days + 1
    daily_budget = request.budget // max(total_days, 1)

    day_plans = []
    poi_idx = 0

    for day_num in range(1, total_days + 1):
        day_date = request.start_date + timedelta(days=day_num - 1)
        activities = []

        # Add 3-4 POIs per day
        for _ in range(min(4, len(pois) - poi_idx)):
            if poi_idx >= len(pois):
                break
            poi = pois[poi_idx]
            poi_idx += 1
            activities.append({
                "name": poi.get("name", "Unknown"),
                "category": poi.get("category", "attraction"),
                "lat": poi.get("coordinates", {}).get("lat", 0),
                "lng": poi.get("coordinates", {}).get("lng", 0),
                "start_time": f"{9 + len(activities) * 2:02d}:00",
                "end_time": f"{10 + len(activities) * 2:02d}:00",
                "estimated_cost": poi.get("estimated_cost", 100),
                "notes": "",
                "is_backup": False,
            })

        meals = [
            {"name": "Local breakfast spot", "meal_type": "breakfast", "cuisine": "Indian", "estimated_cost": 150, "notes": ""},
            {"name": "Local restaurant", "meal_type": "lunch", "cuisine": "Indian", "estimated_cost": 350, "notes": ""},
            {"name": "Dinner restaurant", "meal_type": "dinner", "cuisine": "Indian", "estimated_cost": 500, "notes": ""},
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
        "budget_breakdown": {
            "transport": 0,
            "food": daily_budget * total_days // 3,
            "activities": daily_budget * total_days // 3,
            "accommodation": daily_budget * total_days // 4,
            "miscellaneous": daily_budget * total_days // 12,
        },
        "tips": ["This is a basic itinerary — add your Gemini API key for AI-powered planning"],
    }
