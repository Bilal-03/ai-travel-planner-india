"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  DestinationStayRequest,
  MultiCityTripRequest,
} from "@/lib/api";

interface MultiCityPlannerProps {
  isLoading: boolean;
  onSubmit: (request: MultiCityTripRequest) => void;
}

function defaultStartDate(): string {
  const date = new Date();
  date.setDate(date.getDate() + 30);
  return date.toISOString().slice(0, 10);
}

const inputClass = "mt-1 w-full rounded border border-glass-border bg-black/20 px-3 py-2 text-sm text-foreground outline-none focus:border-marigold";

export default function MultiCityPlanner({ isLoading, onSubmit }: MultiCityPlannerProps) {
  const [origin, setOrigin] = useState("Delhi");
  const [startDate, setStartDate] = useState(defaultStartDate);
  const [budget, setBudget] = useState(30000);
  const [stays, setStays] = useState<DestinationStayRequest[]>([
    { destination: "Jaipur", nights: 2 },
    { destination: "Jodhpur", nights: 2 },
    { destination: "Udaipur", nights: 3 },
  ]);
  const [message, setMessage] = useState<string | null>(null);

  const totalNights = useMemo(() => stays.reduce((total, stay) => total + stay.nights, 0), [stays]);

  const updateStay = (index: number, update: Partial<DestinationStayRequest>) => {
    setStays((current) => current.map((stay, stayIndex) => stayIndex === index ? { ...stay, ...update } : stay));
  };

  const addStay = () => {
    if (stays.length < 5) setStays((current) => [...current, { destination: "", nights: 1 }]);
  };

  const removeStay = (index: number) => {
    if (stays.length > 2) setStays((current) => current.filter((_, stayIndex) => stayIndex !== index));
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = stays.map((stay) => ({ ...stay, destination: stay.destination.trim() }));
    const names = normalized.map((stay) => stay.destination.toLowerCase());
    if (!origin.trim() || normalized.some((stay) => !stay.destination)) {
      setMessage("Add an origin and every destination stop before generating.");
      return;
    }
    if (new Set(names).size !== names.length || names.includes(origin.trim().toLowerCase())) {
      setMessage("Each destination must be a different city from the origin and other stops.");
      return;
    }
    if (totalNights + 1 > 14) {
      setMessage("Keep the route to 14 calendar days or fewer.");
      return;
    }
    setMessage(null);
    onSubmit({
      origin: origin.trim(),
      stays: normalized,
      start_date: startDate,
      budget,
      vibes: ["culture"],
      accommodation_preference: "budget",
      adults: 2,
      children: 0,
      travel_preference: "balanced",
      pace: "balanced",
      senior_citizens: 0,
      allow_early_morning_travel: false,
      allow_late_night_travel: false,
    });
  };

  return (
    <section id="multi-city-planner" className="mx-auto mt-8 max-w-[1180px] rounded-[6px] border border-marigold/30 bg-marigold/[0.04] p-5 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.18em] text-marigold">Phase 6 route studio</p>
          <h2 className="mt-2 text-2xl font-semibold text-foreground">Plan a multi-city route</h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-foreground-secondary">Build a real route of stays and travel legs. Each stop keeps its own identity, so reordering the route does not rebuild unrelated destination visits.</p>
        </div>
        <span className="rounded-full border border-glass-border px-3 py-1 font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-wide text-foreground-muted">{stays.length} stops · {totalNights} nights</span>
      </div>

      <form onSubmit={submit} className="mt-6 space-y-5">
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="text-xs text-foreground-secondary">Start from
            <input aria-label="Multi-city origin" value={origin} onChange={(event) => setOrigin(event.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-foreground-secondary">Departure date
            <input aria-label="Multi-city start date" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className={inputClass} />
          </label>
          <label className="text-xs text-foreground-secondary">Working budget (₹)
            <input aria-label="Multi-city budget" type="number" min={3000} value={budget} onChange={(event) => setBudget(Number(event.target.value) || 0)} className={inputClass} />
          </label>
        </div>

        <div className="space-y-3">
          {stays.map((stay, index) => (
            <div key={`${index}-${stay.destination}`} className="grid gap-3 rounded border border-glass-border bg-black/10 p-3 sm:grid-cols-[1fr_130px_auto] sm:items-end">
              <label className="text-xs text-foreground-secondary">Stop {index + 1}
                <input aria-label={`Destination stop ${index + 1}`} value={stay.destination} onChange={(event) => updateStay(index, { destination: event.target.value })} className={inputClass} placeholder="City name" />
              </label>
              <label className="text-xs text-foreground-secondary">Nights
                <input aria-label={`Nights at stop ${index + 1}`} type="number" min={1} max={14} value={stay.nights} onChange={(event) => updateStay(index, { nights: Math.max(1, Number(event.target.value) || 1) })} className={inputClass} />
              </label>
              <button type="button" onClick={() => removeStay(index)} disabled={stays.length <= 2} className="rounded border border-glass-border px-3 py-2 text-xs text-foreground-muted transition hover:border-error hover:text-error disabled:cursor-not-allowed disabled:opacity-30">Remove</button>
            </div>
          ))}
          <button type="button" onClick={addStay} disabled={stays.length >= 5} className="rounded border border-dashed border-marigold/50 px-3 py-2 text-xs text-marigold transition hover:bg-marigold/10 disabled:cursor-not-allowed disabled:opacity-40">+ Add another city</button>
        </div>

        {message && <p className="rounded border border-error/30 bg-error/10 px-3 py-2 text-xs text-error" role="alert">{message}</p>}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-foreground-muted">The return leg to {origin || "your origin"} is added automatically.</p>
          <button id="generate-multi-city-btn" type="submit" disabled={isLoading} className="rounded-[3px] bg-marigold px-5 py-3 font-[family-name:var(--font-space-mono)] text-xs font-bold uppercase tracking-wide text-[#24160a] transition hover:shadow-[0_6px_24px_rgba(242,169,59,0.3)] disabled:cursor-not-allowed disabled:opacity-50">{isLoading ? "Building route…" : "Generate multi-city route"}</button>
        </div>
      </form>
    </section>
  );
}
