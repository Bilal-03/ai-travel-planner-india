<div align="center">

# ✈️ YatraAI

### AI-Powered India Travel Planner

**Plan a domestic India trip with Gemini-assisted activities, transparent transport sources, deterministic budgeting, weather forecasts, and interactive maps.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20App-6366f1?style=for-the-badge&logo=vercel)](https://ai-travel-planner-india-seven.vercel.app)
[![Backend API](https://img.shields.io/badge/API%20Docs-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://yatraai-backend.onrender.com/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

---

## 🌟 Features

| Feature | Description |
|---|---|
| 🤖 **AI Itinerary Generation** | Google Gemini 2.5 Flash creates personalized day-by-day plans |
| ✈️🚂 **Flights & Trains** | Skyscanner results when configured; train schedules and fares retain separate source labels |
| 🗺️ **Interactive Maps** | Leaflet + OpenStreetMap with routes and POI markers |
| 🌤️ **Weather-Aware Planning** | OpenWeatherMap forecasts with indoor backup activities |
| 💰 **Budget Tracking** | Deterministic breakdown — outbound/return transport, food, activities, stay, local transport and buffer |
| 🔗 **Instant Sharing** | View-only links, WhatsApp sharing, and persistent saved itineraries |
| 🏙️ **Multi-city Routes** | Plan explicit destination stays, travel legs, return legs, and stay-scoped edits |
| ✨ **Plan Refinement** | The planning browser can update its saved itinerary with a follow-up request |
| 🧳 **Packing List** | Generates a weather- and vibe-aware checklist on demand |
| 🖨️ **Print / PDF** | Print any itinerary or save it as a PDF from the browser |
| 🏙️ **City Autocomplete** | Instant search across popular Indian cities and destinations, with an OSM fallback |
| 📱 **Fully Responsive** | Works beautifully on mobile, tablet, and desktop |
| 📴 **Offline PWA** | Keeps a recent itinerary summary, addresses, and emergency notes available offline |
| 👥 **Collaboration** | Create expiring viewer/editor links with immutable history and conflict checks |

---

## 🛠️ Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| [Next.js 16](https://nextjs.org/) | React framework with App Router |
| [TypeScript](https://www.typescriptlang.org/) | Type safety |
| [Tailwind CSS 4](https://tailwindcss.com/) | Utility-first styling |
| [Framer Motion](https://www.framer.com/motion/) | Animations |
| [Leaflet](https://leafletjs.com/) | Interactive maps |
| [QRCode.react](https://github.com/zpao/qrcode.react) | QR code generation |

### Backend
| Technology | Purpose |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | High-performance Python API |
| [Google Gemini AI](https://ai.google.dev/) | LLM itinerary generation |
| [Neon](https://neon.com/) | Serverless PostgreSQL database |
| [Upstash Redis](https://upstash.com/) | API response caching |
| [Skyscanner RapidAPI](https://rapidapi.com/) | Optional live flight search |
| [RailRadar](https://rapidapi.com/railradar/) | Train schedule data (fare and availability are not confirmed) |
| [OpenWeatherMap](https://openweathermap.org/) | Weather forecasts |
| [Nominatim / OSM](https://nominatim.org/) | One-off city geocoding fallback (free) |
| [OSRM](http://project-osrm.org/) | Route calculation (free) |

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- Node.js 18+
- Python 3.11+
- Git

### 1. Clone the repository
```bash
git clone https://github.com/Bilal-03/ai-travel-planner-india.git
cd ai-travel-planner-india
```

### 2. Set up environment variables
```bash
cp .env.example .env
```
Open `.env` and fill in your API keys (see [Environment Variables](#-environment-variables) below).

### 3. Start the Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Backend API will be at: `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

### 4. Start the Frontend
```bash
cd frontend
npm install
cp .env.example .env.local      # or just set NEXT_PUBLIC_API_URL
npm run dev
```
Frontend will be at: `http://localhost:3000`

---

## 🔑 Environment Variables

Copy the included root [`.env.example`](.env.example) to `.env` for the backend, and copy [`frontend/.env.example`](frontend/.env.example) to `frontend/.env.local` for the public frontend URL:

| Variable | Required | Description | Get it from |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | Google Gemini AI key | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `OPENWEATHERMAP_API_KEY` | ⚪ Optional | Weather forecasts | [OpenWeatherMap](https://openweathermap.org/api) |
| `RAILRADAR_API_KEY` | ⚪ Optional | Train search | [RapidAPI - RailRadar](https://rapidapi.com/railradar/) |
| `SKYSCANNER_RAPIDAPI_KEY` | ⚪ Optional | Live flight search | [RapidAPI](https://rapidapi.com/) |
| `UNSPLASH_ACCESS_KEY` | ⚪ Optional | Destination photos | [Unsplash Developers](https://unsplash.com/developers) |
| `DATABASE_URL` | ⚪ Local / ✅ production | Neon PostgreSQL pooled connection string | [Neon](https://neon.com/) |
| `UPSTASH_REDIS_REST_URL` | ⚪ Local / ✅ production | Redis cache, queue, and distributed rate limits | [Upstash](https://upstash.com/) |
| `UPSTASH_REDIS_REST_TOKEN` | ⚪ Local / ✅ production | Redis authentication token | Same as above |
| `REQUIRE_DURABLE_STORAGE` | ⚪ Optional | Set `true` in production to reject memory persistence fallback | — |
| `REQUIRE_REDIS` | ⚪ Optional | Set `true` in production for distributed rate limits and queue readiness | — |
| `FRONTEND_URL` | ✅ Yes | Frontend URL for CORS | Your Vercel URL in production |

> **Note:** The app works without optional keys — it degrades gracefully. Only `GEMINI_API_KEY` is required.

The app uses built-in provider defaults for Skyscanner, RailRadar, Overpass,
OSRM, and OpenWeather, with labelled fallbacks when optional keys are absent.
Phase 6 adds multi-city planning and PostgreSQL-backed durable itinerary/share
storage for production deployments; the app has no user accounts or login flow.

Phase 7 production deployments must apply the ordered SQL migrations under
[`backend/migrations/`](backend/migrations/), set `APP_ENV=production`, enable
`REQUIRE_DURABLE_STORAGE=true` and `REQUIRE_REDIS=true`, and verify `/health`
reports `ready: true` before accepting traffic. See the
[Phase 7 completion report](docs/phase-7-completion-report.md) for the complete
runbook and CI checks.

---

## ☁️ Deployment

### Frontend → Vercel
1. Go to [vercel.com](https://vercel.com) → **New Project**
2. Import this GitHub repository
3. Set **Root Directory** to `frontend`
4. Add environment variable: `NEXT_PUBLIC_API_URL` = your Render backend URL
5. Deploy ✅

### Backend → Render
1. Go to [render.com](https://render.com) → **New Web Service**
2. Connect this GitHub repository
3. Set **Root Directory** to `backend`
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add all environment variables from `.env.example`
7. Deploy ✅

---

## 📁 Project Structure

```
ai-travel-planner-india/
├── .env.example              # Template — copy to .env
├── .gitignore
├── README.md
│
├── backend/                  # FastAPI Python backend
│   ├── main.py               # App entry point
│   ├── requirements.txt
│   ├── Procfile              # Render start command
│   ├── render.yaml           # Render deployment config
│   └── app/
│       ├── api/              # Route handlers
│       │   ├── trips.py      # Trip generation & retrieval
│       │   ├── search.py     # City search
│       │   └── transport.py  # Flights & trains
│       ├── models/           # Pydantic data models
│       ├── services/         # Business logic
│       │   ├── gemini_planner.py # AI itinerary generation and validation
│       │   ├── transport.py  # Flight/train search
│       │   ├── weather.py    # Weather forecasts
│       │   ├── routing.py    # Full stop-to-stop route calculation
│       │   ├── poi_discovery.py # POI lookup
│       │   └── trip_storage.py # Shared-itinerary persistence
│       ├── cache/            # Redis/in-memory caching
│       └── config.py         # Settings & env vars
│
└── frontend/                 # Next.js TypeScript frontend
    ├── next.config.ts
    ├── vercel.json           # Vercel deployment config
    ├── package.json
    ├── playwright.config.ts  # Browser-test setup
    ├── e2e/
    │   └── trip-flow.spec.ts # Form → generation → shared-page test
    └── src/
        ├── app/
        │   ├── page.tsx      # Home page
        │   └── trip/         # Trip detail page
        ├── components/
        │   ├── TripForm.tsx         # Trip planning form
        │   ├── ItineraryTimeline.tsx # Day-by-day timeline
        │   ├── TripMap.tsx          # Interactive map
        │   ├── TransportCard.tsx    # Flight/train options
        │   ├── BudgetBreakdown.tsx  # Budget visualization
        │   ├── WeatherBadge.tsx     # Weather display
        │   ├── ShareTrip.tsx        # Share functionality
        │   ├── CityAutocomplete.tsx # City search input
        │   └── LoadingState.tsx     # Loading animation
        └── lib/
            └── api.ts        # TypeScript API client
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines
- Backend: Follow PEP 8, use type hints, add docstrings
- Frontend: Use TypeScript strictly, follow the existing component patterns
- Commits: Use [Conventional Commits](https://www.conventionalcommits.org/) format

### Tests

```bash
# Backend deterministic budget, transport, validation, route and safety tests
cd backend
pytest

# Frontend lint and browser flow (install browsers once with `npx playwright install`)
cd frontend
npm run lint
npm run test:e2e
```

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [Google Gemini AI](https://ai.google.dev/) for the LLM backbone
- [OpenStreetMap](https://www.openstreetmap.org/) & [Nominatim](https://nominatim.org/) for free geocoding
- [OSRM](http://project-osrm.org/) for free routing
- [Skyscanner](https://www.skyscanner.net/) for optional flight search
- [RailRadar](https://rapidapi.com/railradar/) for train schedules
- [OpenWeatherMap](https://openweathermap.org/) for weather data

---

<div align="center">

Built with 💜 in India · 100% Free-tier powered · No credit card needed

**[⭐ Star this repo](https://github.com/Bilal-03/ai-travel-planner-india) if you find it useful!**

</div>
