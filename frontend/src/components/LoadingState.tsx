"use client";

import { motion } from "framer-motion";
import { GenerationStatus, ResearchEvent } from "@/lib/api";

interface LoadingStateProps {
  waitingForBackend?: boolean;
  status?: GenerationStatus | null;
  researchEvents?: ResearchEvent[];
  onCancel: () => void;
  onRetry: () => void;
}

const STEP_ICONS: Record<string, string> = {
  starting: "🚀",
  accepted: "📨",
  retrieving_data: "📦",
  resolving_locations: "🗺️",
  fetching_transport: "🚂",
  fetching_places: "📍",
  fetching_weather: "🌤️",
  optimising: "🧭",
  generating_narrative: "🤖",
  geocoding: "🗺️",
  trip_context: "📍",
  planning: "🤖",
  validating: "✅",
  routing: "🧭",
  cached: "⚡",
  ready: "✨",
};

export default function LoadingState({ waitingForBackend = false, status, researchEvents = [], onCancel, onRetry }: LoadingStateProps) {
  const title = waitingForBackend
    ? "Waking up the planner…"
    : status?.message || "Starting your trip plan…";
  const detail = waitingForBackend
    ? "The server is starting. Your completed form is safely kept here."
    : "Usually 30–75 seconds on the first plan. We'll show real planner updates as they happen.";
  const progress = waitingForBackend ? Math.max(status?.progress || 0, 4) : status?.progress || 8;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        maxWidth: 520,
        margin: "1.5rem auto",
        padding: "2rem",
        background: "var(--surface)",
        border: "1px solid var(--glass-border)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-md)",
        textAlign: "center",
      }}
    >
      <motion.div
        style={{ marginBottom: "1rem", fontSize: "3rem" }}
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        {waitingForBackend ? "⏳" : STEP_ICONS[status?.step || "starting"] || "🧳"}
      </motion.div>

      <h3 style={{ fontFamily: "var(--font-playfair, 'Playfair Display', Georgia, serif)", fontSize: "1.25rem", fontWeight: 700, color: "var(--foreground)" }}>
        {title}
      </h3>
      <p style={{ marginTop: "0.35rem", fontSize: "0.85rem", color: "var(--foreground-muted)" }}>{detail}</p>

      {/* Progress bar */}
      <div style={{ marginTop: "1.5rem", height: 6, width: "100%", overflow: "hidden", borderRadius: 3, background: "var(--background-secondary)" }}>
        <motion.div
          style={{ height: "100%", borderRadius: 3, background: "linear-gradient(90deg, var(--rust), var(--marigold))" }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(progress, 98)}%` }}
          transition={{ duration: 0.45, ease: "easeOut" }}
        />
      </div>

      {/* Research trail */}
      {researchEvents.length > 0 && (
        <div
          style={{
            marginTop: "1.25rem",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--glass-border)",
            background: "var(--background)",
            padding: "0.85rem",
            textAlign: "left",
          }}
          aria-live="polite"
        >
          <p style={{ fontSize: "0.7rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--foreground-muted)" }}>
            Research trail
          </p>
          <ul style={{ marginTop: "0.5rem", listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: "0.4rem" }}>
            {researchEvents.slice(-4).map((event) => (
              <li key={event.id} style={{ display: "flex", alignItems: "flex-start", gap: "0.4rem", fontSize: "0.8rem", color: "var(--foreground-secondary)" }}>
                <span style={{ color: "var(--success)", marginTop: "0.1rem" }}>✓</span>
                <span>{event.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action buttons */}
      <div style={{ marginTop: "1.25rem", display: "flex", justifyContent: "center", gap: "0.75rem" }}>
        <button
          onClick={onCancel}
          style={{
            padding: "0.55rem 1rem",
            borderRadius: 8,
            border: "1px solid var(--glass-border)",
            background: "transparent",
            fontSize: "0.85rem",
            color: "var(--foreground-secondary)",
            cursor: "pointer",
          }}
        >
          Cancel
        </button>
        <button
          onClick={onRetry}
          style={{
            padding: "0.55rem 1rem",
            borderRadius: 8,
            border: "1px solid rgba(232,144,31,0.4)",
            background: "transparent",
            fontSize: "0.85rem",
            fontWeight: 600,
            color: "var(--marigold)",
            cursor: "pointer",
          }}
        >
          Retry
        </button>
      </div>
    </motion.div>
  );
}
