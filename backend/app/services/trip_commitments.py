"""Shared helpers for trip-level choices that must survive plan changes.

The itinerary's day plans are regenerated and revalidated during refinement,
while saved stays live in the normalized ``items`` collection.  These helpers
keep the two representations consistent without pretending that a planning
estimate is a reservation.
"""

from __future__ import annotations

from copy import deepcopy

from app.models.trip import BudgetBreakdown, Itinerary, ItineraryItem, ItineraryItemType


def stay_total_from_items(items: list[ItineraryItem]) -> int:
    """Return the saved stay estimate total encoded in itinerary items."""

    total = 0
    for item in items:
        if item.item_type != ItineraryItemType.STAY:
            continue
        value = item.metadata.get("total_price")
        if isinstance(value, (int, float)):
            total += max(0, int(value))
    return total


def sync_stay_budget_line(budget: BudgetBreakdown, stay_amount: int) -> None:
    """Adjust only the stay line and its roll-up in an existing budget."""

    clean_amount = max(0, int(stay_amount))
    delta = clean_amount - budget.stay
    budget.stay = clean_amount
    budget.total_estimated += delta
    budget.remaining -= delta


def sync_trip_commitment_budgets(itinerary: Itinerary) -> Itinerary:
    """Apply the saved-item stay amount to the active and alternative budgets."""

    stay_amount = stay_total_from_items(itinerary.items)
    sync_stay_budget_line(itinerary.budget, stay_amount)
    for option in itinerary.plan_options:
        sync_stay_budget_line(option.budget, stay_amount)
        if option.id == itinerary.selected_plan_id:
            option.budget = deepcopy(itinerary.budget)
    return itinerary


def preserve_trip_commitments(previous: Itinerary, updated: Itinerary) -> Itinerary:
    """Carry normalized trip-level items and their budget line into a revision."""

    updated.items = deepcopy(previous.items)
    return sync_trip_commitment_budgets(updated)
