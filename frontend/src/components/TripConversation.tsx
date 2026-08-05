"use client";

import { FormEvent, useState } from "react";
import { Itinerary, formatDate, formatINR } from "@/lib/api";

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
  "Regenerate day 1",
  "Add a food-focused stop",
];

function PreferenceValue({ itinerary }: { itinerary: Itinerary }) {
  const experiences = itinerary.preferences?.experiences?.filter(Boolean) || [];
  const pace = itinerary.preferences?.pace;

  if (!experiences.length && !pace) return <span className="text-foreground-muted">You decide</span>;

  return (
    <span className="text-foreground">
      {[experiences.join(", "), pace ? `${pace} pace` : ""].filter(Boolean).join(" · ")}
    </span>
  );
}

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
    <aside className="workspace-conversation" aria-label="Trip conversation and changes">
      <div className="workspace-conversation-header">
        <div>
          <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.16em] text-marigold">Chat</p>
          <h2 className="mt-0.5 text-lg font-bold tracking-tight text-foreground">Plan conversation</h2>
        </div>
        <span className="rounded-full border border-glass-border bg-background/35 px-2.5 py-1 text-[10px] font-semibold text-success">Server checked</span>
      </div>

      <div className="workspace-conversation-scroll">
        <section className="workspace-message workspace-message-user" aria-label="Trip brief">
          <div className="flex items-center justify-between gap-3">
            <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-foreground-muted">Your brief</p>
            <span className="text-[10px] text-foreground-muted">Private</span>
          </div>
          <p className="mt-2 text-sm font-medium leading-relaxed text-foreground">Plan {itinerary.total_days} days from {itinerary.origin.name} to {itinerary.destination.name}.</p>
          <dl className="mt-3 space-y-2 text-xs">
            <div className="flex items-start justify-between gap-3"><dt className="text-foreground-muted">When</dt><dd className="text-right text-foreground">{formatDate(itinerary.start_date)} – {formatDate(itinerary.end_date)}</dd></div>
            <div className="flex items-start justify-between gap-3"><dt className="text-foreground-muted">Travellers</dt><dd className="text-right text-foreground">{itinerary.members || 2}</dd></div>
            <div className="flex items-start justify-between gap-3"><dt className="text-foreground-muted">Working budget</dt><dd className="text-right text-foreground">{formatINR(itinerary.budget.total_estimated)}</dd></div>
            <div className="flex items-start justify-between gap-3"><dt className="text-foreground-muted">Trip shape</dt><dd className="max-w-[65%] text-right"><PreferenceValue itinerary={itinerary} /></dd></div>
          </dl>
        </section>

        <section className="workspace-message workspace-message-assistant">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-marigold">YatraAI</p>
              <h3 className="mt-1 text-base font-bold text-foreground">Shape the trip as you go.</h3>
            </div>
            <span className="text-lg text-marigold" aria-hidden="true">✦</span>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-foreground-secondary">Ask for a change in plain language. YatraAI updates only the affected day or travel leg, then validates timing, opening hours, and budget before saving.</p>
          {itinerary.planning_notes && <p className="mt-3 border-l-2 border-marigold/50 pl-3 text-xs leading-relaxed text-foreground-muted">Planning note: {itinerary.planning_notes}</p>}
        </section>

        <section className="workspace-panel rounded-xl border border-glass-border bg-glass-bg p-4" aria-live="polite">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-foreground">Research trail</h3>
            <span className="text-[10px] font-[family-name:var(--font-space-mono)] uppercase tracking-wide text-foreground-muted">{itinerary.research_events?.length || 0} checkpoints</span>
          </div>
          {itinerary.research_events?.length ? (
            <ol className="mt-3 space-y-2.5">
              {itinerary.research_events.slice(-6).map((event) => (
                <li key={event.id} className="flex items-start gap-2 text-xs leading-relaxed text-foreground-secondary">
                  <span className={event.status === "error" ? "mt-0.5 text-error" : "mt-0.5 text-success"} aria-hidden="true">{event.status === "error" ? "!" : "✓"}</span>
                  <span>{event.message}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-2 text-xs leading-relaxed text-foreground-muted">The planner&apos;s search and validation checkpoints will appear here.</p>
          )}
        </section>

        <section className="workspace-panel rounded-xl border border-glass-border bg-glass-bg p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-foreground">Trip guardrails</h3>
            <button type="button" onClick={() => void onUndo()} disabled={!canUndo || isRefining} className="rounded-lg border border-glass-border px-2.5 py-1.5 text-[11px] font-medium text-foreground-secondary transition hover:border-primary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40" title={canUndo ? "Restore the previous server-validated version" : "Make a change to enable undo"}>
              ↶ Undo latest
            </button>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-background/45 p-2.5"><span className="block text-foreground-muted">Plan</span><strong className="text-foreground">{(itinerary.plan_options || []).find((option) => option.id === itinerary.selected_plan_id)?.title || "Selected"}</strong></div>
            <div className="rounded-lg bg-background/45 p-2.5"><span className="block text-foreground-muted">Budget left</span><strong className="text-foreground">{formatINR(itinerary.budget.remaining)}</strong></div>
            <div className="rounded-lg bg-background/45 p-2.5"><span className="block text-foreground-muted">Members</span><strong className="text-foreground">{itinerary.members || 2}</strong></div>
            <div className="rounded-lg bg-background/45 p-2.5"><span className="block text-foreground-muted">Data mode</span><strong className="text-foreground">Live + estimates</strong></div>
          </div>
        </section>
      </div>

      <form onSubmit={submit} className="workspace-composer">
        <div className="no-scrollbar flex gap-2 overflow-x-auto pb-2">
          {SUGGESTIONS.map((suggestion) => (
            <button key={suggestion} type="button" onClick={() => setInstruction(suggestion)} className="shrink-0 rounded-full border border-glass-border bg-background/35 px-2.5 py-1.5 text-left text-[11px] text-foreground-secondary transition hover:border-primary hover:text-foreground">
              {suggestion}
            </button>
          ))}
        </div>
        <label htmlFor="workspace-refinement" className="sr-only">Describe a trip change</label>
        <div className="workspace-composer-input">
          <textarea
            id="workspace-refinement"
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            placeholder="Ask to add, remove, or rearrange something…"
            rows={2}
            maxLength={500}
            className="min-h-[52px] w-full resize-none bg-transparent px-1 py-1 text-sm text-foreground outline-none placeholder:text-foreground-muted"
          />
          <button type="submit" aria-label="Apply trip change" disabled={isRefining || instruction.trim().length < 3} className="warm-button self-end rounded-full p-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">
            {isRefining ? "…" : "↑"}
          </button>
        </div>
        <div className="mt-2 flex items-center justify-between gap-3">
          <span className="text-[11px] text-foreground-muted">Changes stay private to this trip.</span>
          {refinementError && <p className="text-right text-xs text-error" role="alert">{refinementError}</p>}
        </div>
      </form>
    </aside>
  );
}
