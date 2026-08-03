"use client";

import { useEffect, useRef, useState } from "react";
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
import { PackingAndPrint, RefineItineraryAction, StaySuggestions } from "@/components/TripEnhancements";
import {
  api,
  Itinerary,
  TripRequest,
  GenerationStatus,
  formatINR,
  formatDate,
  getVibeEmoji,
  ApiError,
} from "@/lib/api";

// Leaflet must be imported dynamically (no SSR)
const TripMap = dynamic(() => import("@/components/TripMap"), { ssr: false });

export default function Home() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [backendReady, setBackendReady] = useState(false);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastRequest, setLastRequest] = useState<TripRequest | null>(null);
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const stopProgressRef = useRef<(() => void) | null>(null);

  // Render's free instances can sleep after inactivity. Start the inexpensive
  // health request on arrival, while the visitor is completing the form.
  useEffect(() => {
    let isMounted = true;

    void api.warmUp().then((isReady) => {
      if (isMounted && isReady) setBackendReady(true);
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleSubmit = async (data: TripRequest) => {
    abortRef.current?.abort();
    stopProgressRef.current?.();
    const controller = new AbortController();
    const progressToken = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    abortRef.current = controller;
    stopProgressRef.current = api.subscribeTripProgress(progressToken, setGenerationStatus);
    setIsGenerating(true);
    setError(null);
    setItinerary(null);
    setLastRequest(data);
    setGenerationStatus({ step: "starting", message: "Sending your trip request…", progress: 5 });

    try {
      const result = await api.generateTrip(data, { signal: controller.signal, progressToken });
      if (abortRef.current !== controller) return;
      setItinerary(result);
    } catch (err) {
      if (abortRef.current !== controller) return;
      if (controller.signal.aborted) {
        setError("Generation cancelled. Your completed form is still available to edit or retry.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      if (abortRef.current === controller) {
        stopProgressRef.current?.();
        stopProgressRef.current = null;
        abortRef.current = null;
        setIsGenerating(false);
      }
    }
  };

  const cancelGeneration = () => {
    abortRef.current?.abort();
    stopProgressRef.current?.();
    stopProgressRef.current = null;
    abortRef.current = null;
    setIsGenerating(false);
    setGenerationStatus(null);
    setError("Generation cancelled. Your completed form is still available to edit or retry.");
  };

  const retryGeneration = () => {
    if (lastRequest) void handleSubmit(lastRequest);
  };

  const handleNewTrip = () => {
    setItinerary(null);
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleTransportSelect = async (option: Itinerary["transport_options"][number]) => {
    if (!itinerary) return;
    try {
      setItinerary(await api.selectTransport(itinerary.id, option));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn’t update transport. Please try again.");
    }
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
            <TripForm onSubmit={handleSubmit} isLoading={isGenerating} />
            {isGenerating && <LoadingState waitingForBackend={!backendReady} status={generationStatus} onCancel={cancelGeneration} onRetry={retryGeneration} />}

            {error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 p-4 glass border-error/30 rounded-xl max-w-md mx-auto text-center"
              >
                <p className="text-error font-medium">⚠️ {error}</p>
                <button
                  onClick={() => { setError(null); retryGeneration(); }}
                  className="mt-2 text-sm text-foreground-muted hover:text-foreground transition-colors"
                >
                  Retry request
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
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-foreground-muted">Trip summary</p>
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
          </motion.div>

          {/* Trip summary */}
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

          {/* Recommended outbound and return journey */}
          {itinerary.selected_transport && (
            <section className="mb-8">
              <h2 className="mb-3 text-xl font-bold text-foreground">🚀 Recommended journey</h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div><p className="mb-2 text-sm font-medium text-foreground-secondary">Outbound · {itinerary.origin.name} → {itinerary.destination.name}</p><TransportCard option={itinerary.selected_transport} travelDate={itinerary.start_date} isSelected /></div>
                <div><p className="mb-2 text-sm font-medium text-foreground-secondary">Return · {itinerary.destination.name} → {itinerary.origin.name}</p><TransportCard option={itinerary.selected_transport} travelDate={itinerary.end_date} isSelected /></div>
              </div>
            </section>
          )}

          {/* Total budget, with exactly what is covered */}
          <section className="mb-8 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
            <BudgetBreakdown budget={itinerary.budget} totalBudget={itinerary.budget.total_estimated + itinerary.budget.remaining} />
            <div className="rounded-xl border border-glass-border bg-glass-bg p-4 text-sm text-foreground-secondary">
              <h3 className="font-semibold text-foreground">What this total covers</h3>
              <p className="mt-2">Selected outbound and return transport, accommodation, meals, activities, local travel, transfers, and buffer.</p>
              <p className="mt-3 text-xs text-foreground-muted">Excludes personal shopping, travel insurance, optional upgrades, and booking-site fees.</p>
            </div>
          </section>

          {/* Day-by-day itinerary remains the primary result */}
          <section className="mb-8">
            <ItineraryTimeline dayPlans={itinerary.day_plans} action={<RefineItineraryAction itinerary={itinerary} onUpdate={setItinerary} />} />
          </section>

          {/* Alternate choices appear after the plan, not before it */}
          {itinerary.transport_options.some((option) => option.provider !== itinerary.selected_transport?.provider || option.code !== itinerary.selected_transport?.code) && (
            <section className="mb-8">
              <h2 className="mb-3 text-xl font-bold text-foreground">Alternative transport options</h2>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                {itinerary.transport_options.filter((option) => option.provider !== itinerary.selected_transport?.provider || option.code !== itinerary.selected_transport?.code).map((option, index) => <TransportCard key={index} option={option} travelDate={itinerary.start_date} onClick={() => void handleTransportSelect(option)} />)}
              </div>
            </section>
          )}

          <section className="mb-8"><StaySuggestions itinerary={itinerary} /></section>

          <details className="glass mb-8 overflow-hidden rounded-xl">
            <summary className="cursor-pointer px-4 py-4 text-sm font-semibold text-foreground">🗺️ View interactive map</summary>
            <div className="border-t border-glass-border"><TripMap center={itinerary.destination.coordinates} dayPlans={itinerary.day_plans} routeSegments={itinerary.route_segments} destination={itinerary.destination.name} /></div>
          </details>

          <section className="mb-8 print:hidden">
            <h2 className="mb-3 text-xl font-bold text-foreground">Secondary tools</h2>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2"><PackingAndPrint itinerary={itinerary} onUpdate={setItinerary} /><div className="glass flex items-center justify-between rounded-xl p-4"><div><h3 className="font-semibold text-foreground">🔗 Share this trip</h3><p className="text-xs text-foreground-muted">Send the live itinerary to your travel group.</p></div><ShareTrip tripId={itinerary.id} /></div></div>
          </section>

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
