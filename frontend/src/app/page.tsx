"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import dynamic from "next/dynamic";
import HomeHero from "@/components/HomeHero";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import TripForm from "@/components/TripForm";
import FeaturesRail from "@/components/FeaturesRail";
import DestinationPostcards from "@/components/DestinationPostcards";
import LoadingState from "@/components/LoadingState";
import ItineraryTimeline from "@/components/ItineraryTimeline";
import TransportCard from "@/components/TransportCard";
import BudgetBreakdown from "@/components/BudgetBreakdown";
import ShareTrip from "@/components/ShareTrip";
import TripEnhancements from "@/components/TripEnhancements";
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
      <Header
        onLogoClick={
          itinerary
            ? handleNewTrip
            : () => window.scrollTo({ top: 0, behavior: "smooth" })
        }
      />

      {/* ── Home: hero, ticket form, features, destinations ─────────── */}
      {!itinerary && (
        <>
          <HomeHero />

          <section id="plan" className="px-7 pt-[30px] pb-[90px]">
            {!isGenerating ? (
              <TripForm onSubmit={handleSubmit} isLoading={isGenerating} />
            ) : (
              <LoadingState />
            )}

            {error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 p-4 glass border-error/30 rounded-xl max-w-md mx-auto text-center"
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
          </section>

          <FeaturesRail />
          <DestinationPostcards />
        </>
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

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="mb-6"
          >
            <TripEnhancements itinerary={itinerary} onUpdate={setItinerary} />
          </motion.div>

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

      <Footer />
    </main>
  );
}
