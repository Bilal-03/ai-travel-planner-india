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
| `UPSTASH_REDIS_REST_URL` | No | `redis_cache.py` | Enables the Redis cache when paired with its token; otherwise memory cache is used. |
| `UPSTASH_REDIS_REST_TOKEN` | No | `redis_cache.py` | Credential for the Upstash Redis client. |
| `FRONTEND_URL` | Yes in deployment | `main.py`, `api/trips.py` | CORS origin and base used when constructing a server-side share URL. |
| `BACKEND_PORT` | No | `config.py` | Default local port setting; Render uses its injected `PORT` in the start command. |
| `NOMINATIM_RPS` | No | `config.py` | Configured setting exists, but the current geocoder uses its own one-request-per-second limiter. |
| `OVERPASS_RPS` | No | `config.py` | Configured setting exists, but the current POI service uses its own limiter. |
| `OSRM_RPS` | No | `config.py` | Configured setting exists, but the current routing service uses its own limiter. |

The current Render configuration declares the provider/database/cache keys
and `FRONTEND_URL`; the rate settings and `GEMINI_MODEL` are not explicitly
listed in `backend/render.yaml` but can still be supplied as environment
variables by the host.

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
| Redis URL/token | Process-local cache, progress, and rate limits | No cross-instance coordination; duplicate work and inconsistent limits are possible. |

## Variables not yet implemented

The Phase 5 provider-gateway plan calls for `FLIGHT_PROVIDER`,
`HOTEL_PROVIDER`, `PLACES_PROVIDER`, `ROUTES_PROVIDER`, `RAIL_PROVIDER`,
`BUS_PROVIDER`, and `WEATHER_PROVIDER`. They are intentionally not added in
Phase 0 because no provider abstraction is being introduced.

No environment variables are added by the Phase 0 branch.
