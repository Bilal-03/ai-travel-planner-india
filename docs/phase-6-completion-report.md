# Phase 6 completion report — multi-city planning and user memory

Branch: `codex/phase-6-multi-city-accounts`  
Audit/implementation date: 2026-08-04

## Delivered

Phase 6 adds a real multi-destination aggregate alongside the stable legacy
single-destination flow. A route is no longer represented as a destination
array: it contains explicit `DestinationStay`, `TravelLeg`, `ItineraryDay`,
`Visit`, `AccommodationSelection`, and `TransportSelection` entities.

The new `POST /api/multi-city/generate` path can compose a three-city route with
an automatic return leg. Each stay and visit retains a stable identity. Route
reordering recalculates the leg graph and shifts existing visit dates; changing
one stay's nights/notes updates only dependent dates and leg dates, preserving
unrelated destination visit identities.

The frontend adds a multi-city route studio with stop ordering, nights editing,
leg comparisons, day shells, and budget visibility. The existing asynchronous
single-destination job flow and shared read-only links are unchanged.

Anonymous visitors receive a signed continuity session. They can optionally
upgrade that session to an account, view saved single- and multi-city trip
history, claim an anonymous trip with the creator edit token, delete their
account and saved trips, and manage explicit preference memory. Memory exposes
transport, hotel category, budget range, dietary preference, pace,
accessibility requirements, and departure times; users can view, edit, disable,
or delete it. No sensitive attributes are inferred.

Supabase Auth is the managed deployment target because the current architecture
is Next.js plus PostgreSQL. The backend accepts and verifies HS256 Supabase JWTs
when configured, while a signed local-session adapter keeps local development
usable without provider credentials. Supabase Auth uses JWTs and supports the
Next.js App Router/server-side flow described in the [official Auth overview](https://supabase.com/docs/guides/auth)
and [Next.js quickstart](https://supabase.com/docs/guides/auth/quickstarts/nextjs).

## Persistence and migration

`backend/migrations/004_phase6_multi_city_accounts.sql` adds:

- the `multi_city_trips` aggregate and normalized stay/leg/visit/day/selection
  projections;
- account, session, and preference-memory tables;
- optional account ownership on legacy `trips`.

The runtime store applies the same schema additively for configured PostgreSQL
deployments and retains an in-memory fallback for local development.

## Exit evidence

- `backend/.venv/bin/python -m pytest -q`: 74 tests passed.
- `backend/.venv/bin/python -m pytest -q tests/test_phase6_multi_city.py`: 4 tests passed.
- `python3 -m compileall -q backend/app backend/tests`: passed.
- `npm run lint`: passed.
- `npx tsc --noEmit`: passed.
- Production build and the existing Playwright flow remain the final checks
  before handoff.

## Known limitations

- The local account adapter is intended for development and controlled fallback;
  production cross-device authentication should configure Supabase Auth and
  apply the migration against PostgreSQL.
- The multi-city route currently uses deterministic composition and transparent
  provider/fallback facts; Gemini narration is still scoped to the existing
  single-destination planner.
- Hotel inventory remains fail-closed per Phase 5. Accommodation selections are
  category estimates, not bookable property offers.
- Backend test dependencies are available in `backend/.venv`; a system
  `python3` without the project dependencies can only run compile checks.
