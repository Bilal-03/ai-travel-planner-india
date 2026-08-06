"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import HomeHero from "@/components/HomeHero";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import QuickPlanner from "@/components/QuickPlanner";
import FeaturesRail from "@/components/FeaturesRail";
import DestinationPostcards from "@/components/DestinationPostcards";
import SocialProofStrip from "@/components/SocialProofStrip";
import SampleItineraries from "@/components/SampleItineraries";
import FinalCTA from "@/components/FinalCTA";
import LoadingState from "@/components/LoadingState";
import TripWorkspace from "@/components/TripWorkspace";
import {
  api,
  Itinerary,
  TripRequest,
  GenerationStatus,
  ResearchEvent,
  TripJob,
  ApiError,
} from "@/lib/api";
import { track } from "@/lib/analytics";
import { saveOfflineTrip } from "@/lib/offline";

const ACTIVE_JOB_STORAGE_KEY = "yatraai:active-trip-job";

interface PersistedTripJob {
  jobId: string | null;
  idempotencyKey: string;
  lastEventId: number;
  request: TripRequest;
}

function randomId(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function readPersistedJob(): PersistedTripJob | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(ACTIVE_JOB_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PersistedTripJob;
  } catch {
    window.localStorage.removeItem(ACTIVE_JOB_STORAGE_KEY);
    return null;
  }
}

function writePersistedJob(job: PersistedTripJob): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(ACTIVE_JOB_STORAGE_KEY, JSON.stringify(job));
  }
}

function clearPersistedJob(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(ACTIVE_JOB_STORAGE_KEY);
  }
}

function statusFromJob(job: TripJob): GenerationStatus {
  return {
    step: job.step,
    message: job.message,
    progress: job.progress,
    status: job.status,
    job_id: job.id,
    error: job.error,
  };
}

