# YatraAI data-provider inventory

Audit date: 2026-08-04

This inventory distinguishes external, curated, calculated, and fallback data.
The current transport implementation has per-field provenance labels; the
common `DataProvenance` model described in the master plan is not implemented
yet.

## Current provider map

| Domain | Current implementation | Source type | Current fallback and label | Cache / freshness | Main risk |
| --- | --- | --- | --- | --- | --- |
| City search and geocoding | `services/india_cities.py`, `services/geocoding.py` | Bundled city index, then Nominatim | No result when both fail; India bounding-box check | Local/index and cached geocodes; Nominatim cache 30 days | A bounding box is not a full administrative validation; public geocoder availability is external. |
| Flights | `services/transport.py` | Skyscanner RapidAPI when keyed | Static route/fare guidance or calculated fare, marked `is_fallback` with `Estimated fare guidance` | One-hour cache | Search results do not confirm booking inventory; fallback routes contain hard-coded fare guidance. |
| Trains | `services/transport.py` | RailRadar schedule endpoint when keyed | Static train reference or calculated fare estimate; schedule/availability are labelled unavailable or not date-verified | Thirty-day cache keyed with request date, but upstream route response is not date-verified | The source returns schedule metadata, not confirmed fare or seats; the fallback can look like a named train. |
| Road | `services/transport.py` | Deterministic distance/cost formula | `Road trip estimate`, not a quote | Included in the request result; no external freshness | It is a planning estimate, not cab availability or a booking quote. |
| Places / POIs | `services/poi_discovery.py` and `data/landmark_catalogue.py` | Reviewed catalogue plus Overpass | Reviewed catalogue remains when Overpass fails | POI discovery cached seven days; catalogue has review dates | Opening hours, prices, closures, and accessibility are not common provenance facts. |
| Routes | `services/routing.py` | OSRM driving route | Haversine-derived distance and 30-minute segment estimate | Route cache seven days | Fallback duration is conservative but not a live route; route mode is always driving. |
| Weather | `services/weather.py` | OpenWeatherMap forecast | Empty forecast; planner notes weather unavailable | Six-hour cache | Forecast window is limited by the upstream five-day endpoint and there is no common retrieval/expiry object in the response. |
| Destination photos | `services/photos.py` | Unsplash search | Empty photo list | Seven-day cache | Image metadata has no provenance contract in the itinerary model. |
| Festivals | `services/festivals.py` | Static catalogue | Generation currently sends an empty festival list | No generation-time freshness contract | Static event dates must not be presented as current facts without review. |

## Data categories currently exposed

The existing `TransportOption` exposes:

- `is_fallback` for a broad fallback signal;
- `field_provenance` for ad hoc labels such as `Estimated 3A fare`,
  `Static schedule reference (not date-verified)`, and `Not available`;
- `availability_status`; and
- `last_checked_at`.

Other domain models do not expose equivalent status fields. The frontend
renders these transport labels in `TransportCard`, but it does not yet share
reusable `DataStatusBadge`, attribution, freshness, or disclaimer components.

The target statuses in the plan are:

```text
live
recently_verified
schedule_only
estimated
static_reference
unavailable
```

No current path should infer that a fallback fare, route duration, or weather
absence is live. The current UI uses `Estimated`, `Not available`, and detailed
field labels for transport; the lack of a common contract is a Phase 1 risk.

## Provider configuration

Current provider credentials are optional except Gemini at product level:

- `SKYSCANNER_RAPIDAPI_KEY` controls flight search.
- `RAILRADAR_API_KEY` controls train schedule search.
- `OPENWEATHERMAP_API_KEY` controls weather.
- `UNSPLASH_ACCESS_KEY` controls destination photos.
- Nominatim, Overpass, and OSRM use public endpoints without configured keys.

There are currently no `FLIGHT_PROVIDER`, `HOTEL_PROVIDER`,
`PLACES_PROVIDER`, `ROUTES_PROVIDER`, `RAIL_PROVIDER`, `BUS_PROVIDER`, or
`WEATHER_PROVIDER` feature flags. Hotels and buses have no provider adapter in
the current app.

## Target provider boundary

Phase 5 should introduce interfaces for flights, hotels, rail, buses, places,
routes, and weather, normalize responses before they reach the itinerary
model, and attach the common provenance object to every displayed travel fact.
It should preserve the current providers until replacements pass contract and
fallback tests.
