"""
Transport service — Skyscanner flights + RailRadar schedules + transparent fallback estimates.
Searches for transport options between Indian cities, with aggressive caching
and graceful fallback when API quotas are exhausted.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.cache.redis_cache import cached
from app.config import settings
from app.models.trip import DataProvenance, DataStatus, TransportMode, TransportOption

logger = logging.getLogger(__name__)

# ── IATA code mapping for major Indian cities ─────────────────────────

CITY_IATA: dict[str, str] = {
    "mumbai": "BOM", "delhi": "DEL", "new delhi": "DEL",
    "bangalore": "BLR", "bengaluru": "BLR", "hyderabad": "HYD",
    "chennai": "MAA", "kolkata": "CCU", "pune": "PNQ",
    "ahmedabad": "AMD", "jaipur": "JAI", "goa": "GOI",
    "panaji": "GOI", "kochi": "COK", "cochin": "COK",
    "lucknow": "LKO", "thiruvananthapuram": "TRV",
    "trivandrum": "TRV", "guwahati": "GAU", "patna": "PAT",
    "bhubaneswar": "BBI", "varanasi": "VNS", "chandigarh": "IXC",
    "indore": "IDR", "nagpur": "NAG", "coimbatore": "CJB",
    "visakhapatnam": "VTZ", "vizag": "VTZ", "srinagar": "SXR",
    "amritsar": "ATQ", "udaipur": "UDR", "jodhpur": "JDH",
    "dehradun": "DED", "ranchi": "IXR", "raipur": "RPR",
    "bhopal": "BHO", "mangalore": "IXE", "madurai": "IXM",
    "leh": "IXL", "agartala": "IXA", "imphal": "IMF",
    "port blair": "IXZ", "bagdogra": "IXB", "siliguri": "IXB",
    "agra": "AGR", "aurangabad": "IXU", "vadodara": "BDQ",
    "surat": "STV", "tiruchirappalli": "TRZ", "trichy": "TRZ",
    "mysore": "MYQ", "mysuru": "MYQ",
}

# ── Station code mapping for major Indian cities ─────────────────────

CITY_STATION: dict[str, str] = {
    "mumbai": "CSTM", "delhi": "NDLS", "new delhi": "NDLS",
    "bangalore": "SBC", "bengaluru": "SBC", "hyderabad": "SC",
    "chennai": "MAS", "kolkata": "HWH", "pune": "PUNE",
    "ahmedabad": "ADI", "jaipur": "JP", "lucknow": "LKO",
    "varanasi": "BSB", "agra": "AGC", "goa": "MAO",
    "panaji": "MAO", "kochi": "ERS", "cochin": "ERS",
    "thiruvananthapuram": "TVC", "trivandrum": "TVC",
    "guwahati": "GHY", "patna": "PNBE", "bhubaneswar": "BBS",
    "chandigarh": "CDG", "indore": "INDB", "nagpur": "NGP",
    "coimbatore": "CBE", "visakhapatnam": "VSKP", "vizag": "VSKP",
    "amritsar": "ASR", "udaipur": "UDZ", "jodhpur": "JU",
    "dehradun": "DDN", "ranchi": "RNC", "raipur": "R",
    "bhopal": "BPL", "madurai": "MDU", "mysore": "MYS",
    "mysuru": "MYS", "surat": "ST", "vadodara": "BRC",
}


def get_iata_code(city: str) -> Optional[str]:
    return CITY_IATA.get(city.lower().strip())


def get_station_code(city: str) -> Optional[str]:
    return CITY_STATION.get(city.lower().strip())


def _transport_provenance(
    provider: str,
    status: DataStatus,
    disclaimer: str,
    *,
    source_reference: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
    field_statuses: Optional[dict[str, DataStatus]] = None,
    retrieved_at: Optional[datetime] = None,
    confidence: Optional[float] = None,
) -> tuple[DataProvenance, dict[str, DataProvenance]]:
    """Build one transport fact envelope plus field-level envelopes."""

    checked_at = retrieved_at or datetime.now(timezone.utc)
    expires_at = checked_at + timedelta(seconds=ttl_seconds) if ttl_seconds else None
    primary = DataProvenance(
        provider=provider,
        status=status,
        retrieved_at=checked_at,
        expires_at=expires_at,
        confidence=confidence,
        source_reference=source_reference,
        disclaimer=disclaimer,
    )
    fields: dict[str, DataProvenance] = {}
    for field_name, field_status in (field_statuses or {}).items():
        field_provider = provider
        if field_status == DataStatus.ESTIMATED:
            field_provider = "YatraAI estimate"
        fields[field_name] = DataProvenance(
            provider=field_provider,
            status=field_status,
            retrieved_at=checked_at,
            expires_at=expires_at,
            confidence=confidence if field_status != DataStatus.UNAVAILABLE else None,
            source_reference=source_reference,
            disclaimer=disclaimer,
        )
    return primary, fields


# ── Static fallback routes ────────────────────────────────────────────
# Pre-seeded common intercity routes with approximate data

FALLBACK_TRAINS: list[dict] = [
    {"from": "delhi", "to": "mumbai", "name": "Rajdhani Express", "code": "12951", "duration": 960, "price": 2500, "class": "3A"},
    {"from": "delhi", "to": "mumbai", "name": "August Kranti Rajdhani", "code": "12953", "duration": 1020, "price": 2400, "class": "3A"},
    {"from": "delhi", "to": "kolkata", "name": "Rajdhani Express", "code": "12301", "duration": 1020, "price": 2600, "class": "3A"},
    {"from": "delhi", "to": "chennai", "name": "Tamil Nadu Express", "code": "12621", "duration": 1980, "price": 2800, "class": "3A"},
    {"from": "delhi", "to": "bangalore", "name": "Rajdhani Express", "code": "22691", "duration": 2040, "price": 3200, "class": "3A"},
    {"from": "delhi", "to": "jaipur", "name": "Shatabdi Express", "code": "12015", "duration": 270, "price": 900, "class": "CC"},
    {"from": "delhi", "to": "agra", "name": "Gatimaan Express", "code": "12049", "duration": 100, "price": 750, "class": "CC"},
    {"from": "delhi", "to": "lucknow", "name": "Shatabdi Express", "code": "12003", "duration": 390, "price": 1100, "class": "CC"},
    {"from": "delhi", "to": "chandigarh", "name": "Shatabdi Express", "code": "12005", "duration": 195, "price": 700, "class": "CC"},
    {"from": "delhi", "to": "varanasi", "name": "Vande Bharat Express", "code": "22435", "duration": 480, "price": 1800, "class": "CC"},
    {"from": "delhi", "to": "dehradun", "name": "Shatabdi Express", "code": "12017", "duration": 330, "price": 800, "class": "CC"},
    {"from": "mumbai", "to": "pune", "name": "Deccan Queen", "code": "12123", "duration": 195, "price": 350, "class": "CC"},
    {"from": "mumbai", "to": "goa", "name": "Konkan Kanya Express", "code": "10111", "duration": 720, "price": 600, "class": "SL"},
    {"from": "mumbai", "to": "ahmedabad", "name": "Shatabdi Express", "code": "12009", "duration": 390, "price": 900, "class": "CC"},
    {"from": "mumbai", "to": "bangalore", "name": "Udyan Express", "code": "11301", "duration": 1440, "price": 1200, "class": "3A"},
    {"from": "chennai", "to": "bangalore", "name": "Shatabdi Express", "code": "12007", "duration": 300, "price": 750, "class": "CC"},
    {"from": "chennai", "to": "coimbatore", "name": "Shatabdi Express", "code": "12243", "duration": 420, "price": 650, "class": "CC"},
    {"from": "kolkata", "to": "patna", "name": "Rajdhani Express", "code": "12309", "duration": 420, "price": 1200, "class": "3A"},
    {"from": "hyderabad", "to": "bangalore", "name": "Kacheguda Express", "code": "12785", "duration": 720, "price": 800, "class": "3A"},
    {"from": "bangalore", "to": "mysore", "name": "Shatabdi Express", "code": "12007", "duration": 120, "price": 400, "class": "CC"},
    {"from": "jaipur", "to": "udaipur", "name": "Chetak Express", "code": "12981", "duration": 660, "price": 500, "class": "SL"},
    {"from": "lucknow", "to": "varanasi", "name": "Vande Bharat Express", "code": "22437", "duration": 240, "price": 1200, "class": "CC"},
]


def _estimated_route_distance(origin: str, destination: str) -> float:
    """Stable coarse distance for direct transport searches without coordinates."""
    route_seed = sum(ord(char) for char in f"{origin.casefold()}:{destination.casefold()}")
    return float(250 + (route_seed % 18) * 100)


def _estimated_train_option(origin: str, destination: str, distance_km: float | None) -> TransportOption:
    distance = distance_km or _estimated_route_distance(origin, destination)
    checked_at = datetime.now(timezone.utc)
    provenance, field_data_provenance = _transport_provenance(
        "YatraAI transport estimator",
        DataStatus.ESTIMATED,
        "Train fare and duration are planning estimates; no schedule, operating date, or availability was verified. Verify before booking.",
        source_reference="app://transport/estimated-train",
        ttl_seconds=86400,
        confidence=0.45,
        field_statuses={
            "train": DataStatus.UNAVAILABLE,
            "schedule": DataStatus.UNAVAILABLE,
            "fare": DataStatus.ESTIMATED,
            "availability": DataStatus.UNAVAILABLE,
            "travel_date": DataStatus.UNAVAILABLE,
        },
        retrieved_at=checked_at,
    )
    return TransportOption(
        mode=TransportMode.TRAIN,
        provider="Indian Railways fare estimate",
        code=None,
        # Approximate 3A/CC fare band, intentionally not represented as live.
        price=max(350, int(distance * 1.45 + 250)),
        duration_minutes=max(180, int(distance * 1.05 + 90)),
        departure_city=origin.title(),
        arrival_city=destination.title(),
        is_fallback=True,
        field_provenance={
            "train": "No schedule data available",
            "schedule": "Not available",
            "fare": "Estimated 3A fare",
            "availability": "Not available",
            "travel_date": "Not date-verified",
        },
        field_data_provenance=field_data_provenance,
        provenance=provenance,
        availability_status="Not available",
        last_checked_at=checked_at,
    )


def _get_fallback_trains(
    origin: str, destination: str, distance_km: float | None = None
) -> list[TransportOption]:
    """Get static fallback train options for a route."""
    origin_lower = origin.lower().strip().replace("new delhi", "delhi")
    dest_lower = destination.lower().strip().replace("new delhi", "delhi")

    results = []
    for train in FALLBACK_TRAINS:
        if (
            (train["from"] == origin_lower and train["to"] == dest_lower)
            or (train["from"] == dest_lower and train["to"] == origin_lower)
        ):
            checked_at = datetime.now(timezone.utc)
            provenance, field_data_provenance = _transport_provenance(
                "YatraAI static train catalogue",
                DataStatus.STATIC_REFERENCE,
                "Static train schedule reference; fare is estimated and operation, date, availability, and current timings were not verified. Verify before booking.",
                source_reference="app://transport/fallback-trains",
                ttl_seconds=86400 * 30,
                confidence=0.55,
                field_statuses={
                    "train": DataStatus.STATIC_REFERENCE,
                    "schedule": DataStatus.STATIC_REFERENCE,
                    "fare": DataStatus.ESTIMATED,
                    "availability": DataStatus.UNAVAILABLE,
                    "travel_date": DataStatus.UNAVAILABLE,
                },
                retrieved_at=checked_at,
            )
            results.append(TransportOption(
                mode=TransportMode.TRAIN,
                provider=train["name"],
                code=train["code"],
                price=train["price"],
                duration_minutes=train["duration"],
                departure_city=origin.title(),
                arrival_city=destination.title(),
                is_fallback=True,
                field_provenance={
                    "train": "Static schedule reference (not live)",
                    "schedule": "Static schedule reference (not date-verified)",
                    "fare": f"Estimated {train['class']} fare",
                    "availability": "Not available",
                    "travel_date": "Not date-verified",
                },
                field_data_provenance=field_data_provenance,
                provenance=provenance,
                availability_status="Not available",
                last_checked_at=checked_at,
            ))

    return results or [_estimated_train_option(origin, destination, distance_km)]


# ── Static fallback flights ───────────────────────────────────────────

FALLBACK_FLIGHTS: list[dict] = [
    {"from": "delhi", "to": "mumbai", "provider": "IndiGo", "code": None, "duration": 130, "price": 4500},
    {"from": "mumbai", "to": "delhi", "provider": "Air India", "code": None, "duration": 135, "price": 4800},
    {"from": "bangalore", "to": "delhi", "provider": "Air India", "code": None, "duration": 165, "price": 6000},
    {"from": "delhi", "to": "bangalore", "provider": "IndiGo", "code": None, "duration": 160, "price": 5500},
    {"from": "mumbai", "to": "bangalore", "provider": "Akasa Air", "code": None, "duration": 110, "price": 3500},
    {"from": "bangalore", "to": "mumbai", "provider": "IndiGo", "code": None, "duration": 115, "price": 3800},
    {"from": "delhi", "to": "goa", "provider": "Air India Express", "code": None, "duration": 150, "price": 5200},
    {"from": "mumbai", "to": "goa", "provider": "IndiGo", "code": None, "duration": 75, "price": 2800},
    {"from": "delhi", "to": "chennai", "provider": "IndiGo", "code": None, "duration": 170, "price": 5800},
    {"from": "chennai", "to": "delhi", "provider": "Air India", "code": None, "duration": 175, "price": 6200},
]

# The flight-search response occasionally exposes an internal or malformed
# carrier ``alternateId`` (for example, ``0S`` for SpiceJet).  Prefer the
# airline's published IATA designator whenever its marketing name is known.
AIRLINE_IATA_CODES: dict[str, str] = {
    "air india": "AI",
    "air india express": "IX",
    "akasa air": "QP",
    "alliance air": "9I",
    "fly91": "IC",
    "indigo": "6E",
    "spicejet": "SG",
    "star air": "S5",
    "vistara": "UK",
}


def _format_flight_code(provider: str, carrier_code: object, flight_number: object) -> Optional[str]:
    """Return a readable, canonical flight number without trusting provider aliases."""
    number = "".join(re.findall(r"\d+", str(flight_number or "")))
    if not number:
        return None

    canonical_code = AIRLINE_IATA_CODES.get(provider.casefold().strip())
    if canonical_code:
        return f"{canonical_code}{number}"

    # Preserve an unknown carrier code only when it is a plausible IATA-like
    # identifier. This avoids rendering provider-specific punctuation or IDs.
    raw_code = re.sub(r"[^A-Z0-9]", "", str(carrier_code or "").upper())
    return f"{raw_code}{number}" if 2 <= len(raw_code) <= 3 else number


def _best_flights_per_airline(flights: list[dict], per_airline: int = 2, total_limit: int = 8) -> list[dict]:
    """Keep the best-priced, shortest options while avoiding one-airline repetition."""
    ranked = sorted(
        flights,
        key=lambda flight: (
            flight["price"],
            flight["duration_minutes"],
            flight.get("departure_time") or "",
        ),
    )
    chosen: list[dict] = []
    counts: dict[str, int] = {}
    for flight in ranked:
        airline = flight["provider"].casefold().strip()
        if counts.get(airline, 0) >= per_airline:
            continue
        chosen.append(flight)
        counts[airline] = counts.get(airline, 0) + 1
        if len(chosen) == total_limit:
            break
    return chosen

def _get_fallback_flights(
    origin: str, destination: str, distance_km: float | None = None
) -> list[dict]:
    origin_lower = origin.lower().strip().replace("new delhi", "delhi")
    dest_lower = destination.lower().strip().replace("new delhi", "delhi")
    
    results = []
    for f in FALLBACK_FLIGHTS:
        if f["from"] == origin_lower and f["to"] == dest_lower:
            checked_at = datetime.now(timezone.utc)
            provenance, field_data_provenance = _transport_provenance(
                "YatraAI static flight catalogue",
                DataStatus.ESTIMATED,
                "Flight fare is planning guidance without a verified schedule or availability. Verify the fare, timing, and seat availability before booking.",
                source_reference="app://transport/fallback-flights",
                ttl_seconds=86400,
                confidence=0.4,
                field_statuses={
                    "fare": DataStatus.ESTIMATED,
                    "schedule": DataStatus.UNAVAILABLE,
                    "availability": DataStatus.UNAVAILABLE,
                },
                retrieved_at=checked_at,
            )
            results.append({
                "mode": "flight",
                "provider": f["provider"],
                "code": f["code"],
                "price": f["price"],
                "duration_minutes": f["duration"],
                # Static options are fare guidance, not a fabricated schedule.
                "departure_time": None,
                "arrival_time": None,
                "departure_city": origin.title(),
                "arrival_city": destination.title(),
                "is_fallback": True,
                "field_provenance": {
                    "fare": "Estimated fare guidance",
                    "schedule": "Not available",
                    "availability": "Not available",
                },
                "field_data_provenance": {
                    key: value.model_dump(mode="json")
                    for key, value in field_data_provenance.items()
                },
                "provenance": provenance.model_dump(mode="json"),
                "availability_status": "Not available",
                "last_checked_at": checked_at.isoformat(),
            })
    if results:
        return results

    distance = distance_km or _estimated_route_distance(origin, destination)
    checked_at = datetime.now(timezone.utc)
    provenance, field_data_provenance = _transport_provenance(
        "YatraAI transport estimator",
        DataStatus.ESTIMATED,
        "Flight fare and duration are planning estimates without a verified schedule or availability. Verify before booking.",
        source_reference="app://transport/estimated-flight",
        ttl_seconds=86400,
        confidence=0.4,
        field_statuses={
            "fare": DataStatus.ESTIMATED,
            "schedule": DataStatus.UNAVAILABLE,
            "availability": DataStatus.UNAVAILABLE,
        },
        retrieved_at=checked_at,
    )
    return [{
        "mode": "flight",
        "provider": "Domestic flight fare estimate",
        "code": None,
        "price": max(2800, int(distance * 4.2 + 1800)),
        "duration_minutes": max(70, int(distance / 8.5 + 45)),
        "departure_time": None,
        "arrival_time": None,
        "departure_city": origin.title(),
        "arrival_city": destination.title(),
        "is_fallback": True,
        "field_provenance": {
            "fare": "Estimated fare guidance",
            "schedule": "Not available",
            "availability": "Not available",
        },
        "field_data_provenance": {
            key: value.model_dump(mode="json")
            for key, value in field_data_provenance.items()
        },
        "provenance": provenance.model_dump(mode="json"),
        "availability_status": "Not available",
        "last_checked_at": checked_at.isoformat(),
    }]

# ── Skyscanner Flight Search ──────────────────────────────────────────

@cached("flights", ttl_seconds=3600)  # Cache for 1 hour
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    max_price: Optional[int] = None,
    distance_km: float | None = None,
) -> list[dict]:
    """Search flights via Skyscanner RapidAPI."""
    origin_iata = get_iata_code(origin)
    dest_iata = get_iata_code(destination)

    if not origin_iata or not dest_iata:
        logger.warning(f"No IATA code for {origin} or {destination}, using fallback")
        return _get_fallback_flights(origin, destination, distance_km)

    if not settings.skyscanner_rapidapi_key:
        logger.warning("No Skyscanner API key — using fallback flights")
        return _get_fallback_flights(origin, destination, distance_km)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://flights-sky.p.rapidapi.com/flights/search-one-way",
                params={
                    "fromEntityId": origin_iata,
                    "toEntityId": dest_iata,
                    "departDate": departure_date[:10],
                    "currency": "INR",
                    "market": "IN",
                },
                headers={
                    "x-rapidapi-key": settings.skyscanner_rapidapi_key,
                    "x-rapidapi-host": "flights-sky.p.rapidapi.com"
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            checked_at = datetime.now(timezone.utc)
            flights = []
            itineraries = data.get("data", {}).get("itineraries", [])
            for it in itineraries:
                try:
                    price = it.get("price", {}).get("raw", 5000)
                    legs = it.get("legs", [])
                    if not legs:
                        continue
                    leg = legs[0]
                    
                    carriers = leg.get("carriers", {}).get("marketing", [])
                    provider = carriers[0].get("name", "Unknown") if carriers else "Unknown"
                    
                    segs = leg.get("segments", [])
                    flight_num = None
                    if segs:
                        fn = segs[0].get("flightNumber", "")
                        mc = segs[0].get("marketingCarrier", {}).get("alternateId", "")
                        if not mc and carriers:
                            mc = carriers[0].get("alternateId", "")
                        flight_num = _format_flight_code(provider, mc, fn)
                    
                    duration_mins = leg.get("durationInMinutes", 120)
                    dep_time = leg.get("departure", "")
                    arr_time = leg.get("arrival", "")
                    
                    if max_price and price > max_price:
                        continue

                    provenance, field_data_provenance = _transport_provenance(
                        f"Skyscanner RapidAPI ({provider})",
                        DataStatus.RECENTLY_VERIFIED,
                        "Search result retrieved recently, but fare and seat availability can change before booking. Verify before purchase.",
                        source_reference="https://www.skyscanner.co.in/",
                        ttl_seconds=3600,
                        confidence=0.8,
                        field_statuses={
                            "fare": DataStatus.RECENTLY_VERIFIED,
                            "schedule": DataStatus.RECENTLY_VERIFIED,
                            "availability": DataStatus.UNAVAILABLE,
                        },
                        retrieved_at=checked_at,
                    )
                        
                    flights.append({
                        "mode": "flight",
                        "provider": provider,
                        "code": flight_num,
                        "price": int(price),
                        "duration_minutes": duration_mins,
                        "departure_time": dep_time,
                        "arrival_time": arr_time,
                        "departure_city": origin.title(),
                        "arrival_city": destination.title(),
                        "is_fallback": False,
                        "field_provenance": {
                            "fare": "Flight search result",
                            "schedule": "Flight search result",
                            "availability": "Not provided by search result",
                        },
                        "field_data_provenance": {
                            key: value.model_dump(mode="json")
                            for key, value in field_data_provenance.items()
                        },
                        "provenance": provenance.model_dump(mode="json"),
                        "availability_status": "Not provided by search result",
                        "last_checked_at": checked_at.isoformat(),
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse flight itinerary: {e}")
                    continue
            
            flights = _best_flights_per_airline(flights)
            if not flights:
                return _get_fallback_flights(origin, destination, distance_km)
                
            return flights

    except Exception as e:
        logger.error(f"Skyscanner flight search failed: {e}")
        return _get_fallback_flights(origin, destination, distance_km)




# ── RailRadar Train Search ──────────────────────────────────────────────

@cached("trains", ttl_seconds=86400 * 30)  # Cache for 30 days
async def search_trains(
    origin: str,
    destination: str,
    date: Optional[str] = None,
    distance_km: float | None = None,
) -> list[dict]:
    """
    Search trains via RailRadar native API.
    Falls back to static data when API fails or no trains found.
    """
    origin_code = get_station_code(origin)
    dest_code = get_station_code(destination)
    
    # Try Mumbai Central mapping since RailRadar is strict about CSTM vs MMCT
    if dest_code == "CSTM":
        dest_code = "MMCT"
    if origin_code == "CSTM":
        origin_code = "MMCT"

    if not origin_code or not dest_code:
        logger.info(f"No station code for {origin} or {destination}, using fallback")
        fallbacks = _get_fallback_trains(origin, destination, distance_km)
        return [f.model_dump() for f in fallbacks]

    if not settings.railradar_api_key:
        logger.info("No RailRadar API key — using fallback train data")
        fallbacks = _get_fallback_trains(origin, destination, distance_km)
        return [f.model_dump() for f in fallbacks]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.railradar.in/v1/trains/between/{origin_code}/{dest_code}",
                headers={
                    "Authorization": f"Bearer {settings.railradar_api_key}",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning(f"RailRadar API failed, using fallback: {e}")
        fallbacks = _get_fallback_trains(origin, destination, distance_km)
        return [f.model_dump() for f in fallbacks]

    checked_at = datetime.now(timezone.utc)
    trains = []
    # Parse RailRadar response
    for train_entry in data.get("data", {}).get("trains", [])[:5]:
        try:
            train_details = train_entry.get("train", {})
            from_details = train_entry.get("from", {})
            to_details = train_entry.get("to", {})
            
            # RailRadar provides schedule metadata, but neither confirmed fares
            # nor seat availability. Never present its results as a live booking.
            duration_minutes = train_entry.get("duration", 0)
            distance = distance_km or _estimated_route_distance(origin, destination)
            estimated_fare = max(350, int(distance * 1.45 + 250))
            provenance, field_data_provenance = _transport_provenance(
                "RailRadar",
                DataStatus.SCHEDULE_ONLY,
                "Rail schedule data was retrieved recently, but the travel date, fare, and seat availability were not verified. Verify before booking.",
                source_reference="https://railradar.in/",
                ttl_seconds=21600,
                confidence=0.7,
                field_statuses={
                    "train": DataStatus.SCHEDULE_ONLY,
                    "schedule": DataStatus.SCHEDULE_ONLY,
                    "fare": DataStatus.ESTIMATED,
                    "availability": DataStatus.UNAVAILABLE,
                    "travel_date": DataStatus.UNAVAILABLE,
                },
                retrieved_at=checked_at,
            )

            trains.append({
                "mode": "train",
                "provider": train_details.get("name", "Unknown Train"),
                "code": train_details.get("number", ""),
                "price": estimated_fare,
                "duration_minutes": duration_minutes,
                "departure_time": from_details.get("departure", ""),
                "arrival_time": to_details.get("arrival", ""),
                "departure_city": origin.title(),
                "arrival_city": destination.title(),
                "is_fallback": False,
                "field_provenance": {
                    "train": "RailRadar schedule data",
                    "schedule": "RailRadar schedule data (not date-verified)",
                    "fare": "Estimated 3A fare",
                    "availability": "Not available",
                    "travel_date": "Not verified against operating days",
                },
                "field_data_provenance": {
                    key: value.model_dump(mode="json")
                    for key, value in field_data_provenance.items()
                },
                "provenance": provenance.model_dump(mode="json"),
                "availability_status": "Not available",
                "last_checked_at": checked_at.isoformat(),
            })
        except Exception as e:
            logger.warning(f"Failed to parse train data: {e}")
            continue

    if not trains:
        fallbacks = _get_fallback_trains(origin, destination, distance_km)
        return [f.model_dump() for f in fallbacks]

    return trains


def _road_option(origin: str, destination: str, distance_km: float) -> TransportOption:
    """Return a transparent self-drive/cab estimate; it is never a live quote."""
    checked_at = datetime.now(timezone.utc)
    provenance, field_data_provenance = _transport_provenance(
        "YatraAI road-trip estimator",
        DataStatus.ESTIMATED,
        "Road fare and duration are planning estimates based on distance; traffic, tolls, and provider availability were not verified. Verify before booking.",
        source_reference="app://transport/road-estimator",
        ttl_seconds=86400,
        confidence=0.45,
        field_statuses={
            "fare": DataStatus.ESTIMATED,
            "schedule": DataStatus.ESTIMATED,
            "availability": DataStatus.UNAVAILABLE,
        },
        retrieved_at=checked_at,
    )
    return TransportOption(
        mode=TransportMode.ROAD,
        provider="Road trip estimate",
        code=None,
        # Intercity cab estimate including a modest toll allowance.
        price=max(900, int(distance_km * 13 + 350)),
        duration_minutes=max(90, int(distance_km / 45 * 60)),
        departure_city=origin.title(),
        arrival_city=destination.title(),
        is_fallback=True,
        field_provenance={
            "fare": "Estimated intercity cab, fuel, and toll cost",
            "schedule": "Traveller-selected departure time",
            "availability": "Not checked",
        },
        field_data_provenance=field_data_provenance,
        provenance=provenance,
        availability_status="Not checked",
        last_checked_at=checked_at,
    )


# ── Combined Transport Search ─────────────────────────────────────────

async def search_transport(
    origin: str,
    destination: str,
    date: str,
    budget: int,
    distance_km: float,
) -> list[TransportOption]:
    """
    Search both flights and trains, returning combined results.
    Recommends based on budget and distance.
    """
    import asyncio

    flight_task = search_flights(
        origin, destination, date, max_price=budget, distance_km=distance_km
    )
    train_task = search_trains(origin, destination, date, distance_km=distance_km)

    flight_results, train_results = await asyncio.gather(
        flight_task, train_task, return_exceptions=True,
    )

    options: list[TransportOption] = []

    if isinstance(flight_results, list):
        for f in flight_results:
            options.append(TransportOption(**f))

    if isinstance(train_results, list):
        for t in train_results:
            options.append(TransportOption(**t))

    options.append(_road_option(origin, destination, distance_km))

    # Sort by price
    options.sort(key=lambda o: o.price)

    # Recommend based on distance and budget
    if options:
        if distance_km < 500 and budget < 10000:
            # Short distance, tight budget → recommend train
            for opt in options:
                if opt.mode == TransportMode.TRAIN:
                    opt.is_recommended = True
                    break
        else:
            # Long distance or comfortable budget → recommend cheapest flight
            for opt in options:
                if opt.mode == TransportMode.FLIGHT:
                    opt.is_recommended = True
                    break

        # If no recommendation set, recommend cheapest overall
        if not any(o.is_recommended for o in options):
            options[0].is_recommended = True

    return options
