# AI Travel Itinerary Planner — India Domestic (Free-Tier Stack)

Scope narrowed to **domestic India travel only** (any city/state to any city/state within India). This actually simplifies things a lot: no currency conversion, no visa logic, no international flight complexity, and it opens up train travel (a very Indian, very real travel mode) as a first-class option alongside flights.

Everything below is chosen to run on **free tiers with no or minimal upfront cost.** I've flagged where a free tier requires a card and where it doesn't, since that matters for what you can realistically prototype without spending money.

---

## 1. Revised Tech Stack (Free-Tier First)

| Layer | Choice | Free tier reality (as of mid-2026) |
|---|---|---|
| LLM | **Google Gemini API** (`gemini-2.5-flash` or `gemini-3-flash`) | No credit card needed. ~1,500 requests/day, 15 RPM, 1M tokens/min on Flash. This easily covers a solo-dev MVP. Enabling billing later removes the free tier on that project, so keep a separate "dev" project with billing off. |
| LLM (fallback/alt) | Groq API (Llama 3.x / open models) | No card required, fast inference, free tier ~1,000 req/day per model. Good as a second option if you want to A/B or if Gemini quota runs out. |
| Maps/Places (primary, free, no card) | **OpenStreetMap + Nominatim** (geocoding) + **Overpass API** (POI search) + **OSRM** (routing/distance) | Fully free, no API key, no card, no request cap beyond fair-use rate limiting (~1 req/sec on public Nominatim — self-host or cache if you scale). Best fit for a bootstrapped MVP. |
| Maps/Places (optional, better data, needs card) | Google Maps Platform (Places, Directions, Distance Matrix) | Google removed the old $200/month blanket credit in March 2025. Now each SKU gets its own free monthly quota instead (e.g., ~10,000 free Geocoding calls/month, ~5,000 free Places Text Search calls/month) — but you must add a billing card to even get an API key, even if you stay under the free quota. Use only if OSM data quality proves insufficient for a specific city. |
| Domestic Flights | **Amadeus Self-Service API (Test environment)** | Free, no cost, generous test-environment call limits. Real flight-like data (schedules/pricing) though the test environment is not always 100% live pricing — fine for a planner/estimator, not for actual booking. |
| Domestic Trains | **IRCTC API via RapidAPI** (unofficial, e.g. "IRCTC1") | Free tier exists but is very limited (as low as ~20 calls/month on some listings) — enough to demo, not enough for live traffic. Cache aggressively; treat train data as a "nice to have" layer that degrades gracefully if quota runs out. |
| Weather | **OpenWeatherMap** | Free tier: 1,000 calls/day, 60 calls/min, no card required. Good for backup-option logic (indoor vs outdoor). |
| Database | **Supabase (free tier)** or **Neon (free tier)** — both are hosted Postgres | Free tier gives you a real Postgres instance (500MB–1GB storage range) with no card required to start. Good enough for MVP user/trip data. |
| Cache | **Upstash Redis (free tier)** | No card required, serverless Redis, generous free request allowance — ideal for caching OSM/weather/train responses to stay under their rate limits. |
| Backend | FastAPI (Python) or Node/Express | Free to run locally / on free hosting tier (see below). |
| Frontend | Next.js + Tailwind | Free. |
| Hosting (frontend) | **Vercel free tier** | Generous free tier for personal/hobby projects. |
| Hosting (backend) | **Render free tier** or **Railway free trial credits** | Both have a genuinely free tier for small backend services (with cold-start sleep on Render's free instance — acceptable for MVP). |
| Auth (optional for MVP) | Supabase Auth (bundled free with the Supabase free tier) | Skip auth entirely for v1 if you want — let people generate and share a trip without an account. |

**Net effect:** You can build and run the entire MVP for **₹0**, using only providers that don't require a credit card (Gemini, OSM/Nominatim/Overpass/OSRM, OpenWeatherMap, Amadeus test env, Supabase/Neon, Upstash, Vercel, Render). Google Maps and a production-grade train API are the two places where free tiers are either card-gated or too thin for real usage — treat both as later upgrades, not MVP requirements.

---

## 2. Why This Simplifies the Architecture

- **No currency conversion needed** — everything is INR.
- **No visa/international-flight complexity.**
- **Two transport modes to plan around instead of one**: flights (fast, pricier) vs. trains (slower, cheaper, very common for Indian domestic travel, especially under ₹5,000–10,000 budgets). Your LLM prompt should pick the mode based on budget and distance, not just default to flights.
- **OSM/Overpass has solid India coverage** for major and mid-tier cities (POIs, restaurants, attractions) — good enough to skip Google Maps entirely for MVP.

---

## 3. Updated Core Workflow

1. **Input**: origin city, destination city (India only), dates, budget (₹), vibe.
2. **Distance check**: geocode origin/destination via Nominatim → straight-line distance.
   - If distance is short (< ~500 km) and budget is tight → bias toward **train** as the primary transport suggestion, flight as an alternate.
   - If distance is long or budget comfortably covers flights → bias toward **flight**, train as a backup/cheaper alternate.
3. **Transport search**:
   - Flights → Amadeus test-env search, filtered by budget ceiling.
   - Trains → IRCTC RapidAPI (cached hard — this is your scarcest resource), or degrade gracefully to "typical trains on this route" language if quota is exhausted, sourced from a small manually-seeded table of common routes as fallback.
4. **POI discovery**: Overpass API query around destination coordinates, filtered by vibe-mapped OSM tags (e.g., `tourism=attraction`, `amenity=restaurant`, `leisure=*`) within a reasonable radius.
5. **Weather check**: OpenWeatherMap forecast for the destination during travel dates → flags days likely to need indoor backups.
6. **Grounded LLM call (Gemini)**: feed real transport options, real POIs (with OSM coordinates), remaining per-day budget, and weather into the prompt. Ask for day-by-day sequencing, food spots, and backup options — same "propose, then validate" loop as before, just swap Google Distance Matrix for **OSRM** to check travel-time feasibility between consecutive stops.
7. **Validate & repair loop**: same logic as before — check budget, feasibility, opening-hour plausibility (OSM data on opening hours is less reliable than Google's, so treat this check as advisory rather than hard-blocking) — then return the structured itinerary.
8. **Render**: Leaflet.js (free, open-source) + OSM tile layer for the map view instead of Google Maps JS SDK — keeps the frontend free too, no Maps JavaScript API billing at all.

---

## 4. Revised MVP Roadmap

**Phase 1 (1–2 weeks) — Skeleton, no transport yet**
- Input form (origin, destination, dates, budget, vibe) — India-only city list/autocomplete via Nominatim.
- Overpass POI discovery for one vibe category.
- Gemini call to generate a rough day-by-day plan from POIs + budget.
- Render as a simple list (no map).

**Phase 2 (2 weeks) — Transport + grounding**
- Amadeus flight search integration.
- IRCTC train search integration (with aggressive caching + graceful fallback).
- OSRM-based feasibility validation + repair loop.
- Budget validation.

**Phase 3 (1–2 weeks) — Map + weather + polish**
- Leaflet + OSM map rendering with day routes.
- OpenWeatherMap-driven backup logic.
- Shareable trip link (no auth needed) via Supabase.

**Phase 4 — Later upgrades (only if free tiers become a bottleneck)**
- Swap OSM Places data for Google Places API on cities where OSM coverage is thin (requires adding a billing card, but usage will likely stay inside the free monthly SKU quota at MVP scale).
- Add hotel suggestions (no good free API for this in India yet — likely a v2/manual-curation problem).
- Move off Amadeus test-env to production for real live pricing once you're ready to handle real bookings.

---

## 5. Key Free-Tier Gotchas to Plan Around

- **Nominatim/Overpass public instances**: rate-limited (~1 req/sec) and ask that you set a descriptive User-Agent and cache results — don't hit them per page-load, cache POI results in Postgres/Redis for days.
- **Gemini free tier is per-project, not per-key**: generating more API keys won't raise your quota; if you need more headroom, use a second Google Cloud project for a second free pool rather than trying to fake concurrency with multiple keys.
- **IRCTC RapidAPI free tier is thin** (reports of as low as ~20 calls/month on some plans) — this is your tightest constraint. Cache train-route results by (origin, destination) pair for as long as reasonably accurate (train schedules don't change daily), and consider seeding a small static fallback table of common intercity routes so the app still shows something useful even at zero remaining quota.
- **Google Maps now requires a billing card just to get a key**, even for free-quota usage — this is a meaningful reason to default to OSM for as long as possible in this build.

---

*Want me to scaffold the actual project (Next.js + FastAPI, with Nominatim/Overpass/OSRM calls and a Gemini API call wired up end-to-end) as the next step?*
