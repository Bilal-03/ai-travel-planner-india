"""Phase 5 provider boundary, normalization, and resilience contracts."""

from __future__ import annotations

import asyncio

import pytest

from app.config import Settings
from app.providers.contracts import (
    FlightSearchRequest,
    RailSearchRequest,
)
from app.providers.gateway import ProviderGateway
from app.providers.resilience import (
    CircuitBreaker,
    CircuitState,
    ProviderErrorCode,
    ProviderExecutionError,
    ProviderExecutor,
    RetryPolicy,
)


async def _no_sleep(_delay: float) -> None:
    return None


def test_provider_executor_retries_once_then_returns_normalized_value():
    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary upstream failure")
        return "normalized"

    executor = ProviderExecutor(
        policy=RetryPolicy(timeout_seconds=0.1, max_retries=1, backoff_seconds=0),
        sleeper=_no_sleep,
    )

    assert asyncio.run(executor.execute(operation)) == "normalized"
    assert calls == 2
    assert executor.circuit.state == CircuitState.CLOSED


def test_provider_executor_opens_circuit_after_repeated_failures():
    calls = 0
    now = [0.0]

    async def operation() -> str:
        nonlocal calls
        calls += 1
        raise RuntimeError("provider down")

    breaker = CircuitBreaker(
        failure_threshold=2,
        cooldown_seconds=10,
        clock=lambda: now[0],
    )
    executor = ProviderExecutor(
        policy=RetryPolicy(timeout_seconds=0.1, max_retries=0, backoff_seconds=0),
        circuit=breaker,
        sleeper=_no_sleep,
    )

    for _ in range(2):
        with pytest.raises(ProviderExecutionError) as failure:
            asyncio.run(executor.execute(operation))
        assert failure.value.code == ProviderErrorCode.UNAVAILABLE

    assert calls == 2
    assert breaker.state == CircuitState.OPEN

    with pytest.raises(ProviderExecutionError) as blocked:
        asyncio.run(executor.execute(operation))
    assert blocked.value.code == ProviderErrorCode.CIRCUIT_OPEN
    assert calls == 2


def test_provider_executor_converts_timeout_to_safe_provider_error():
    async def slow_operation() -> str:
        await asyncio.sleep(0.05)
        return "too late"

    executor = ProviderExecutor(
        policy=RetryPolicy(timeout_seconds=0.001, max_retries=0, backoff_seconds=0),
        sleeper=_no_sleep,
    )

    with pytest.raises(ProviderExecutionError) as failure:
        asyncio.run(executor.execute(slow_operation))

    assert failure.value.code == ProviderErrorCode.TIMEOUT


def test_flight_callback_normalizes_before_service_boundary():
    async def callback(_request: FlightSearchRequest) -> list[dict]:
        return [{
            "mode": "flight",
            "provider": "Contract Air",
            "code": "CA101",
            "price": 4_500,
            "duration_minutes": 120,
            "departure_city": "Delhi",
            "arrival_city": "Mumbai",
        }]

    gateway = ProviderGateway(Settings())
    provider = gateway.flight_provider(callback)
    offers = asyncio.run(provider.search(FlightSearchRequest(
        origin="Delhi",
        destination="Mumbai",
        departure_date="2026-08-20",
    )))

    assert len(offers) == 1
    assert offers[0].provider == "Contract Air"
    assert offers[0].mode.value == "flight"
    assert offers[0].price == 4_500


def test_rail_callback_exposes_schedule_only_contract():
    async def callback(_request: RailSearchRequest) -> list[dict]:
        return [{
            "mode": "train",
            "provider": "Schedule Rail",
            "code": "12345",
            "price": 1_100,
            "duration_minutes": 300,
            "departure_city": "Delhi",
            "arrival_city": "Jaipur",
        }]

    gateway = ProviderGateway(Settings())
    provider = gateway.rail_provider(callback)
    request = RailSearchRequest(origin="Delhi", destination="Jaipur")

    schedules = asyncio.run(provider.search_schedules(request))
    availability = asyncio.run(provider.search_availability(request))

    assert schedules[0].provider == "Schedule Rail"
    assert availability == []


def test_unsupported_live_choices_fail_closed_and_return_no_invented_inventory():
    config = Settings()
    config.flight_provider = "amadeus"
    gateway = ProviderGateway(config)

    async def callback(_request: FlightSearchRequest) -> list[dict]:
        raise AssertionError("unsupported provider must not call the legacy adapter")

    flight_provider = gateway.flight_provider(callback)

    assert asyncio.run(flight_provider.search(FlightSearchRequest(
        origin="Delhi",
        destination="Mumbai",
        departure_date="2026-08-20",
    ))) == []


def test_gateway_exposes_all_feature_flag_domains():
    selected = ProviderGateway(Settings()).selected_providers()

    assert set(selected) == {
        "flight", "places", "routes", "rail", "weather",
    }


def test_weather_advisories_are_derived_without_claiming_official_alerts():
    from app.services.weather import _weather_alerts

    alerts = _weather_alerts("Thunderstorm", 0.9, 39)

    assert len(alerts) == 2
    assert "Severe weather signal" in alerts[0]
    assert "Heat advisory" in alerts[1]
