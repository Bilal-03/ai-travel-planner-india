"use client";

import { useMemo, useState } from "react";
import { api, ApiError, formatDate, formatDuration, formatINR, MultiCityTrip } from "@/lib/api";

interface MultiCityWorkspaceProps {
  trip: MultiCityTrip;
  onUpdate: (trip: MultiCityTrip) => void;
  onNewTrip: () => void;
}

export default function MultiCityWorkspace({ trip, onUpdate, onNewTrip }: MultiCityWorkspaceProps) {
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nightDrafts, setNightDrafts] = useState<Record<string, number>>(() => Object.fromEntries(trip.destination_stays.map((stay) => [stay.id, stay.nights])));

  const routeLabel = useMemo(
    () => [trip.origin.name, ...trip.destination_stays.map((stay) => stay.city.name), trip.origin.name].join(" → "),
    [trip],
  );

  const moveStay = async (index: number, direction: -1 | 1) => {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= trip.destination_stays.length) return;
    const ids = trip.destination_stays.map((stay) => stay.id);
    [ids[index], ids[nextIndex]] = [ids[nextIndex], ids[index]];
    setSaving("route");
    setError(null);
    try {
      onUpdate(await api.reorderMultiCityTrip(trip.id, ids));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The route could not be reordered.");
    } finally {
      setSaving(null);
    }
  };

  const saveNights = async (stayId: string) => {
    const nights = Math.max(1, Math.min(14, nightDrafts[stayId] || 1));
    setNightDrafts((current) => ({ ...current, [stayId]: nights }));
    setSaving(stayId);
    setError(null);
    try {
      onUpdate(await api.updateMultiCityStay(trip.id, stayId, { nights }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That destination stay could not be updated.");
    } finally {
      setSaving(null);
    }
  };

  return (
    <main className="mx-auto max-w-[1280px] px-5 pb-20 pt-16 sm:px-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.18em] text-marigold">Multi-city trip workspace</p>
          <h1 className="mt-3 max-w-5xl text-3xl font-semibold leading-tight text-foreground sm:text-5xl">{routeLabel}</h1>
          <p className="mt-3 text-sm text-foreground-secondary">{formatDate(trip.start_date)} – {formatDate(trip.end_date)} · {trip.total_days} days · {trip.destination_stays.length} destination stays</p>
        </div>
        <button type="button" onClick={onNewTrip} className="rounded border border-glass-border px-4 py-2 text-xs uppercase tracking-wide text-foreground-muted transition hover:border-marigold hover:text-foreground">Plan another trip</button>
      </div>

      {error && <p role="alert" className="mt-5 rounded border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">{error}</p>}

      <section className="mt-8 grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-[6px] border border-glass-border bg-background/35 p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.16em] text-foreground-muted">Route order</p>
              <h2 className="mt-1 text-xl font-semibold text-foreground">Edit the journey without losing the plan</h2>
            </div>
            {saving === "route" && <span className="text-xs text-marigold">Recalculating legs…</span>}
          </div>
          <div className="mt-5 space-y-3">
            {trip.destination_stays.map((stay, index) => (
              <div key={stay.id} className="rounded border border-glass-border bg-black/10 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-wide text-marigold">Stop {index + 1}</p>
                    <h3 className="mt-1 text-lg font-semibold text-foreground">{stay.city.name}</h3>
                    <p className="mt-1 text-xs text-foreground-muted">{formatDate(stay.arrival_date)} – {formatDate(stay.departure_date)} · {stay.nights} nights</p>
                  </div>
                  <div className="flex gap-1">
                    <button type="button" aria-label={`Move ${stay.city.name} up`} onClick={() => void moveStay(index, -1)} disabled={index === 0 || saving !== null} className="rounded border border-glass-border px-2 py-1 text-xs text-foreground-muted disabled:opacity-30">↑</button>
                    <button type="button" aria-label={`Move ${stay.city.name} down`} onClick={() => void moveStay(index, 1)} disabled={index === trip.destination_stays.length - 1 || saving !== null} className="rounded border border-glass-border px-2 py-1 text-xs text-foreground-muted disabled:opacity-30">↓</button>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap items-end gap-2">
                  <label className="text-xs text-foreground-secondary">Nights
                    <input type="number" min={1} max={14} value={nightDrafts[stay.id] ?? stay.nights} onChange={(event) => setNightDrafts((current) => ({ ...current, [stay.id]: Number(event.target.value) || 1 }))} className="ml-2 w-16 rounded border border-glass-border bg-black/20 px-2 py-1 text-xs text-foreground" />
                  </label>
                  <button type="button" onClick={() => void saveNights(stay.id)} disabled={saving !== null} className="rounded border border-marigold/50 px-3 py-1.5 text-xs text-marigold disabled:opacity-40">{saving === stay.id ? "Saving…" : "Update stay"}</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-[6px] border border-glass-border bg-background/35 p-5">
            <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.16em] text-foreground-muted">Travel legs</p>
            <div className="mt-4 space-y-3">
              {trip.travel_legs.map((leg) => (
                <div key={leg.id} className="rounded border border-glass-border bg-black/10 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-foreground">{leg.origin.name} → {leg.destination.name}</p>
                    <span className="rounded-full bg-marigold/10 px-2 py-1 text-[10px] uppercase text-marigold">{leg.mode}</span>
                  </div>
                  <p className="mt-1 text-xs text-foreground-muted">{formatDate(leg.date)} · {formatDuration(leg.duration_minutes)} · {formatINR(leg.fare)}</p>
                  <p className="mt-2 text-[11px] text-foreground-muted">{leg.selected_offer?.provider || "No selected offer"} · {leg.alternatives.length} alternative{leg.alternatives.length === 1 ? "" : "s"}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[6px] border border-glass-border bg-background/35 p-5">
            <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.16em] text-foreground-muted">Budget estimate</p>
            <div className="mt-3 flex items-baseline justify-between gap-3"><span className="text-sm text-foreground-secondary">Estimated total</span><strong className="text-2xl text-marigold">{formatINR(trip.budget.total_estimated)}</strong></div>
            <p className="mt-2 text-xs text-foreground-muted">{formatINR(Math.max(0, trip.budget.remaining))} remaining from the working budget. Provider and booking values should be verified.</p>
          </div>
        </div>
      </section>

      <section className="mt-8 rounded-[6px] border border-glass-border bg-background/35 p-5">
        <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.16em] text-foreground-muted">Itinerary days</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {trip.itinerary_days.map((day) => (
            <article key={`${day.day_number}-${day.date}`} className="rounded border border-glass-border bg-black/10 p-4">
              <div className="flex items-start justify-between gap-3"><div><p className="text-xs uppercase tracking-wide text-marigold">Day {day.day_number}</p><h3 className="mt-1 font-semibold text-foreground">{formatDate(day.date)}{day.destination ? ` · ${day.destination.name}` : " · Return"}</h3></div><span className="text-xs text-foreground-muted">{formatINR(day.day_budget)}</span></div>
              {day.visits.length > 0 ? <ul className="mt-3 space-y-2">{day.visits.map((visit) => <li key={visit.id} className="text-sm text-foreground-secondary">{visit.poi.name}<span className="ml-2 text-xs text-foreground-muted">{visit.start_time}–{visit.end_time}</span></li>)}</ul> : <p className="mt-3 text-xs text-foreground-muted">Keep this day flexible for the travel leg.</p>}
              {day.notes && <p className="mt-3 text-xs text-foreground-muted">{day.notes}</p>}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
