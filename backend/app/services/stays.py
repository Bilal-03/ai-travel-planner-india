"""Provider-neutral stay discovery and itinerary mutations.

Live hotel inventory is deliberately not fabricated here. Until a property
provider is configured, the workspace receives clearly-labelled area-level
planning estimates and a handoff link for checking current inventory.
"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote_plus

from app.models.trip import (
    DataProvenance,
    DataStatus,
    Itinerary,
    ItineraryItem,
    ItineraryItemType,
    StayOption,
)


def _estimate_provenance() -> DataProvenance:
    checked_at = datetime.now(timezone.utc)
    return DataProvenance(
        provider="YatraAI stay planning estimate",
        status=DataStatus.ESTIMATED,
        retrieved_at=checked_at,
        expires_at=checked_at + timedelta(hours=24),
        confidence=0.45,
        source_reference="app://stay-estimates",
        disclaimer=(
            "Area-level planning estimate only. No property availability, room, "
            "rate, tax, or reservation is confirmed; search live inventory before booking."
        ),
    )


def _stable_stay_id(city: str, area: str, check_in: date, check_out: date, style: str, rooms: int) -> str:
    fingerprint = "|".join([
        " ".join(city.casefold().split()),
        " ".join(area.casefold().split()),
        check_in.isoformat(),
        check_out.isoformat(),
        " ".join(style.casefold().split()),
        str(rooms),
    ])
    return f"stay-{hashlib.sha1(fingerprint.encode('utf-8')).hexdigest()[:16]}"


def _nightly_base(style: str) -> int:
    value = style.casefold()
    if any(term in value for term in ("hostel", "budget", "backpack")):
        return 1_800
    if any(term in value for term in ("premium", "luxury", "resort")):
        return 7_500
    return 3_200


def search_stays(
    *,
    city: str,
    check_in: date,
    check_out: date,
    members: int = 2,
    hotel_style: str | None = None,
) -> list[StayOption]:
    """Return honest area-level estimates for an India destination.

    This seam is intentionally synchronous and provider-neutral. A future
    property adapter can replace the estimate list without changing the API
    or the workspace data shape.
    """

    clean_city = " ".join(city.split())
    if not clean_city:
        raise ValueError("A destination city is required for stay search")
    if check_out <= check_in:
        raise ValueError("Stay check-out must be after check-in")
    nights = (check_out - check_in).days
    rooms = max(1, min(20, math.ceil(max(1, members) / 2)))
    style = " ".join((hotel_style or "standard").split()) or "standard"
    base = _nightly_base(style)
    area_options = [
        (
            "Central / old city",
            1.0,
            "A practical base for walking to headline sights and trying local food.",
            ["Walkable sights", "Local restaurants", "Easy taxi access"],
        ),
        (
            "Quiet neighbourhood",
            0.88,
            "A calmer area estimate for travellers who want slower mornings and evenings.",
            ["Quieter streets", "Longer-stay comfort", "Local markets nearby"],
        ),
        (
            "Station / airport side",
            0.78,
            "A transport-friendly base when arrival timing or an early departure matters.",
            ["Transfer-friendly", "Late arrival practical", "Food delivery access"],
        ),
    ]
    options: list[StayOption] = []
    for area, multiplier, description, amenities in area_options:
        nightly_price = max(900, round(base * multiplier / 100) * 100)
        total_price = nightly_price * nights * rooms
        provenance = _estimate_provenance()
        query = quote_plus(f"Hotels in {clean_city}, {area}, India")
        options.append(StayOption(
            id=_stable_stay_id(clean_city, area, check_in, check_out, style, rooms),
            city=clean_city,
            area=area,
            name=f"{area} stay estimate",
            stay_type="area_estimate",
            check_in=check_in,
            check_out=check_out,
            nights=nights,
            rooms=rooms,
            nightly_price=nightly_price,
            total_price=total_price,
            amenities=amenities,
            description=(
                f"{description} Priced as a {style} planning estimate for {rooms} "
                f"room{'s' if rooms != 1 else ''} in {clean_city}."
            ),
            booking_url=f"https://www.google.com/travel/search?q={query}",
            maps_url=f"https://www.google.com/maps/search/?api=1&query={query}",
            is_fallback=True,
            provenance=provenance,
            field_provenance={
                "nightly_price": provenance,
                "total_price": provenance,
                "availability": DataProvenance(
                    provider="not_provided",
                    status=DataStatus.UNAVAILABLE,
                    source_reference="app://stay-estimates",
                    disclaimer="No live room availability was queried; verify before booking.",
                ),
            },
        ))
    return options


def _sync_selected_plan(updated: Itinerary) -> None:
    for option in updated.plan_options:
        if option.id != updated.selected_plan_id:
            continue
        option.day_plans = [day.model_copy(deep=True) for day in updated.day_plans]
        option.budget = updated.budget.model_copy(deep=True)
        break


def add_stay_to_itinerary(itinerary: Itinerary, stay: StayOption) -> tuple[Itinerary, bool]:
    """Persist one stay estimate as a trip-level itinerary item, idempotently."""

    if stay.city.casefold().strip() != itinerary.destination.name.casefold().strip():
        raise ValueError("The stay must be in the trip destination")
    updated = itinerary.model_copy(deep=True)
    if any(item.metadata.get("stay_id") == stay.id for item in updated.items):
        return updated, False

    updated.items.append(ItineraryItem(
        item_type=ItineraryItemType.STAY,
        title=stay.name,
        position=0,
        description=stay.description,
        notes="Area-level estimate saved for planning. Search live stays and verify taxes, cancellation, and room availability before booking.",
        provenance=stay.provenance,
        metadata=stay.model_dump(mode="json") | {"stay_id": stay.id},
    ))
    updated.budget.stay += stay.total_price
    updated.budget.total_estimated += stay.total_price
    updated.budget.remaining -= stay.total_price
    _sync_selected_plan(updated)
    return updated, True


def remove_stay_from_itinerary(itinerary: Itinerary, stay_id: str) -> tuple[Itinerary, bool]:
    """Remove a previously added stay estimate and reverse its budget line."""

    updated = itinerary.model_copy(deep=True)
    removed = next((item for item in updated.items if item.item_type == ItineraryItemType.STAY and item.metadata.get("stay_id") == stay_id), None)
    if removed is None:
        return updated, False
    total_price = removed.metadata.get("total_price")
    amount = int(total_price) if isinstance(total_price, (int, float)) else 0
    updated.items = [item for item in updated.items if item.id != removed.id]
    updated.budget.stay = max(0, updated.budget.stay - amount)
    updated.budget.total_estimated = max(0, updated.budget.total_estimated - amount)
    updated.budget.remaining += amount
    _sync_selected_plan(updated)
    return updated, True
