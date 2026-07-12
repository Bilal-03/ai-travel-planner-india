"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import dynamic from "next/dynamic";
import ItineraryTimeline from "@/components/ItineraryTimeline";
import TransportCard from "@/components/TransportCard";
import BudgetBreakdown from "@/components/BudgetBreakdown";
import ShareTrip from "@/components/ShareTrip";
import {
  api,
  Itinerary,
  formatINR,
  formatDate,
  getVibeEmoji,
} from "@/lib/api";

const TripMap = dynamic(() => import("@/components/TripMap"), { ssr: false });

export default function TripDetailPage() {
  const params = useParams();
  const tripId = params.id as string;

  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTrip() {
      try {
        const data = await api.getTrip(tripId);
        setItinerary(data);
      } catch {
        setError("Trip not found or has expired.");
      } finally {
        setLoading(false);
      }
    }
    if (tripId) loadTrip();
  }, [tripId]);

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center gradient-hero">
        <div className="glass p-8 rounded-2xl text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="text-5xl mb-4 inline-block"
          >
            ✈️
          </motion.div>
          <p className="text-foreground-secondary">Loading trip...</p>
        </div>
      </main>
    );
  }

  if (error || !itinerary) {
    return (
      <main className="min-h-screen flex items-center justify-center gradient-hero">
        <div className="glass p-8 rounded-2xl text-center max-w-md">
          <div className="text-5xl mb-4">🔍</div>
          <h2 className="text-xl font-bold text-foreground mb-2">Trip Not Found</h2>
          <p className="text-foreground-muted mb-4">{error}</p>
          <a
            href="/"
            className="inline-block px-6 py-3 bg-primary text-white rounded-xl font-medium
                       hover:bg-primary-light transition-colors"
          >
            ← Plan a New Trip
          </a>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <div className="gradient-hero px-4 py-8">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
          >
            <div>
              <div className="flex items-center gap-2 mb-2">
                <a
                  href="/"
                  className="text-foreground-muted hover:text-foreground transition-colors text-sm flex items-center gap-1"
                >
                  ✈️ YatraAI
                </a>
                <span className="text-foreground-muted">/</span>
                <span className="text-foreground-secondary text-sm">Shared Trip</span>
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
                <span>{itinerary.vibes.map((v) => getVibeEmoji(v)).join(" ")}</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <ShareTrip tripId={itinerary.id} />
              <a
                href="/"
                className="px-4 py-2 glass glass-hover rounded-xl text-sm font-medium text-foreground"
              >
                ✨ Plan Your Own
              </a>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Content */}
      <div className="px-4 py-8 max-w-6xl mx-auto">
        {/* Generation Notes */}
        {itinerary.generation_notes.length > 0 && (
          <div className="glass p-4 rounded-xl mb-6">
            <h4 className="text-sm font-semibold text-foreground-secondary mb-2">💡 Travel Tips</h4>
            <ul className="text-sm text-foreground-muted space-y-1">
              {itinerary.generation_notes.map((note, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-accent mt-0.5">•</span>
                  {note}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <TripMap
              center={itinerary.destination.coordinates}
              dayPlans={itinerary.day_plans}
              routeSegments={itinerary.route_segments}
              destination={itinerary.destination.name}
            />
            <ItineraryTimeline dayPlans={itinerary.day_plans} />
          </div>

          <div className="space-y-6">
            {itinerary.transport_options.length > 0 && (
              <div>
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
              </div>
            )}

            <BudgetBreakdown
              budget={itinerary.budget}
              totalBudget={itinerary.budget.total_estimated + itinerary.budget.remaining}
            />
          </div>
        </div>

        {/* CTA */}
        <div className="text-center mt-12 mb-8">
          <a
            href="/"
            className="inline-block px-8 py-3 bg-gradient-to-r from-primary to-primary-light
                       text-white rounded-xl font-semibold
                       hover:shadow-[0_0_30px_rgba(99,102,241,0.3)] transition-all duration-300"
          >
            ✨ Plan Your Own Trip
          </a>
        </div>
      </div>
    </main>
  );
}
