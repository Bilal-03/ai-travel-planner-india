"""Normalized place discovery and deterministic saved-place mutations.

The planner still stores the complete itinerary JSON for compatibility. This
module gives the workspace a small, server-validated seam for turning provider
POIs into saved places and scheduling one saved place into a day.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from typing import Any

from app.models.trip import (
    POI,
    Activity,
    DataProvenance,
    Itinerary,
    ItineraryItem,
    ItineraryItemType,
    Place,
)

_DAY_START_MINUTES = 9 * 60
_DAY_END_MINUTES = 21 * 60
_BREAK_MINUTES = 15
_MINUTES_PATTERN = re.compile(r"^(\d{1,2}):(\d{2})$")


def _as_provenance(value: Any) -> DataProvenance:
    if isinstance(value, DataProvenance):
        return value
    if isinstance(value, dict):
        try:
            return DataProvenance.model_validate(value)
        except (TypeError, ValueError):
            return DataProvenance()
    return DataProvenance()


def _as_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _stable_place_id(name: str, coordinates: dict[str, Any], city: str | None) -> str:
    fingerprint = "|".join([
        " ".join(name.casefold().split()),
        f"{float(coordinates['lat']):.6f}",
        f"{float(coordinates['lng']):.6f}",
        " ".join((city or "India").casefold().split()),
    ])
    digest = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:16]
    return f"place-{digest}"


def _query_matches(raw: dict[str, Any], query: str | None) -> bool:
    if not query or not query.strip():
        return True
    tags = raw.get("osm_tags") if isinstance(raw.get("osm_tags"), dict) else {}
    coordinates = raw.get("coordinates") if isinstance(raw.get("coordinates"), dict) else {}
    haystack = " ".join(
        str(value)
        for value in [
            raw.get("name"),
            raw.get("category"),
            raw.get("description"),
            raw.get("city"),
            raw.get("state"),
            *tags.values(),
            coordinates.get("lat"),
            coordinates.get("lng"),
        ]
        if value is not None
    ).casefold()
    terms = [term for term in re.split(r"[^a-z0-9]+", query.casefold()) if term]
    return bool(terms) and all(term in haystack for term in terms)


def normalise_pois_to_places(
    pois: Iterable[dict[str, Any]],
    *,
    city: str | None = None,
    query: str | None = None,
    limit: int = 30,
) -> list[Place]:
    """Convert provider-neutral POI dictionaries into stable ``Place`` records."""

    places: list[Place] = []
    seen_ids: set[str] = set()
    for raw in pois:
        if not isinstance(raw, dict) or not _query_matches(raw, query):
            continue
        coordinates = raw.get("coordinates")
        if not isinstance(coordinates, dict) or coordinates.get("lat") is None or coordinates.get("lng") is None:
            continue
        name = _as_text(raw.get("name"))
        category = _as_text(raw.get("category")) or "attraction"
        if not name:
            continue
        resolved_city = _as_text(raw.get("city")) or city
        place_id = _stable_place_id(name, coordinates, resolved_city)
        if place_id in seen_ids:
            continue

        tags = raw.get("osm_tags") if isinstance(raw.get("osm_tags"), dict) else {}
        provider_ids = {
            str(key): str(value)
            for key, value in (raw.get("provider_ids") or {}).items()
            if value is not None
        } if isinstance(raw.get("provider_ids"), dict) else {}
        if raw.get("id") is not None:
            provider_ids.setdefault("provider", str(raw["id"]))
        provider_ids.setdefault("yatraai", place_id)

        provenance = _as_provenance(raw.get("provenance"))
        field_provenance = {
            str(key): _as_provenance(value)
            for key, value in (raw.get("field_provenance") or {}).items()
        } if isinstance(raw.get("field_provenance"), dict) else {}
        website = _as_text(raw.get("official_url")) or _as_text(tags.get("website"))
        lat = float(coordinates["lat"])
        lng = float(coordinates["lng"])
        estimated_visit_minutes = int(raw.get("estimated_visit_minutes") or 60)
        estimated_cost = int(raw.get("estimated_cost") or 0)
        description = _as_text(raw.get("description")) or (
            f"{category.replace('_', ' ').title()} stop in {resolved_city or 'India'}. "
            "Verify current access, opening hours, and ticketing before visiting."
        )
        place = Place(
            id=place_id,
            name=name,
            category=category,
            coordinates={"lat": lat, "lng": lng},
            address=_as_text(raw.get("address")) or _as_text(tags.get("addr:full")),
            city=resolved_city,
            state=_as_text(raw.get("state")),
            country=_as_text(raw.get("country")) or "India",
            description=description,
            opening_hours=_as_text(raw.get("opening_hours")) or _as_text(tags.get("opening_hours")),
            rating=raw.get("rating") if isinstance(raw.get("rating"), (int, float)) else None,
            review_count=raw.get("review_count") if isinstance(raw.get("review_count"), int) else None,
            price_level=raw.get("price_level") if isinstance(raw.get("price_level"), int) else None,
            estimated_visit_minutes=max(15, min(1_440, estimated_visit_minutes)),
            estimated_cost=max(0, min(1_000_000, estimated_cost)),
            official_url=website,
            maps_url=f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lng:.6f}",
            provider_ids=provider_ids,
            photos=[],
            provenance=provenance,
            field_provenance=field_provenance,
        )
        places.append(place)
        seen_ids.add(place_id)
        if len(places) >= limit:
            break
    return places


def _parse_minutes(value: str | None) -> int | None:
    if not value:
        return None
    match = _MINUTES_PATTERN.match(value.strip())
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute


def _format_minutes(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _activity_place_id(activity: Activity) -> str | None:
    tags = activity.poi.osm_tags or {}
    return str(tags["place_id"]) if tags.get("place_id") else activity.poi.id


def _next_activity_start(activities: list[Activity]) -> int:
    cursor = _DAY_START_MINUTES
    for activity in activities:
        start = _parse_minutes(activity.start_time)
        end = _parse_minutes(activity.end_time)
        if end is None:
            start = start if start is not None else cursor
            end = start + max(30, activity.poi.estimated_visit_minutes)
        cursor = max(cursor, end + _BREAK_MINUTES)
    return cursor


def _sync_selected_plan(updated: Itinerary) -> None:
    """Keep the selected plan option aligned with top-level workspace edits."""

    for option in updated.plan_options:
        if option.id != updated.selected_plan_id:
            continue
        option.day_plans = [day.model_copy(deep=True) for day in updated.day_plans]
        option.budget = updated.budget.model_copy(deep=True)
        break


def save_place(itinerary: Itinerary, place: Place) -> tuple[Itinerary, bool]:
    """Save a validated India place to the current trip, idempotently."""

    if place.country.casefold() not in {"india", "in"}:
        raise ValueError("Only places in India can be saved to this trip.")
    updated = itinerary.model_copy(deep=True)
    if any(saved.id == place.id for saved in updated.places):
        return updated, False
    updated.places.append(place.model_copy(deep=True))
    return updated, True


def remove_saved_place(itinerary: Itinerary, place_id: str) -> tuple[Itinerary, bool]:
    """Remove a saved place without deleting an existing scheduled visit."""

    updated = itinerary.model_copy(deep=True)
    remaining = [place for place in updated.places if place.id != place_id]
    changed = len(remaining) != len(updated.places)
    updated.places = remaining
    return updated, changed


def add_place_to_day(
    itinerary: Itinerary,
    *,
    place_id: str,
    day_number: int,
    position: int | None = None,
    place: Place | None = None,
) -> tuple[Itinerary, bool]:
    """Add a saved place to a day with deterministic time and budget checks."""

    updated = itinerary.model_copy(deep=True)
    saved = next((candidate for candidate in updated.places if candidate.id == place_id), None)
    if saved is None and place is not None:
        if place.id != place_id:
            raise ValueError("The place payload does not match the requested place.")
        updated, _ = save_place(updated, place)
        saved = next(candidate for candidate in updated.places if candidate.id == place_id)
    if saved is None:
        raise ValueError("Save this place before adding it to the itinerary.")

    day = next((candidate for candidate in updated.day_plans if candidate.day_number == day_number), None)
    if day is None:
        raise ValueError(f"Day {day_number} is not part of this itinerary.")
    if any(_activity_place_id(activity) == place_id for candidate in updated.day_plans for activity in candidate.activities):
        return updated, False

    insert_at = len(day.activities) if position is None else position
    if insert_at < 0 or insert_at > len(day.activities):
        raise ValueError("The requested itinerary position is invalid.")

    start_minutes = _next_activity_start(day.activities)
    duration = max(15, min(1_440, saved.estimated_visit_minutes))
    end_minutes = start_minutes + duration
    if end_minutes > _DAY_END_MINUTES:
        raise ValueError(f"There is no room for {saved.name} on day {day_number}; choose another day.")

    poi = POI(
        id=place_id,
        name=saved.name,
        category=saved.category,
        coordinates=saved.coordinates,
        osm_tags={"place_id": place_id, **saved.provider_ids},
        estimated_visit_minutes=duration,
        estimated_cost=saved.estimated_cost,
        description=saved.description,
        opening_hours=saved.opening_hours,
        rating=saved.rating,
        provenance=saved.provenance,
        field_provenance=saved.field_provenance,
    )
    activity = Activity(
        poi=poi,
        start_time=_format_minutes(start_minutes),
        end_time=_format_minutes(end_minutes),
        estimated_cost=saved.estimated_cost,
        notes="Added from Saved Places; verify hours, access, and ticketing before visiting.",
    )
    day.activities.insert(insert_at, activity)
    day.day_spent = (
        sum(item.estimated_cost for item in day.activities)
        + sum(meal.estimated_cost for meal in day.meals)
        + day.local_transport_cost
    )

    for item in updated.items:
        if item.day_number == day_number and item.position >= insert_at:
            item.position += 1
    image_url = saved.photos[0].url if saved.photos else None
    updated.items.append(ItineraryItem(
        item_type=ItineraryItemType.PLACE_VISIT,
        title=saved.name,
        day_number=day_number,
        position=insert_at,
        place_id=place_id,
        coordinates=saved.coordinates,
        start_time=activity.start_time,
        end_time=activity.end_time,
        duration_minutes=duration,
        description=saved.description,
        notes=activity.notes,
        image_url=image_url,
        provenance=saved.provenance,
        metadata={"estimated_cost": saved.estimated_cost, "category": saved.category},
    ))
    updated.budget.activities += saved.estimated_cost
    updated.budget.total_estimated += saved.estimated_cost
    updated.budget.remaining -= saved.estimated_cost
    _sync_selected_plan(updated)
    return updated, True
