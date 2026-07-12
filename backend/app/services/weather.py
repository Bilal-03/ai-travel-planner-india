"""
Weather service — OpenWeatherMap.
Fetches 5-day forecast and categorizes days for itinerary planning.
"""

import logging
from datetime import date, datetime
from typing import Optional

import httpx

from app.cache.redis_cache import cached
from app.config import settings
from app.models.trip import DayWeather, WeatherSeverity

logger = logging.getLogger(__name__)

OWM_BASE = "https://api.openweathermap.org/data/2.5"


def _classify_severity(condition: str, rain_prob: float) -> WeatherSeverity:
    """Classify weather severity for activity planning."""
    rain_keywords = {"rain", "thunderstorm", "drizzle", "snow", "squall", "tornado"}
    if any(k in condition.lower() for k in rain_keywords) or rain_prob > 0.6:
        return WeatherSeverity.INDOOR
    if rain_prob > 0.3 or "cloud" in condition.lower():
        return WeatherSeverity.OKAY
    return WeatherSeverity.GREAT


def _severity_to_summary(severity: WeatherSeverity, condition: str, temp_max: float) -> str:
    """Generate a human-readable weather summary."""
    if severity == WeatherSeverity.INDOOR:
        return f"⛈️ {condition} expected — indoor activities recommended"
    if severity == WeatherSeverity.OKAY:
        return f"⛅ {condition} — carry an umbrella just in case"
    if temp_max > 38:
        return f"☀️ {condition}, hot ({temp_max:.0f}°C) — stay hydrated, prefer morning/evening"
    return f"☀️ {condition} — perfect for outdoor activities"


@cached("weather", ttl_seconds=3600 * 6)  # Cache for 6 hours
async def get_forecast(
    lat: float,
    lng: float,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """
    Get weather forecast for a location and date range.
    Uses OpenWeatherMap 5-day/3-hour forecast.
    Returns list of dicts for caching.
    """
    if not settings.openweathermap_api_key:
        logger.info("No OpenWeatherMap API key — weather unavailable")
        return []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{OWM_BASE}/forecast",
                params={
                    "lat": lat,
                    "lon": lng,
                    "appid": settings.openweathermap_api_key,
                    "units": "metric",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"OpenWeatherMap API error: {e}")
        return []

    # Parse into daily summaries
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    daily: dict[str, dict] = {}

    for item in data.get("list", []):
        dt = datetime.fromtimestamp(item["dt"])
        day_key = dt.strftime("%Y-%m-%d")
        item_date = dt.date()

        if item_date < start or item_date > end:
            continue

        if day_key not in daily:
            daily[day_key] = {
                "temps": [],
                "conditions": [],
                "icons": [],
                "rain_probs": [],
            }

        daily[day_key]["temps"].append(item["main"]["temp"])
        weather = item.get("weather", [{}])[0]
        daily[day_key]["conditions"].append(weather.get("main", "Clear"))
        daily[day_key]["icons"].append(weather.get("icon", "01d"))
        daily[day_key]["rain_probs"].append(item.get("pop", 0))

    forecasts = []
    for day_key in sorted(daily.keys()):
        d = daily[day_key]
        temps = d["temps"]
        conditions = d["conditions"]
        rain_probs = d["rain_probs"]

        # Most common condition for the day
        main_condition = max(set(conditions), key=conditions.count)
        avg_rain = sum(rain_probs) / len(rain_probs) if rain_probs else 0
        severity = _classify_severity(main_condition, avg_rain)

        temp_min = min(temps)
        temp_max = max(temps)

        forecasts.append({
            "date": day_key,
            "temp_min": round(temp_min, 1),
            "temp_max": round(temp_max, 1),
            "condition": main_condition,
            "icon": d["icons"][len(d["icons"]) // 2],  # Mid-day icon
            "rain_probability": round(avg_rain, 2),
            "severity": severity.value,
            "summary": _severity_to_summary(severity, main_condition, temp_max),
        })

    return forecasts
