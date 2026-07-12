"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import dynamic from "next/dynamic";
import TripForm from "@/components/TripForm";
import LoadingState from "@/components/LoadingState";
import ItineraryTimeline from "@/components/ItineraryTimeline";
import TransportCard from "@/components/TransportCard";
import BudgetBreakdown from "@/components/BudgetBreakdown";
import ShareTrip from "@/components/ShareTrip";
import {
  api,
  Itinerary,
  TripRequest,
  formatINR,
  formatDate,
  getVibeEmoji,
  ApiError,
} from "@/lib/api";

// Leaflet must be imported dynamically (no SSR)
const TripMap = dynamic(() => import("@/components/TripMap"), { ssr: false });

const FEATURES = [
  {
    icon: "🤖",
    title: "AI-Powered",
    desc: "Gemini AI creates personalized day-by-day plans grounded in real data",
  },
  {
    icon: "✈️🚂",
    title: "Flights & Trains",
    desc: "Compare flights and trains with smart recommendations based on budget",
  },
  {
    icon: "🗺️",
    title: "Interactive Maps",
    desc: "Visualize your trip on beautiful maps with routes and POI markers",
  },
  {
    icon: "🌤️",
    title: "Weather-Aware",
    desc: "Plans adapt to weather forecasts with indoor backup activities",
  },
  {
    icon: "💰",
    title: "Budget Tracking",
    desc: "Visual budget breakdown ensures you stay within your spending limits",
  },
  {
    icon: "🔗",
    title: "Share Instantly",
    desc: "Share your trip via link, WhatsApp, Twitter, or QR code — no signup",
  },
];

