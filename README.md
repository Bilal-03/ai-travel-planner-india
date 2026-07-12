<div align="center">

# ✈️ YatraAI

### AI-Powered India Travel Planner

**Plan your perfect domestic India trip in seconds — powered by Gemini AI, real flight/train data, weather forecasts, and interactive maps.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20App-6366f1?style=for-the-badge&logo=vercel)](https://ai-travel-planner-india.vercel.app)
[![Backend API](https://img.shields.io/badge/API%20Docs-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://yatraai-backend.onrender.com/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

![YatraAI Screenshot](docs/screenshot.png)

</div>

---

## 🌟 Features

| Feature | Description |
|---|---|
| 🤖 **AI Itinerary Generation** | Google Gemini 2.5 Flash creates personalized day-by-day plans |
| ✈️🚂 **Flights & Trains** | Real-time comparison via Amadeus & RailRadar APIs |
| 🗺️ **Interactive Maps** | Leaflet + OpenStreetMap with routes and POI markers |
| 🌤️ **Weather-Aware Planning** | OpenWeatherMap forecasts with indoor backup activities |
| 💰 **Budget Tracking** | Visual breakdown — transport, food, activities, accommodation |
| 🔗 **Instant Sharing** | Share via link, WhatsApp, Twitter, or QR code — no signup |
| 🏙️ **City Autocomplete** | Smart search across all Indian cities using Nominatim |
| 📱 **Fully Responsive** | Works beautifully on mobile, tablet, and desktop |

---

## 🛠️ Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| [Next.js 16](https://nextjs.org/) | React framework with App Router |
| [TypeScript](https://www.typescriptlang.org/) | Type safety |
| [Tailwind CSS 4](https://tailwindcss.com/) | Utility-first styling |
| [Framer Motion](https://www.framer.com/motion/) | Animations |
| [React Leaflet](https://react-leaflet.js.org/) | Interactive maps |
| [QRCode.react](https://github.com/zpao/qrcode.react) | QR code generation |

### Backend
| Technology | Purpose |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | High-performance Python API |
| [Google Gemini AI](https://ai.google.dev/) | LLM itinerary generation |
| [Supabase](https://supabase.com/) | PostgreSQL database |
| [Upstash Redis](https://upstash.com/) | API response caching |
| [Amadeus API](https://developers.amadeus.com/) | Flight search |
| [RailRadar](https://rapidapi.com/railradar/) | Train search |
| [OpenWeatherMap](https://openweathermap.org/) | Weather forecasts |
| [Nominatim / OSM](https://nominatim.org/) | City geocoding (free) |
| [OSRM](http://project-osrm.org/) | Route calculation (free) |

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- Node.js 18+
- Python 3.11+
- Git

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/ai-travel-planner-india.git
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

Create a `.env` file at the root from `.env.example`:

| Variable | Required | Description | Get it from |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | Google Gemini AI key | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `OPENWEATHERMAP_API_KEY` | ⚪ Optional | Weather forecasts | [OpenWeatherMap](https://openweathermap.org/api) |
| `RAILRADAR_API_KEY` | ⚪ Optional | Train search | [RapidAPI - RailRadar](https://rapidapi.com/railradar/) |
| `AMADEUS_API_KEY` | ⚪ Optional | Flight search | [Amadeus Developers](https://developers.amadeus.com/) |
| `AMADEUS_API_SECRET` | ⚪ Optional | Flight search | Same as above |
| `SUPABASE_URL` | ⚪ Optional | Database (falls back to in-memory) | [Supabase](https://supabase.com/) |
| `SUPABASE_KEY` | ⚪ Optional | Database | Same as above |
| `UPSTASH_REDIS_REST_URL` | ⚪ Optional | Cache (falls back to in-memory) | [Upstash](https://upstash.com/) |
| `UPSTASH_REDIS_REST_TOKEN` | ⚪ Optional | Cache | Same as above |
| `FRONTEND_URL` | ✅ Yes | Frontend URL for CORS | Your Vercel URL in production |

> **Note:** The app works without optional keys — it degrades gracefully. Only `GEMINI_API_KEY` is required.

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
│       │   ├── gemini.py     # AI itinerary generation
│       │   ├── transport.py  # Flight/train search
│       │   ├── weather.py    # Weather forecasts
│       │   └── osm.py        # Maps & routing
│       ├── cache/            # Redis/in-memory caching
│       └── config.py         # Settings & env vars
│
└── frontend/                 # Next.js TypeScript frontend
    ├── next.config.ts
    ├── vercel.json           # Vercel deployment config
    ├── package.json
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

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [Google Gemini AI](https://ai.google.dev/) for the LLM backbone
- [OpenStreetMap](https://www.openstreetmap.org/) & [Nominatim](https://nominatim.org/) for free geocoding
- [OSRM](http://project-osrm.org/) for free routing
- [Amadeus](https://developers.amadeus.com/) for flight data
- [OpenWeatherMap](https://openweathermap.org/) for weather data

---

<div align="center">

Built with 💜 in India · 100% Free-tier powered · No credit card needed

**[⭐ Star this repo](https://github.com/YOUR_USERNAME/ai-travel-planner-india) if you find it useful!**

</div>
