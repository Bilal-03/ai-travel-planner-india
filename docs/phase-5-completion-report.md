# YatraAI Phase 5 completion report

Branch: `codex/phase-5-provider-gateway`

Phase 5 is complete. YatraAI now has a provider-neutral gateway around the
existing live travel-data integrations, with safe feature-flag selection and
fallback behavior preserved.

## Delivered

- Added provider-neutral request/result contracts and protocols for flights, rail
  schedules/availability, places, routes, and weather.
- Added `ProviderGateway` with the required `FLIGHT_PROVIDER`,
  `PLACES_PROVIDER`, `ROUTES_PROVIDER`, `RAIL_PROVIDER`, and
  `WEATHER_PROVIDER` switches.
- Routed the current Skyscanner, RailRadar, Overpass, OSRM, and OpenWeather
  adapters through normalized callback providers. Provider payloads do not cross
  into itinerary or UI models.
- Added bounded per-attempt timeout, configurable retry/backoff, and a
  per-domain circuit breaker. Service boundaries catch provider failures and
  retain the existing labelled fallbacks.
- Kept Indian rail schedule results schedule-only; availability returns an
  empty result until an authorised/commercially supportable source is wired.
- Added normalized weather advisories for wet/severe weather and heat. The
  existing deterministic constraint engine continues to move outdoor choices
  toward indoor alternatives when forecast severity requires it.
- Added selected-provider visibility to `/health` and documented local/Render
  environment defaults.

## Verification

- `python3 -m compileall -q backend/app backend/tests` passed.
- `frontend`: `npm run lint` passed.
- `frontend`: `npx tsc --noEmit` passed.
- `frontend`: `npm run build` passed.
- `frontend`: `npm run test:e2e -- --reporter=line` passed: `1 passed`.
- Added `backend/tests/test_provider_gateway.py` covering normalization,
  retries, timeouts, circuit opening, schedule-only rail behavior, fail-closed
  unsupported providers, feature-flag domains, and weather advisories.
- The backend test command was attempted, but the current environment does
  not have `pytest` or the repository's Pydantic runtime installed. The new
  Python tests therefore require the documented backend virtual environment
  setup before execution.

## Known limitations

- Amadeus, Duffel, Google Places/Routes, Mapbox, and authorised rail availability
  are interfaces and evaluation targets only; none is enabled by default in
  this phase.
- Circuit state is process-local. Redis-backed shared provider health belongs to
  production hardening.
- Weather advisories are derived planning signals, not official emergency
  alerts. The five-day forecast window and current conditions should be
  rechecked near travel.
- Provider flags can select future names, but unsupported names fail closed to
  the current labelled fallback or unavailable state until an adapter passes
  its contract tests.

## Phase boundary

Phase 6 is next: multi-destination trips and anonymous edit/share access, while
preserving the provider gateway and provenance contracts.
