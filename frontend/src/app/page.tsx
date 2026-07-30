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
        <section className="gradient-hero">
          <nav className="border-b border-glass-border bg-background/70 px-4 backdrop-blur"><div className="mx-auto flex max-w-6xl items-center justify-between py-4"><span className="font-display text-3xl text-foreground">YatraAI</span><span className="font-ticket text-[10px] tracking-[.14em] text-foreground-muted">INDIA TRAVEL PLANNER</span><a href="#plan" className="font-ticket border border-glass-border px-3 py-2 text-[10px] tracking-[.1em] text-accent">PLAN A TRIP</a></div></nav>
          <div className="mx-auto grid max-w-6xl gap-10 px-4 pb-16 pt-16 lg:grid-cols-[1.05fr_.95fr] lg:items-center">
            <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .55 }}>
              <p className="section-eyebrow">Your India, your way</p>
              <h1 className="font-display mt-4 text-6xl text-foreground sm:text-7xl md:text-8xl">WHERE ARE<br />WE <span className="text-accent">HEADING</span><br />TODAY?</h1>
              <p className="mt-6 max-w-lg text-base font-medium leading-7 text-foreground-secondary">A thoughtful AI trip planner for journeys worth taking slowly—built around your dates, budget, travel vibe, and the way India actually moves.</p>
              <div className="mt-8 flex flex-wrap gap-3"><a href="#plan" className="font-ticket bg-accent px-5 py-4 text-xs font-bold tracking-[.08em] text-[#24160a]">PLAN MY JOURNEY →</a><a href="#destinations" className="font-ticket border border-glass-border px-5 py-4 text-xs tracking-[.08em] text-foreground">EXPLORE DESTINATIONS</a></div>
              <p className="font-ticket mt-5 text-[10px] tracking-[.08em] text-foreground-muted">DOMESTIC INDIA ONLY · NO SIGNUP · BUILT FOR REAL JOURNEYS</p>
            </motion.div>
            <DepartureBoard />
          </div>

          <div id="plan" className="mx-auto max-w-6xl px-4 pb-20">
            <div className="ticket-stub p-6 md:p-8"><div className="mb-5 flex items-center justify-between"><div><p className="section-eyebrow">Issue your ticket</p><h2 className="font-display mt-1 text-4xl text-foreground">Plan the route</h2></div><span className="font-ticket text-xs text-foreground-muted">YATRA / 01</span></div>
            {!isGenerating ? <TripForm onSubmit={handleSubmit} isLoading={isGenerating} /> : <LoadingState />}</div>
          </div>

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
              className="rail-features mx-auto max-w-6xl px-4 pb-20"
            >
              <p className="section-eyebrow text-center">Everything you need, on one route</p><h2 className="font-display mb-10 mt-2 text-center text-5xl text-foreground">Travel, connected</h2>
              <div className="grid grid-cols-2 gap-5 md:grid-cols-3">
                {FEATURES.map((feature, idx) => (
                  <motion.div
                    key={feature.title}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 + idx * 0.1 }}
                    className="rail-stop px-3 text-center"
                  >
                    <div className="text-2xl mb-2">{feature.icon}</div><h3 className="font-ticket text-xs font-bold tracking-[.08em] text-foreground mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-xs leading-5 text-foreground-muted">
                      {feature.desc}
                    </p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          <div id="destinations"><DestinationPosters /></div>
          <div className="pb-10 text-center font-ticket text-[10px] tracking-[.08em] text-foreground-muted"><p>BUILT WITH GEMINI AI · OPENSTREETMAP · OPENWEATHERMAP</p></div>
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
