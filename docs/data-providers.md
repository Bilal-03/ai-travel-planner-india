# YatraAI data-provider inventory

Audit date: 2026-08-04

This inventory distinguishes external, curated, calculated, and fallback data.
Phase 1 adds a common `DataProvenance` model to every displayed travel-data
family while retaining the existing transport labels for compatibility.

## Current provider map

| Domain | Current implementation | Source type | Current fallback and label | Cache / freshness | Main risk |
| --- | --- | --- | --- | --- | --- |
| City search and geocoding | `services/india_cities.py`, `services/geocoding.py` | Bundled city index, then Nominatim | `static_reference` or `recently_verified` coordinates | Local/index and cached geocodes; Nominatim cache 30 days | A bounding box is not a full administrative validation; public geocoder availability is external. |
| Flights | `services/transport.py` | Skyscanner RapidAPI when keyed | Static/calculated fares are `estimated`; search results are `recently_verified` with unconfirmed availability | One-hour cache and one-hour provenance expiry | Search results do not confirm booking inventory; fallback routes contain hard-coded fare guidance. |
| Trains | `services/transport.py` | RailRadar schedule endpoint when keyed | `schedule_only` schedule, `estimated` fare, unavailable seats/date verification; static references are `static_reference` | Thirty-day provider cache, with shorter fact windows | The source returns schedule metadata, not confirmed fare or seats; the fallback can look like a named train. |
| Road | `services/transport.py` | Deterministic distance/cost formula | `estimated`, never a live quote | Included in the request result with a one-day estimate window | It is a planning estimate, not cab availability or a booking quote. |
| Places / POIs | `services/poi_discovery.py` and `data/landmark_catalogue.py` | Reviewed catalogue plus Overpass | Catalogue is `static_reference`; OSM records are `recently_verified`; costs/durations are `estimated` | POI discovery cached seven days; catalogue has review dates | Opening hours, prices, closures, and accessibility still need direct verification. |
| Routes | `services/routing.py` | OSRM driving route | OSRM is `recently_verified`; fallback is `estimated` | Route cache and provenance window seven days | Fallback duration is conservative but not a live route; route mode is always driving. |
| Weather | `services/weather.py` | OpenWeatherMap forecast | Forecast facts are `recently_verified` for a six-hour window; absent data is unavailable | Six-hour cache and expiry | Forecast window is limited by the upstream five-day endpoint and should be rechecked near travel. |
| Destination photos | `services/photos.py` | Unsplash search | Returned images are `recently_verified` for attribution purposes; absent list stays empty | Seven-day cache | Images are illustrative and do not verify the exact venue or conditions. |
| Festivals | `services/festivals.py` | Static catalogue | Generation currently sends an empty festival list | No generation-time freshness contract | Static event dates must not be presented as current facts without review. |

## Data categories currently exposed

The existing `TransportOption` exposes:

- `is_fallback` for a broad fallback signal;
- `field_provenance` for ad hoc labels such as `Estimated 3A fare`,
  `Static schedule reference (not date-verified)`, and `Not available`;
- `availability_status`; and
- `last_checked_at`.

Other domain models now expose `provenance` and, where needed, field-level
provenance. The frontend renders these through reusable `DataStatusBadge`,
`ProviderAttribution`, `FreshnessTimestamp`, and `EstimateDisclaimer`
components in transport, weather, budget, activity, and meal views.

The target statuses in the plan are:

```text
live
recently_verified
schedule_only
estimated
static_reference
unavailable
```

Fallback fares, route durations, meal costs, POI costs, and budget totals are
explicitly `estimated` or `static_reference`; absent provider data is
`unavailable`. Expired facts are treated as stale by the model/UI and are not
presented as live claims. Non-live values carry a verify-before-booking or
verify-before-visiting disclaimer.

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
model, and extend the Phase 1 provenance object to every newly added provider.
It should preserve the current providers until replacements pass contract and
fallback tests.
