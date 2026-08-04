"use client";

import { FormEvent, useState } from "react";
import { Itinerary, formatINR } from "@/lib/api";

interface TripConversationProps {
  itinerary: Itinerary;
  onRefine: (instruction: string) => Promise<void>;
  onUndo: () => Promise<void>;
  isRefining: boolean;
  refinementError: string | null;
  canUndo: boolean;
}

const SUGGESTIONS = [
  "Make day 2 less crowded",
  "Reduce the trip budget",
  "Avoid early morning travel",
  "Regenerate day 1",
];

export default function TripConversation({
  itinerary,
  onRefine,
  onUndo,
  isRefining,
  refinementError,
  canUndo,
}: TripConversationProps) {
  const [instruction, setInstruction] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const value = instruction.trim();
    if (value.length < 3 || isRefining) return;
    await onRefine(value);
    setInstruction("");
  };

  return (
    <aside className="workspace-conversation space-y-4" aria-label="Trip conversation and changes">
      <div className="workspace-panel rounded-xl border border-glass-border bg-glass-bg p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.16em] text-marigold">Plan conversation</p>
            <h2 className="mt-1 text-lg font-bold text-foreground">Shape the trip as you go.</h2>
          </div>
          <span className="rounded-full bg-success/15 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-success">Server checked</span>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-foreground-secondary">
          Ask for a change in plain language. YatraAI updates only the affected day or travel leg, then validates timing, opening hours, pace, and budget before saving.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button key={suggestion} type="button" onClick={() => setInstruction(suggestion)} className="rounded-full border border-glass-border px-2.5 py-1.5 text-left text-[11px] text-foreground-secondary transition hover:border-primary hover:text-foreground">
              {suggestion}
            </button>
          ))}
        </div>
        <form onSubmit={submit} className="mt-4">
          <label htmlFor="workspace-refinement" className="sr-only">Describe a trip change</label>
          <textarea
            id="workspace-refinement"
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            placeholder="e.g. Move Amber Fort to day 2"
            rows={3}
            maxLength={500}
            className="w-full resize-y rounded-lg border border-glass-border bg-background/60 px-3 py-2.5 text-sm text-foreground outline-none transition focus:border-primary focus:ring-1 focus:ring-primary/30"
          />
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className="text-[11px] text-foreground-muted">Changes are kept private to this trip.</span>
            <button type="submit" disabled={isRefining || instruction.trim().length < 3} className="warm-button rounded-lg px-3 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">
              {isRefining ? "Checking…" : "Apply change"}
            </button>
          </div>
          {refinementError && <p className="mt-2 text-xs text-error" role="alert">{refinementError}</p>}
        </form>
      </div>

      <div className="workspace-panel rounded-xl border border-glass-border bg-glass-bg p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-foreground">Trip guardrails</h3>
          <button type="button" onClick={() => void onUndo()} disabled={!canUndo || isRefining} className="rounded-lg border border-glass-border px-2.5 py-1.5 text-[11px] font-medium text-foreground-secondary transition hover:border-primary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40" title={canUndo ? "Restore the previous server-validated version" : "Make a change to enable undo"}>
            ↶ Undo latest
          </button>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <div className="rounded-lg bg-background/45 p-2.5"><span className="block text-foreground-muted">Pace</span><strong className="capitalize text-foreground">{itinerary.pace}</strong></div>
          <div className="rounded-lg bg-background/45 p-2.5"><span className="block text-foreground-muted">Budget left</span><strong className="text-foreground">{formatINR(itinerary.budget.remaining)}</strong></div>
          <div className="rounded-lg bg-background/45 p-2.5"><span className="block text-foreground-muted">Must visit</span><strong className="text-foreground">{itinerary.mandatory_places?.length || "None"}</strong></div>
          <div className="rounded-lg bg-background/45 p-2.5"><span className="block text-foreground-muted">Data mode</span><strong className="text-foreground">Live + estimates</strong></div>
        </div>
      </div>
    </aside>
  );
}
