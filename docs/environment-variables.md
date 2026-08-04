# YatraAI environment variables

Audit date: 2026-08-04

The root `.env.example` is the primary checked-in template for backend/local
settings. `backend/app/config.py` loads `.env` and `../.env` and uses
`pydantic-settings` name conversion, so uppercase environment names map to the
lowercase `Settings` fields. Never commit actual `.env` or `.env.local` files.

## Backend and shared variables

| Variable | Required | Used by | Current behavior |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Product-required | `gemini_planner.py` | Enables Gemini; missing key triggers the deterministic fallback planner. |
| `GEMINI_MODEL` | No | `config.py` | Overrides the default configured model name; default is `gemini-2.5-flash`. |
| `SKYSCANNER_RAPIDAPI_KEY` | No | `transport.py` | Enables flight search; missing or failed search returns labelled estimate guidance. |
| `RAILRADAR_API_KEY` | No | `transport.py` | Enables rail schedule search; missing or failed search returns labelled static/estimated records. |
| `OPENWEATHERMAP_API_KEY` | No | `weather.py` | Enables forecast data; otherwise forecast is unavailable. |
| `UNSPLASH_ACCESS_KEY` | No | `photos.py` | Enables destination photos; otherwise the photo list is empty. |
| `DATABASE_URL` | No locally; operationally important in production | `trip_storage.py` | Enables Neon-compatible PostgreSQL; absent or failing storage uses an in-memory dictionary. |
| `UPSTASH_REDIS_REST_URL` | Strongly recommended for production | `redis_cache.py`, `services/trip_jobs.py` | Enables shared cache, job queue, event replay, idempotency, cancellation, and distributed coordination when paired with its token; otherwise process-local fallback is used. |
| `UPSTASH_REDIS_REST_TOKEN` | Strongly recommended for production | `redis_cache.py`, `services/trip_jobs.py` | Credential for the Upstash Redis client. |
| `TRIP_JOB_SECRET` | Strongly recommended for production | `config.py`, `services/trip_jobs.py` | Secret used to derive the edit token returned for completed asynchronous jobs. A development fallback exists, but production deployments must set this explicitly. |
| `AUTH_PROVIDER` | No locally; `supabase` in managed deployment | `config.py`, `services/account_service.py` | Selects the account boundary. `local` is the signed-session fallback; `supabase` enables inbound Supabase JWT verification when the secret is present. |
| `SUPABASE_URL` | Required for a Supabase deployment | `config.py` | Records the managed auth project URL for deployment configuration. |
| `SUPABASE_JWT_SECRET` | Required for HS256 Supabase JWT verification | `config.py`, `services/account_service.py` | Verifies bearer tokens and auto-provisions an account record from the JWT subject. Keep it server-only. |
| `ACCOUNT_SESSION_TTL_SECONDS` | No | `config.py`, `services/account_service.py` | Lifetime of local signed account sessions; default is 30 days. |
| `FRONTEND_URL` | Yes in deployment | `main.py`, `api/trips.py` | CORS origin and base used when constructing a server-side share URL. |
| `BACKEND_PORT` | No | `config.py` | Default local port setting; Render uses its injected `PORT` in the start command. |
| `NOMINATIM_RPS` | No | `config.py` | Configured setting exists, but the current geocoder uses its own one-request-per-second limiter. |
| `OVERPASS_RPS` | No | `config.py` | Configured setting exists, but the current POI service uses its own limiter. |
| `OSRM_RPS` | No | `config.py` | Configured setting exists, but the current routing service uses its own limiter. |
| `FLIGHT_PROVIDER` | No | `providers/gateway.py` | Defaults to `legacy` (Skyscanner adapter); unsupported values fail closed to labelled fallback. |
| `HOTEL_PROVIDER` | No | `providers/gateway.py` | Defaults to `none`; no hotel inventory is shown until a contracted adapter is enabled. |
| `PLACES_PROVIDER` | No | `providers/gateway.py` | Defaults to `overpass`; unsupported values fall back to the reviewed catalogue. |
| `ROUTES_PROVIDER` | No | `providers/gateway.py` | Defaults to `osrm`; unsupported values let feasibility use its deterministic estimate. |
| `RAIL_PROVIDER` | No | `providers/gateway.py` | Defaults to `legacy` (RailRadar schedule adapter); fares and seats remain unverified. |
| `BUS_PROVIDER` | No | `providers/gateway.py` | Defaults to `none`; operators and schedules are never invented. |
| `WEATHER_PROVIDER` | No | `providers/gateway.py` | Defaults to `openweather`; unsupported values leave weather unavailable. |
| `PROVIDER_TIMEOUT_SECONDS` | No | `providers/resilience.py` | Gateway timeout per attempt; default `20`. Provider HTTP clients retain their own shorter timeouts. |
| `PROVIDER_MAX_RETRIES` | No | `providers/resilience.py` | Number of bounded retries after the first attempt; default `1`. |
| `PROVIDER_RETRY_BACKOFF_SECONDS` | No | `providers/resilience.py` | Exponential retry backoff base; default `0.25`. |
| `PROVIDER_CIRCUIT_FAILURE_THRESHOLD` | No | `providers/resilience.py` | Consecutive failed calls before opening a domain circuit; default `3`. |
| `PROVIDER_CIRCUIT_COOLDOWN_SECONDS` | No | `providers/resilience.py` | Time before a half-open probe; default `30`. |

The current Render configuration declares the provider/database/cache keys,
provider selections/resilience defaults, and `FRONTEND_URL`; the rate settings
and `GEMINI_MODEL` can still be supplied as environment variables by the host.

## Frontend variables

| Variable | Required | Used by | Current behavior |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Yes for deployed frontend | `frontend/src/lib/api.ts` | Backend base URL; defaults to `http://localhost:8000` locally. |
| `NEXT_PUBLIC_SITE_URL` | Optional | Root template/deployment convention | Intended public-site URL; current client API code does not use it directly. |

The dynamic shared-trip metadata fetch also reads `NEXT_PUBLIC_API_URL` on the
server. A deployed frontend therefore needs the same backend URL available at
build/runtime according to the Vercel environment configuration.

## Current fallback matrix

| Missing setting | Local result | Production risk |
| --- | --- | --- |
| `GEMINI_API_KEY` | Basic deterministic plan | User loses AI personalization; still receives a plan. |
| Transport keys | Estimated/static labelled options | No date-specific live offers or availability. |
| `OPENWEATHERMAP_API_KEY` | No forecast and an itinerary note | Weather-sensitive planning is less informed. |
| `UNSPLASH_ACCESS_KEY` | No destination photos | Cosmetic degradation only. |
| `DATABASE_URL` | Process-local trips | Trips disappear on restart and are not shared across instances. |
| Redis URL/token | Process-local cache, jobs, progress, rate limits, and provider caches | No cross-instance coordination; jobs and replay history are not restart-durable and duplicate work is possible. Provider circuit state is process-local by design in Phase 5. |
| `SUPABASE_JWT_SECRET` | Local signed-session fallback remains usable | Managed bearer-token account access is not enabled; configure Supabase before production cross-device auth. |
| `DATABASE_URL` for Phase 6 | Account/trip data remains process-local | Anonymous/account history, preference memory, and multi-city normalized projections disappear on restart. |

Phase 2 adds `TRIP_JOB_SECRET` and makes Redis strongly recommended for durable
multi-instance job processing. Phase 6 adds the auth variables above; no new
frontend variables are required for the local fallback. A managed Supabase
frontend can add its public URL/key according to the official Next.js SSR
quickstart.
