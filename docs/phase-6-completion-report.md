# Phase 6 completion report — multi-city planning

Branch: `codex/phase-6-multi-city-accounts`  
Audit/implementation date: 2026-08-04

## Delivered

Phase 6 adds a real multi-destination aggregate alongside the stable legacy
single-destination flow. A route is represented with explicit
`DestinationStay`, `TravelLeg`, `ItineraryDay`, `Visit`,
`AccommodationSelection`, and `TransportSelection` entities.

The `POST /api/multi-city/generate` path composes a three-city route with an
automatic return leg. Each stay and visit retains a stable identity. Route
reordering recalculates the leg graph and shifts existing visit dates; changing
one stay's nights or notes updates only dependent dates and leg dates,
preserving unrelated destination visit identities.

The frontend adds a multi-city route studio with stop ordering, nights editing,
leg comparisons, day shells, and budget visibility. The existing asynchronous
single-destination job flow and anonymous shared links remain available.

## Anonymous access model

The app is intentionally account-free. It does not create user profiles,
sessions, logins, saved-trip history, or preference memory. Every generated
trip receives a random edit token in the response header; only its hash is
stored. The browser keeps that capability in session storage, and optional
share links provide read or edit access to the persisted itinerary.

## Persistence and migration

`backend/migrations/004_phase6_multi_city.sql` adds:

- the `multi_city_trips` aggregate;
- normalized stay, leg, visit, day, accommodation-selection, and
  transport-selection projections;
- the anonymous edit-token hash and previous-trip revision fields needed for
  shared-trip editing and undo.

The runtime store applies the same schema additively for configured PostgreSQL
deployments and retains an in-memory fallback for local development.

## Exit evidence

- `backend/.venv/bin/python -m pytest -q`: 74 tests passed before the later
  account-removal change.
- `backend/.venv/bin/python -m pytest -q tests/test_phase6_multi_city.py`:
  multi-city tests passed before the later account-removal change.
- `python3 -m compileall -q backend/app backend/tests`: passed.
- `npm run lint`: passed.
- `npx tsc --noEmit`: passed.

## Known limitations

- The multi-city route uses deterministic composition and transparent
  provider/fallback facts; Gemini narration remains scoped to the existing
  single-destination planner.
- Hotel inventory remains fail-closed per Phase 5. Accommodation selections
  are category estimates, not bookable property offers.
- Backend test dependencies are available in `backend/.venv`; a system
  `python3` without the project dependencies can only run compile checks.
