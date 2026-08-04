"""Phase 1 data-trust contract and provider disclosure tests."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.models.trip import (
    DataProvenance,
    DataStatus,
    TransportMode,
    TransportOption,
)
from app.services import transport
from app.services.transport import _get_fallback_flights, _get_fallback_trains


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _transport_option(**overrides) -> TransportOption:
    payload = {
        "mode": TransportMode.TRAIN,
        "provider": "Fixture train",
        "price": 900,
        "duration_minutes": 240,
        "departure_city": "Delhi",
        "arrival_city": "Jaipur",
        **overrides,
    }
    return TransportOption(**payload)


def test_missing_provider_defaults_to_unavailable():
    provenance = DataProvenance()

    assert provenance.provider == "not_provided"
    assert provenance.status == DataStatus.UNAVAILABLE
    assert provenance.disclaimer


def test_expired_facts_are_stale_and_not_effectively_live():
    now = _now()
    provenance = DataProvenance(
        provider="fixture",
        status=DataStatus.RECENTLY_VERIFIED,
        retrieved_at=now - timedelta(hours=3),
        expires_at=now - timedelta(hours=1),
    )

    assert provenance.is_stale(now)
    assert provenance.effective_status(now) == DataStatus.UNAVAILABLE


def test_estimated_fare_cannot_be_marked_live_on_fallback_transport():
    now = _now()
    live = DataProvenance(
        provider="fixture provider",
        status=DataStatus.LIVE,
        retrieved_at=now,
        expires_at=now + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="Fallback transport"):
        _transport_option(
            is_fallback=True,
            provenance=DataProvenance(
                provider="fixture provider",
                status=DataStatus.ESTIMATED,
                retrieved_at=now,
                expires_at=now + timedelta(hours=1),
            ),
            field_data_provenance={"fare": live},
        )


def test_static_transport_has_explicit_schedule_and_fare_statuses():
    options = _get_fallback_trains("Delhi", "Jaipur")

    assert options
    option = options[0]
    assert option.provenance.status == DataStatus.STATIC_REFERENCE
    assert option.field_data_provenance["schedule"].status == DataStatus.STATIC_REFERENCE
    assert option.field_data_provenance["fare"].status == DataStatus.ESTIMATED
    assert option.field_data_provenance["availability"].status == DataStatus.UNAVAILABLE
    assert "Verify before booking" in option.provenance.disclaimer


def test_estimated_flight_fallback_has_non_live_fare():
    option = _get_fallback_flights("Delhi", "Jaipur")[0]
    parsed = TransportOption(**option)

    assert parsed.provenance.status == DataStatus.ESTIMATED
    assert parsed.field_data_provenance["fare"].status == DataStatus.ESTIMATED
    assert parsed.field_data_provenance["fare"].status != DataStatus.LIVE


def test_every_combined_transport_response_has_provenance(monkeypatch: pytest.MonkeyPatch):
    async def fake_flights(*_args, **_kwargs):
        return _get_fallback_flights("Delhi", "Mumbai")

    async def fake_trains(*_args, **_kwargs):
        return [option.model_dump(mode="json") for option in _get_fallback_trains("Delhi", "Mumbai")]

    monkeypatch.setattr(transport, "search_flights", fake_flights)
    monkeypatch.setattr(transport, "search_trains", fake_trains)

    options = asyncio.run(
        transport.search_transport(
            origin="Delhi",
            destination="Mumbai",
            date="2026-08-20",
            budget=100_000,
            distance_km=1_150,
        )
    )

    assert options
    assert all(option.provenance is not None for option in options)
    assert all(option.provenance.provider != "" for option in options)
    assert all(option.field_data_provenance for option in options)
