"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import dynamic from "next/dynamic";
import ItineraryTimeline from "@/components/ItineraryTimeline";
import TransportCard from "@/components/TransportCard";
import TripCommitments from "@/components/TripCommitments";
import BudgetBreakdown from "@/components/BudgetBreakdown";
import ShareTrip from "@/components/ShareTrip";
import ConnectivityIndicator from "@/components/ConnectivityIndicator";
import OfflineEssentials from "@/components/OfflineEssentials";
import { DestinationInspiration, PrintTripButton } from "@/components/TripEnhancements";
import {
  api,
  Itinerary,
  formatINR,
  formatDate,
  setShareToken,
} from "@/lib/api";
import { loadOfflineTrip, saveOfflineTrip, type OfflineTripSnapshot } from "@/lib/offline";

const TripMap = dynamic(() => import("@/components/TripMap"), { ssr: false });

export default function TripDetailPage() {
  const params = useParams();
  const tripId = params.id as string;

  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offlineSnapshot, setOfflineSnapshot] = useState<OfflineTripSnapshot | null>(null);
  const [usingOfflineSnapshot, setUsingOfflineSnapshot] = useState(false);

  useEffect(() => {
    async function loadTrip() {
      const shareToken = new URLSearchParams(window.location.search).get("share");
      setShareToken(tripId, shareToken);
      setUsingOfflineSnapshot(false);
      try {
        const data = await api.getTrip(tripId);
        setItinerary(data);
        saveOfflineTrip(data, "single");
        setOfflineSnapshot(loadOfflineTrip(tripId));
      } catch {
        const cached = loadOfflineTrip(tripId);
        if (cached?.kind === "single") {
          setItinerary(cached.trip as Itinerary);
          setOfflineSnapshot(cached);
          setUsingOfflineSnapshot(true);
          setError(null);
        } else {
          setError("Trip not found or has expired.");
        }
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
          <Link
            href="/"
            className="inline-block px-6 py-3 bg-primary text-white rounded-xl font-medium
                       hover:bg-primary-light transition-colors"
          >
            ← Plan a New Trip
          </Link>
        </div>
      </main>
    );
  }

  if (!itinerary) return null;

  return (
    <main className="min-h-screen bg-background">
      <ConnectivityIndicator savedAt={offlineSnapshot?.savedAt} usingSnapshot={usingOfflineSnapshot} />
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
                <Link
                  href="/"
                  className="text-foreground-muted hover:text-foreground transition-colors text-sm flex items-center gap-1"
                >
                  ✈️ YatraAI
                </Link>
                <span className="text-foreground-muted">/</span>
                <span className="text-foreground-secondary text-sm">Shared Trip</span>
              </div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-foreground-muted">Trip summary</p>
              <h1 className="font-display text-3xl md:text-4xl font-bold">
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
                <span>👥 {itinerary.members || 2} members</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="px-4 py-2 glass glass-hover rounded-xl text-sm font-medium text-foreground"
              >
                ✨ Plan Your Own
              </Link>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Content */}
      <div className="px-4 py-8 max-w-6xl mx-auto">
        {offlineSnapshot && <OfflineEssentials snapshot={offlineSnapshot} />}
        {(itinerary.plan_options || []).length > 1 && (
          <section className="mb-8 rounded-xl border border-marigold/30 bg-marigold/5 p-4">
            <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-marigold">Selected itinerary shape</p>
            <h2 className="mt-1 text-xl font-bold text-foreground">{(itinerary.plan_options || []).find((option) => option.id === itinerary.selected_plan_id)?.title || "Selected plan"}</h2>
            <p className="mt-1 text-sm text-foreground-secondary">This shared view is read-only. Create your own trip to choose another plan.</p>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {(itinerary.plan_options || []).map((option) => <div key={option.id} className={`rounded-lg border p-3 ${option.id === itinerary.selected_plan_id ? "border-marigold bg-marigold/15" : "border-glass-border bg-background/20"}`}><div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold text-foreground">{option.title}</span>{option.id === itinerary.selected_plan_id && <span className="text-[10px] font-bold uppercase text-marigold">Selected</span>}</div><p className="mt-2 text-xs text-foreground-secondary">{option.description}</p><p className="mt-3 text-xs font-semibold text-foreground">{formatINR(option.budget.total_estimated)} estimated</p></div>)}
            </div>
          </section>
        )}
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

        <section className="mb-8"><TripCommitments itinerary={itinerary} /></section>

        <section className="mb-8 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
          <BudgetBreakdown budget={itinerary.budget} totalBudget={itinerary.budget.total_estimated + itinerary.budget.remaining} />
          <div className="rounded-xl border border-glass-border bg-glass-bg p-4 text-sm text-foreground-secondary"><h3 className="font-semibold text-foreground">What this total covers</h3><p className="mt-2">Selected outbound and return transport, meals, activities, local travel, transfers, and buffer.</p><p className="mt-3 text-xs text-foreground-muted">Excludes personal shopping, travel insurance, optional upgrades, and booking-site fees.</p></div>
        </section>

        <section className="mb-8"><ItineraryTimeline dayPlans={itinerary.day_plans} /></section>

        <section className="mb-8"><DestinationInspiration itinerary={itinerary} /></section>

        {itinerary.transport_options.some((option) => option.provider !== itinerary.selected_transport?.provider || option.code !== itinerary.selected_transport?.code) && (
          <section className="mb-8"><h2 className="mb-3 text-xl font-bold text-foreground">Alternative transport options</h2><p className="mb-3 text-sm text-foreground-muted">Shared itineraries are read-only. Create your own plan to choose another option.</p><div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">{itinerary.transport_options.filter((option) => option.provider !== itinerary.selected_transport?.provider || option.code !== itinerary.selected_transport?.code).map((option, index) => <TransportCard key={index} option={option} travelDate={itinerary.start_date} tripId={itinerary.id} />)}</div></section>
        )}

        <details className="glass print:hidden mb-8 overflow-hidden rounded-xl"><summary className="cursor-pointer px-4 py-4 text-sm font-semibold text-foreground">🗺️ View interactive map</summary><div className="border-t border-glass-border"><TripMap center={itinerary.destination.coordinates} dayPlans={itinerary.day_plans} routeSegments={itinerary.route_segments} destination={itinerary.destination.name} /></div></details>

        <section className="mb-8 print:hidden"><h2 className="mb-3 text-xl font-bold text-foreground">Secondary tools</h2><div className="glass flex flex-col gap-4 rounded-xl p-4 sm:flex-row sm:items-center sm:justify-between"><div><h3 className="font-semibold text-foreground">🔗 Share or print this trip</h3><p className="text-xs text-foreground-muted">Shared itineraries are read-only. Print a copy before you leave, then verify live details with providers.</p></div><div className="flex flex-wrap gap-2"><PrintTripButton itinerary={itinerary} /><ShareTrip tripId={itinerary.id} /></div></div></section>

        {/* CTA */}
        <div className="text-center mt-12 mb-8 print:hidden">
          <Link
            href="/"
            className="warm-button inline-block px-8 py-3 text-white rounded-xl font-semibold hover:brightness-110 transition-all duration-300"
          >
            ✨ Plan Your Own Trip
          </Link>
        </div>
      </div>
    </main>
  );
}
