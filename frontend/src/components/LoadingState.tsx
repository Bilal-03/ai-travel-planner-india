"use client";

import { motion } from "framer-motion";
import { GenerationStatus } from "@/lib/api";

interface LoadingStateProps {
  waitingForBackend?: boolean;
  status?: GenerationStatus | null;
  onCancel: () => void;
  onRetry: () => void;
}

const STEP_ICONS: Record<string, string> = {
  starting: "🚀",
  geocoding: "🗺️",
  trip_context: "📍",
  planning: "🤖",
  validating: "✅",
  routing: "🧭",
  cached: "⚡",
  ready: "✨",
};

export default function LoadingState({ waitingForBackend = false, status, onCancel, onRetry }: LoadingStateProps) {
  const title = waitingForBackend
    ? "Waking up the planner…"
    : status?.message || "Starting your trip plan…";
  const detail = waitingForBackend
    ? "The server is starting. Your completed form is safely kept here."
    : "Usually 30–75 seconds on the first plan. We’ll show real planner updates as they happen.";
  const progress = waitingForBackend ? Math.max(status?.progress || 0, 4) : status?.progress || 8;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass gradient-border mx-auto mt-5 w-full max-w-lg rounded-2xl p-6 text-center">
      <motion.div className="mb-4 text-5xl" animate={{ y: [0, -8, 0] }} transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}>
        {waitingForBackend ? "⏳" : STEP_ICONS[status?.step || "starting"] || "🧳"}
      </motion.div>
      <h3 className="font-[family-name:var(--font-outfit)] text-xl font-bold text-foreground">{title}</h3>
      <p className="mt-1 text-sm text-foreground-muted">{detail}</p>
      <div className="mt-5 h-2 w-full overflow-hidden rounded-full bg-glass-bg"><motion.div className="h-full rounded-full bg-gradient-to-r from-primary to-accent" initial={{ width: 0 }} animate={{ width: `${Math.min(progress, 98)}%` }} transition={{ duration: 0.45, ease: "easeOut" }} /></div>
      <div className="mt-4 flex justify-center gap-3">
        <button onClick={onCancel} className="rounded-lg border border-glass-border px-3 py-2 text-sm text-foreground-secondary hover:bg-glass-highlight">Cancel</button>
        <button onClick={onRetry} className="rounded-lg border border-primary/50 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/10">Retry</button>
      </div>
    </motion.div>
  );
}