export default function Home() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [backendReady, setBackendReady] = useState(false);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastRequest, setLastRequest] = useState<TripRequest | null>(null);
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus | null>(null);
  const [researchEvents, setResearchEvents] = useState<ResearchEvent[]>([]);
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);
  const requestAbortRef = useRef<AbortController | null>(null);
  const stopJobEventsRef = useRef<(() => void) | null>(null);
  const activeJobIdRef = useRef<string | null>(null);
  const resumeStartedRef = useRef(false);
  const generationStartedAtRef = useRef<number | null>(null);
  const clarificationRef = useRef<HTMLDivElement>(null);

  const stopJobEvents = () => {
    stopJobEventsRef.current?.();
    stopJobEventsRef.current = null;
  };

  const addResearchEvent = useCallback((event?: ResearchEvent | null) => {
    if (!event) return;
    setResearchEvents((current) => current.some((item) => item.id === event.id)
      ? current
      : [...current, event].slice(-16));
  }, []);

  const finishFailedJob = useCallback((jobId: string, message: string) => {
    if (activeJobIdRef.current !== jobId) return;
    stopJobEvents();
    activeJobIdRef.current = null;
    clearPersistedJob();
    setIsGenerating(false);
    setError(message);
    track("generation_failed", { metadata: { status: "failed", duration_ms: generationStartedAtRef.current ? Date.now() - generationStartedAtRef.current : undefined } });
    generationStartedAtRef.current = null;
  }, []);

  const resolveCompletedJob = useCallback(async (jobId: string) => {
    if (activeJobIdRef.current !== jobId) return;
    try {
      const result = await api.getTripJobResult(jobId);
      if (activeJobIdRef.current !== jobId) return;
      stopJobEvents();
      activeJobIdRef.current = null;
      clearPersistedJob();
      setItinerary(result);
      setResearchEvents(result.research_events || []);
      saveOfflineTrip(result, "single");
      setError(null);
      setIsGenerating(false);
      const duration = generationStartedAtRef.current ? Date.now() - generationStartedAtRef.current : undefined;
      track("generation_completed", { tripId: result.id, kind: "single", metadata: { duration_ms: duration } });
      track("planner_completed", { tripId: result.id, kind: "single", metadata: { duration_ms: duration, days: result.total_days } });
      generationStartedAtRef.current = null;
    } catch (err) {
      if (activeJobIdRef.current !== jobId) return;
      finishFailedJob(jobId, err instanceof ApiError ? err.message : "The saved itinerary could not be loaded.");
    }
  }, [finishFailedJob]);

  const applyJobSnapshot = useCallback((job: TripJob) => {
    setGenerationStatus(statusFromJob(job));
    if (job.status === "completed") {
      void resolveCompletedJob(job.id);
      return;
    }
    if (job.status === "failed") {
      finishFailedJob(job.id, job.error || job.message || "The planner could not complete this request.");
      return;
    }
    if (job.status === "cancelled") {
      finishFailedJob(job.id, "Generation cancelled. Your completed form is still available to edit or retry.");
      return;
    }

    activeJobIdRef.current = job.id;
    stopJobEvents();
    stopJobEventsRef.current = api.subscribeTripJobEvents(
      job.id,
      (event) => {
        if (activeJobIdRef.current !== event.job_id) return;
        const stored = readPersistedJob();
        if (stored && stored.jobId === event.job_id) {
          writePersistedJob({ ...stored, lastEventId: event.id });
        }
        addResearchEvent(event.research_event);
        setGenerationStatus(event);
        if (event.status === "completed") {
          void resolveCompletedJob(event.job_id);
        } else if (event.status === "failed") {
          finishFailedJob(event.job_id, event.error || event.message);
        } else if (event.status === "cancelled") {
          finishFailedJob(event.job_id, "Generation cancelled. Your completed form is still available to edit or retry.");
        }
      },
      readPersistedJob()?.lastEventId || 0,
    );
  }, [addResearchEvent, finishFailedJob, resolveCompletedJob]);

  const resumePersistedJob = useCallback(async (persisted: PersistedTripJob) => {
    setLastRequest(persisted.request);
    setResearchEvents([]);
    setIsGenerating(true);
    setError(null);
    setGenerationStatus({ step: "accepted", message: "Resuming your trip plan…", progress: 4, status: "accepted" });

    try {
      const job = persisted.jobId
        ? await api.getTripJob(persisted.jobId)
        : await api.createTripJob(persisted.request, persisted.idempotencyKey);
      activeJobIdRef.current = job.id;
      writePersistedJob({ ...persisted, jobId: job.id });
      applyJobSnapshot(job);
    } catch (err) {
      activeJobIdRef.current = null;
      clearPersistedJob();
      setIsGenerating(false);
      setError(err instanceof ApiError ? err.message : "The saved trip job could not be resumed.");
    }
  }, [applyJobSnapshot]);

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

  // A refresh or route navigation must reconnect to the accepted job instead
  // of starting a second generation request.
  useEffect(() => {
    if (resumeStartedRef.current) return;
    resumeStartedRef.current = true;
    const persisted = readPersistedJob();
    if (persisted) window.setTimeout(() => void resumePersistedJob(persisted), 0);
  }, [resumePersistedJob]);

  const handleSubmit = async (data: TripRequest, existingIdempotencyKey?: string) => {
    requestAbortRef.current?.abort();
    stopJobEvents();
    activeJobIdRef.current = null;
    const controller = new AbortController();
    const idempotencyKey = existingIdempotencyKey || randomId();
    generationStartedAtRef.current = Date.now();
    track("planner_started", { kind: "single" });
    track("generation_started", { kind: "single" });
    requestAbortRef.current = controller;
    writePersistedJob({ jobId: null, idempotencyKey, lastEventId: 0, request: data });
    setIsGenerating(true);
    setError(null);
    setItinerary(null);
    setResearchEvents([]);
    setLastRequest(data);
    setGenerationStatus({ step: "accepted", message: "Sending your trip request…", progress: 2, status: "accepted" });

    try {
      const job = await api.createTripJob(data, idempotencyKey, controller.signal);
      if (requestAbortRef.current !== controller) return;
      activeJobIdRef.current = job.id;
      writePersistedJob({ jobId: job.id, idempotencyKey, lastEventId: 0, request: data });
      applyJobSnapshot(job);
    } catch (err) {
      if (requestAbortRef.current !== controller) return;
      if (controller.signal.aborted) {
        setError("Generation cancelled. Your completed form is still available to edit or retry.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      if (requestAbortRef.current === controller) {
        requestAbortRef.current = null;
        if (!activeJobIdRef.current) setIsGenerating(false);
      }
    }
  };

  const cancelGeneration = () => {
    requestAbortRef.current?.abort();
    const jobId = activeJobIdRef.current;
    if (!jobId) {
      stopJobEvents();
      clearPersistedJob();
      setIsGenerating(false);
      setGenerationStatus(null);
      setPendingPrompt(null);
      setError("Generation cancelled. Your completed form is still available to edit or retry.");
      return;
    }
    void api.cancelTripJob(jobId).then((job) => {
      if (activeJobIdRef.current !== jobId) return;
      setGenerationStatus(statusFromJob(job));
      stopJobEvents();
      activeJobIdRef.current = null;
      clearPersistedJob();
      setIsGenerating(false);
      setPendingPrompt(null);
      setError("Generation cancelled. Your completed form is still available to edit or retry.");
    }).catch((err) => {
      if (activeJobIdRef.current === jobId) {
        setError(err instanceof ApiError ? err.message : "The planner could not be cancelled yet.");
      }
    });
  };

  const retryGeneration = () => {
    if (lastRequest) {
      const persisted = readPersistedJob();
      const samePendingRequest = persisted && !persisted.jobId;
      void handleSubmit(lastRequest, samePendingRequest ? persisted.idempotencyKey : undefined);
    }
  };

  const handleNewTrip = () => {
    requestAbortRef.current?.abort();
    stopJobEvents();
    activeJobIdRef.current = null;
    clearPersistedJob();
    setItinerary(null);
    setResearchEvents([]);
    setError(null);
    setPendingPrompt(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleTransportSelect = async (option: Itinerary["transport_options"][number]) => {
    if (!itinerary) return;
    try {
      setItinerary(await api.selectTransport(itinerary.id, option));
      track("transport_selected", { tripId: itinerary.id, kind: "single", metadata: { provider: option.provider } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't update transport. Please try again.");
    }
  };

  // When user submits from hero search bar, show the clarification flow
  const handleHeroSearch = (prompt: string) => {
    setPendingPrompt(prompt);
    // Scroll to clarification section
    setTimeout(() => {
      clarificationRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 100);
  };

  return (
    <main className="min-h-screen">
      {!itinerary && <Header onLogoClick={() => { handleNewTrip(); }} />}

      {/* ── Home: hero, clarification, features, destinations ─────── */}
      {!itinerary && (
        <>
          <HomeHero onSearch={handleHeroSearch} isLoading={isGenerating} />

          <SocialProofStrip />

          {/* Clarification flow — appears when user submits a prompt */}
          {pendingPrompt && !isGenerating && (
            <div ref={clarificationRef} style={{ padding: "1rem 1.75rem" }}>
              <QuickPlanner
                prompt={pendingPrompt}
                onGenerate={handleSubmit}
                isLoading={isGenerating}
              />
            </div>
          )}

          {/* Loading state */}
          {isGenerating && (
            <div style={{ padding: "1rem 1.75rem" }}>
              <LoadingState
                waitingForBackend={!backendReady}
                status={generationStatus}
                researchEvents={researchEvents}
                onCancel={cancelGeneration}
                onRetry={retryGeneration}
              />
            </div>
          )}

          {/* Error state */}
          {error && !isGenerating && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                maxWidth: 520,
                margin: "1rem auto",
                padding: "1.25rem",
                background: "rgba(239, 68, 68, 0.05)",
                border: "1px solid rgba(239, 68, 68, 0.15)",
                borderRadius: "var(--radius-md)",
                textAlign: "center",
              }}
            >
              <p style={{ color: "var(--error)", fontWeight: 600, fontSize: "0.9rem" }}>⚠️ {error}</p>
              <button
                onClick={() => { setError(null); retryGeneration(); }}
                style={{
                  marginTop: "0.5rem",
                  fontSize: "0.82rem",
                  color: "var(--foreground-muted)",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  textDecoration: "underline",
                }}
              >
                Retry request
              </button>
            </motion.div>
          )}

          <FeaturesRail />
          <DestinationPostcards />
          <SampleItineraries />
          <FinalCTA onSearch={handleHeroSearch} isLoading={isGenerating} />
        </>
      )}

      {/* ── Itinerary Result ─────────────────────────────────────── */}
      {itinerary && (
        <TripWorkspace itinerary={itinerary} onUpdate={(updated) => { setItinerary(updated); saveOfflineTrip(updated, "single"); }} onNewTrip={handleNewTrip} onTransportSelect={handleTransportSelect} />
      )}

      <Footer />
    </main>
  );
}
