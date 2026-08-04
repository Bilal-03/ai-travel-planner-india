"""Transport labels and recommendation policy must remain explicit and testable."""

from app.models.trip import DataStatus, TransportMode, TransportOption
from app.services.gemini_planner import _select_transport
from app.services.transport import _get_fallback_trains


def _option(mode: TransportMode, price: int, minutes: int) -> TransportOption:
    return TransportOption(
        mode=mode,
        provider=f"{mode.value.title()} option",
        price=price,
        duration_minutes=minutes,
        departure_city="Delhi",
        arrival_city="Jaipur",
    )


def test_transport_distance_policy_changes_the_recommended_option():
    train = _option(TransportMode.TRAIN, price=900, minutes=300)
    flight = _option(TransportMode.FLIGHT, price=2_800, minutes=70)

    cheapest = _select_transport([train, flight], None, 260)
    fastest = _select_transport([train, flight], None, 900)

    assert cheapest is train
    assert fastest is flight
    assert flight.is_recommended
    assert not train.is_recommended


def test_fallback_train_labels_each_unverified_field_honestly():
    option = _get_fallback_trains("Delhi", "Jaipur")[0]

    assert option.field_provenance["train"].startswith("Static schedule")
    assert "date-verified" in option.field_provenance["schedule"]
    assert option.field_provenance["fare"].startswith("Estimated")
    assert option.field_provenance["availability"] == "Not available"
    assert option.availability_status == "Not available"
    assert option.last_checked_at is not None
    assert option.provenance.status == DataStatus.STATIC_REFERENCE
    assert option.field_data_provenance["fare"].status == DataStatus.ESTIMATED
    assert "Verify before booking" in option.provenance.disclaimer