export default function Home() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: TripRequest) => {
    setIsGenerating(true);
    setError(null);
    setItinerary(null);

    try {
      const result = await api.generateTrip(data);
      setItinerary(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleNewTrip = () => {
    setItinerary(null);
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <main className="min-h-screen">
      {/* ── Hero Section ─────────────────────────────────────────── */}
      {!itinerary && (
        <section className="gradient-hero min-h-screen flex flex-col items-center justify-center px-4 py-20">
          {/* Brand */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-10"
          >
            <div className="flex items-center justify-center gap-3 mb-4">
              <motion.span
                className="text-5xl"
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              >
                ✈️
              </motion.span>
              <h1 className="text-5xl md:text-7xl font-bold font-[family-name:var(--font-outfit)]">
                <span className="gradient-text">YatraAI</span>
              </h1>
            </div>
            <p className="text-xl md:text-2xl text-foreground-secondary max-w-xl mx-auto text-balance">
              Plan your perfect India trip with AI — personalized itineraries in seconds
            </p>
            <p className="text-sm text-foreground-muted mt-3">
              🇮🇳 Domestic India Only • 100% Free • No Signup Required
            </p>
          </motion.div>

          {/* Trip Form */}
          {!isGenerating ? (
            <TripForm onSubmit={handleSubmit} isLoading={isGenerating} />
          ) : (
            <LoadingState />
          )}

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 p-4 glass border-error/30 rounded-xl max-w-md text-center"
            >
              <p className="text-error font-medium">⚠️ {error}</p>
              <button
                onClick={() => { setError(null); setIsGenerating(false); }}
                className="mt-2 text-sm text-foreground-muted hover:text-foreground transition-colors"
              >
                Try again
              </button>
            </motion.div>
          )}

          {/* Features Grid */}
          {!isGenerating && !error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="mt-20 max-w-5xl mx-auto"
            >
              <h2 className="text-center text-2xl font-bold font-[family-name:var(--font-outfit)] text-foreground mb-8">
                Why YatraAI?
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {FEATURES.map((feature, idx) => (
                  <motion.div
                    key={feature.title}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 + idx * 0.1 }}
                    className="glass glass-hover p-5 rounded-xl"
                  >
                    <div className="text-3xl mb-3">{feature.icon}</div>
                    <h3 className="font-semibold text-foreground mb-1">
                      {feature.title}
                    </h3>
                    <p className="text-sm text-foreground-muted">
                      {feature.desc}
                    </p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Footer */}
          <div className="mt-16 text-center text-xs text-foreground-muted">
            <p>
              Built with 💜 using Gemini AI • OpenStreetMap • Amadeus • OpenWeatherMap
            </p>
            <p className="mt-1">Entirely free-tier powered — no credit card needed</p>
          </div>
        </section>
      )}

      {/* ── Itinerary Result ─────────────────────────────────────── */}
      {itinerary && (
        <section className="px-4 py-8 max-w-6xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8"
          >
            <div>
              <div className="flex items-center gap-2 mb-1">
                <button
                  onClick={handleNewTrip}
                  className="text-foreground-muted hover:text-foreground transition-colors text-sm"
                >
                  ← New Trip
                </button>
              </div>
              <h1 className="text-3xl md:text-4xl font-bold font-[family-name:var(--font-outfit)]">
                <span className="gradient-text">
                  {itinerary.origin.name} → {itinerary.destination.name}
                </span>
              </h1>
              <div className="flex flex-wrap items-center gap-3 mt-2 text-foreground-secondary text-sm">
                <span>📅 {formatDate(itinerary.start_date)} – {formatDate(itinerary.end_date)}</span>
                <span>•</span>
                <span>🗓️ {itinerary.total_days} days</span>
                <span>•</span>
                <span>💰 {formatINR(itinerary.budget.total_estimated)}</span>
                <span>•</span>
                <span>
                  {itinerary.vibes.map((v) => getVibeEmoji(v)).join(" ")}
                </span>
              </div>
            </div>
            <ShareTrip tripId={itinerary.id} />
          </motion.div>

          {/* Generation Notes */}
          {itinerary.generation_notes.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="glass p-4 rounded-xl mb-6"
            >
              <h4 className="text-sm font-semibold text-foreground-secondary mb-2">
                💡 Travel Tips
              </h4>
              <ul className="text-sm text-foreground-muted space-y-1">
                {itinerary.generation_notes.map((note, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-accent mt-0.5">•</span>
                    {note}
                  </li>
                ))}
              </ul>
            </motion.div>
          )}

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Timeline (2 cols) */}
            <div className="lg:col-span-2 space-y-6">
              {/* Map */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <TripMap
                  center={itinerary.destination.coordinates}
                  dayPlans={itinerary.day_plans}
                  routeSegments={itinerary.route_segments}
                  destination={itinerary.destination.name}
                />
              </motion.div>

              {/* Timeline */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <ItineraryTimeline dayPlans={itinerary.day_plans} />
              </motion.div>
            </div>

            {/* Right: Sidebar (1 col) */}
            <div className="space-y-6">
              {/* Transport Options */}
              {itinerary.transport_options.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <h3 className="text-lg font-bold font-[family-name:var(--font-outfit)] text-foreground mb-3 flex items-center gap-2">
                    🚀 Transport Options
                  </h3>
                  <div className="space-y-3">
                    {itinerary.transport_options.map((opt, idx) => (
                      <TransportCard
                        key={idx}
                        option={opt}
                        isSelected={
                          itinerary.selected_transport?.code === opt.code &&
                          itinerary.selected_transport?.provider === opt.provider
                        }
                      />
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Budget Breakdown */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <BudgetBreakdown
                  budget={itinerary.budget}
                  totalBudget={
                    itinerary.budget.total_estimated + itinerary.budget.remaining
                  }
                />
              </motion.div>
            </div>
          </div>

          {/* New Trip CTA */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="text-center mt-12 mb-8"
          >
            <button
              onClick={handleNewTrip}
              className="px-8 py-3 bg-gradient-to-r from-primary to-primary-light text-white
                         rounded-xl font-semibold hover:shadow-[0_0_30px_rgba(99,102,241,0.3)]
                         transition-all duration-300"
            >
              ✨ Plan Another Trip
            </button>
          </motion.div>
        </section>
      )}
    </main>
  );
}
