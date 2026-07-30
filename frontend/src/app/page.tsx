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
import TripEnhancements from "@/components/TripEnhancements";
import DepartureBoard from "@/components/DepartureBoard";
import DestinationPosters from "@/components/DestinationPosters";
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
    icon: "🧭",
    title: "Plans grounded in real places",
    desc: "Gemini builds a day-by-day route around actual stays, food, sights, and the way cities connect.",
  },
  {
    icon: "✈️🚂",
    title: "Flights and trains, side by side",
    desc: "See the practical choice for your route before you commit — time, price, and trade-offs included.",
  },
  {
    icon: "⛅",
    title: "Built around the weather",
    desc: "Forecast-aware suggestions with indoor backups, so one rainy afternoon does not derail a whole day.",
  },
  {
    icon: "💰",
    title: "A budget that holds",
    desc: "Transport, stays, meals, and activities in one honest number — not a vague “starting from” price.",
  },
  {
    icon: "🗺️",
    title: "Every stop, on the map",
    desc: "See how your days fit together geographically before you are standing in the wrong part of town.",
  },
  {
    icon: "🔗",
    title: "One link, no sign-up",
    desc: "Share a finished itinerary with the people you are travelling with. They can open it anywhere.",
  },
];

export default function Home() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [suggestedDestination, setSuggestedDestination] = useState("");

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

  const chooseDestination = (destination: string) => {
    setSuggestedDestination(destination);
    window.setTimeout(() => document.getElementById("plan")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
  };

  return (
    <main className="min-h-screen">
      {/* ── Hero Section ─────────────────────────────────────────── */}
      {!itinerary && (
        <section className="reference-home">
          <nav className="reference-nav"><div className="reference-wrap reference-nav-inner"><div className="reference-brand"><span>Yatra<span>AI</span></span><small>Ghoomte raho</small></div><a href="#plan" className="reference-nav-cta">Plan a trip <span>→</span></a></div></nav>
          <div className="reference-wrap reference-hero-grid">
            <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .55 }}>
              <p className="reference-eyebrow">India, end to end</p>
              <h1 className="reference-hero-title">Namaste.<br />Where are we<br /><span>heading today?</span></h1>
              <p className="reference-hero-copy">Give YatraAI your cities and dates. It plans the routes, the stays, the food, and a budget that actually adds up — grounded in real places, not a generic listicle.</p>
              <div className="reference-hero-actions"><a href="#plan" className="reference-primary-cta">Plan my journey <span>→</span></a><a href="#destinations" className="reference-secondary-cta">Explore destinations</a></div>
              <p className="reference-hero-note">No sign-up · Free to plan · Built for domestic India travel</p>
            </motion.div>
            <DepartureBoard />
          </div>

          <div id="plan" className="reference-ticket-section"><div className="reference-wrap">
            {!isGenerating ? <TripForm key={suggestedDestination} onSubmit={handleSubmit} isLoading={isGenerating} initialDestination={suggestedDestination} /> : <LoadingState />}
          </div></div>

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
              className="reference-features"
            >
              <div className="reference-wrap"><div className="reference-feature-heading"><p className="reference-eyebrow">How it helps</p><h2>Everything a trip needs,<br />in one line</h2><p>Not another list of places. A trip that makes sense from the moment you leave home to the moment you return.</p></div>
              <div className="reference-rail">
                {FEATURES.map((feature, idx) => (
                  <motion.div
                    key={feature.title}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 + idx * 0.1 }}
                    className="reference-rail-stop"
                  >
                    <div className="reference-stop-dot" /><div className="reference-stop-icon">{feature.icon}</div><h3>{feature.title}</h3><p>{feature.desc}</p>
                  </motion.div>
                ))}
              </div></div>
            </motion.div>
          )}

          <DestinationPosters onSelect={chooseDestination} />
          <footer className="reference-footer"><div className="reference-wrap"><div className="reference-brand"><span>Yatra<span>AI</span></span><small>Ghoomte raho</small></div><nav className="reference-footer-links"><a href="#plan">Plan a trip</a><a href="#destinations">Destinations</a><a href="https://github.com/Bilal-03/ai-travel-planner-india" target="_blank" rel="noreferrer">GitHub</a></nav><p>Built for the next Indian trip · 100% free-tier</p></div></footer>
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
                <span className="gradient-text font-display">
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

          <div className="mb-6">
            <TripEnhancements itinerary={itinerary} onUpdate={setItinerary} />
          </div>

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
                  <h3 className="text-lg font-bold font-display text-foreground mb-3 flex items-center gap-2">
                    🚀 Transport Options
                  </h3>
                  <div className="space-y-3">
                    {itinerary.transport_options.map((opt, idx) => (
                      <TransportCard
                        key={idx}
                        option={opt}
                        travelDate={itinerary.start_date}
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
              className="warm-button px-8 py-3 text-white
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
