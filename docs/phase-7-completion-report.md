# Phase 7 completion report — offline access, collaboration, and production hardening

Branch: `codex/phase-7-production-hardening`
Implementation date: 2026-08-04

## Delivered

Phase 7 adds the production boundary around the existing planner without
changing the provider-neutral itinerary contract.

### Offline PWA

- Added a standalone web manifest and service-worker registration.
- Added a network-first shell and same-origin trip snapshot cache.
- Added a browser-local trip snapshot containing the itinerary summary,
  destination addresses, and emergency notes, with a 24-hour stale warning.
- Added online/offline state and stale-data indicators.
- `POST` requests are never cached, and map-tile requests are explicitly passed
  through without caching.

### Collaboration

- Added owner, editor, and viewer role models with expiring, revocable share
  links.
- Raw share tokens are returned only when a link is created; PostgreSQL stores
  SHA-256 token hashes.
- Added optional email-labelled collaborator invitations, view/edit access
  checks, immutable version history, structured activity history, optimistic
  `ETag`/`If-Match` conflict handling, and trip-copy endpoints.
- Single- and multi-city mutations accept editor links while viewer links stay
  read-only.

### Analytics and observability

- Added the eleven allowlisted product events from the implementation plan.
- Analytics metadata is allowlisted and trip identifiers are hashed; no user
  identity is collected.
- Added summary metrics for completion, success, latency, refinement
  acceptance, sharing, export, estimated-data use, freshness, invalid output,
  and estimated cost per completed trip.
- Added request and trip-job correlation IDs, JSON structured logs, provider
  latency metrics, and LLM usage metrics.
- Health output now reports readiness, Redis mode, database mode, and pending
  job depth.

### Security and reliability

- Production durable-storage mode now fails closed for trips, collaboration,
  analytics, and audit logs; it never silently
  serves process-local persistence.
- Added Redis-backed rate limits with a distributed-counter requirement when
  `REQUIRE_REDIS=true`.
- Added request-size limits for both declared and chunked mutation bodies,
  strict environment-aware CORS, an optional bot-protection gateway token, and
  sanitized API error responses.
- Added SSRF validation for provider-returned image and attribution URLs.
- Bounded traveller free text before it reaches Gemini and explicitly labels it
  as untrusted data in the planning prompts.
- Added audit records for collaboration changes, share-link actions, trip
  copies, and other sensitive trip actions.

## Persistence and migration

`backend/migrations/005_phase7_collaboration_analytics.sql` adds the append-only
`itinerary_versions` and `trip_edits` tables, hashed `share_links`,
`collaborators`, privacy-safe `analytics_events`, and `audit_logs`. The runtime
schema initializer remains useful for local development, but hosted databases
must apply the ordered migrations before production readiness is enabled.

The migration checker validates all seven ordered migration files and the Phase 7
tables. Migration 006 removes the retired account schema from databases that
ran the earlier account-based implementation. Migration 007 removes a retired
multi-city projection from earlier itinerary deployments. See
[backend/migrations/README.md](../backend/migrations/README.md).

## Production configuration

Before deployment:

1. Apply migrations `001` through `007` to staging, verify the schema, then
   apply them to production.
2. Set `APP_ENV=production`, `REQUIRE_DURABLE_STORAGE=true`, and
   `REQUIRE_REDIS=true`.
3. Configure `DATABASE_URL`, both Upstash Redis variables, and a long random
   `TRIP_JOB_SECRET`.
4. Set the exact deployed frontend origin in `FRONTEND_URL`; do not use a
   wildcard CORS origin.
5. Deploy only after `/health` reports `ready: true` and `database: neon`,
   `redis: redis`.

## CI/CD

`.github/workflows/ci.yml` runs frontend lint/type/unit/build checks, backend
lint/Phase 7 type checks/unit tests, migration checks, API contract tests,
Playwright smoke tests, dependency audits, secret scanning, and pull-request
dependency review.

The Phase 7 mypy gate covers the hardened boundary and new collaboration,
analytics, storage, and observability modules. Legacy planner typing remains a
separate cleanup track because the pre-existing full-tree invocation reports
errors in older planner modules.

## Exit evidence

- `backend/.venv/bin/python -m pytest -q`: **83 passed**, one existing
  Starlette/httpx deprecation warning.
- `backend/.venv/bin/python -m compileall -q app main.py`: passed.
- Phase 7 Ruff syntax/undefined-name gate: passed.
- Phase 7 mypy gate: **17 source files**, no issues.
- `backend/.venv/bin/python scripts/check_migrations.py`: **7 ordered
  migrations validated**.
- `npm run lint`: passed.
- `npx tsc --noEmit`: passed.
- `npm run test:unit`: **2 passed**.
- `npm run build`: passed.
- `npm run test:e2e`: **2 passed**.

## Known operational boundaries

- Offline storage is browser-local and intentionally expires into a visible
  stale state; live fares, venue hours, weather, and booking availability still
  require connectivity and independent verification.
- The service worker never caches cross-origin map tiles or backend responses;
  the localStorage snapshot is the offline source of truth for the trip page.
- Share-link listings cannot reconstruct a raw token after creation because
  only hashes are persisted; the creation response is the copyable link.
- Local in-memory fallbacks remain available for development only. Production
  must keep both durable-storage and Redis requirements enabled.
