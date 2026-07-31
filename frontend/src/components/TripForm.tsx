"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import CityAutocomplete from "./CityAutocomplete";
import { TravelVibe, TripRequest } from "@/lib/api";

interface TripFormProps {
  onSubmit: (data: TripRequest) => void;
  isLoading: boolean;
}

const VIBES: { value: TravelVibe; label: string; desc: string }[] = [
  { value: "adventure", label: "Adventure", desc: "Thrills & outdoors" },
  { value: "culture", label: "Culture", desc: "History & heritage" },
  { value: "food", label: "Food", desc: "Cuisine & flavors" },
  { value: "relaxation", label: "Relaxation", desc: "Peace & calm" },
  { value: "spiritual", label: "Spiritual", desc: "Temples & faith" },
  { value: "nightlife", label: "Nightlife", desc: "Bars & clubs" },
];

function formatBudgetLabel(value: number): string {
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
  if (value >= 1000) return `₹${(value / 1000).toFixed(0)}K`;
  return `₹${value}`;
}

export default function TripForm({ onSubmit, isLoading }: TripFormProps) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [budget, setBudget] = useState(15000);
  const [selectedVibes, setSelectedVibes] = useState<TravelVibe[]>(["culture"]);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const toggleVibe = (vibe: TravelVibe) => {
    setSelectedVibes((prev) =>
      prev.includes(vibe) ? prev.filter((v) => v !== vibe) : [...prev, vibe]
    );
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!origin) newErrors.origin = "Select an origin city";
    if (!destination) newErrors.destination = "Select a destination city";
    if (!startDate) newErrors.startDate = "Pick a start date";
    if (!endDate) newErrors.endDate = "Pick an end date";
    if (startDate && endDate && new Date(endDate) <= new Date(startDate)) {
      newErrors.endDate = "End date must be after start date";
    }
    if (selectedVibes.length === 0) newErrors.vibes = "Select at least one vibe";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    onSubmit({
      origin,
      destination,
      start_date: startDate,
      end_date: endDate,
      budget,
      vibes: selectedVibes,
    });
  };

  const today = new Date().toISOString().split("T")[0];

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="max-w-[1180px] mx-auto rounded-[10px] overflow-hidden border border-glass-border shadow-[0_40px_80px_-30px_rgba(0,0,0,0.55)] grid grid-cols-1 min-[860px]:grid-cols-[1fr_260px]"
    >
      {/* ── Main ticket body ─────────────────────────────────── */}
      <form onSubmit={handleSubmit} className="bg-surface px-5 py-10 sm:px-8 md:px-12 space-y-5" id="trip-form">
        <div>
          <span className="font-[family-name:var(--font-space-mono)] text-[11px] uppercase tracking-[0.16em] text-marigold">
            Book the plan, not just the ticket
          </span>
          <h2 className="mt-1.5 font-[family-name:var(--font-teko)] font-semibold uppercase tracking-wide text-[clamp(2rem,3.6vw,2.8rem)] text-foreground">
            Plan your journey
          </h2>
          <p className="mt-2.5 max-w-[52ch] font-medium text-foreground-secondary">
            Tell us where you&apos;re starting, where you&apos;re headed, and what the trip is for. YatraAI handles the rest.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-[18px] pt-2">
          <div className="relative z-20">
            <CityAutocomplete
              label="From"
              placeholder="e.g. Delhi"
              value={origin}
              onChange={setOrigin}
              id="origin-city"
            />
            {errors.origin && <p className="text-error text-xs mt-1">{errors.origin}</p>}
          </div>
          <div className="relative z-10">
            <CityAutocomplete
              label="To"
              placeholder="e.g. Goa"
              value={destination}
              onChange={setDestination}
              id="destination-city"
            />
            {errors.destination && <p className="text-error text-xs mt-1">{errors.destination}</p>}
          </div>
          <div>
            <label
              htmlFor="start-date"
              className="block font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted mb-2"
            >
              Depart
            </label>
            <input
              id="start-date"
              type="date"
              value={startDate}
              min={today}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-3 bg-black/20 border border-glass-border rounded
                         text-foreground text-sm font-semibold focus:outline-none focus:border-marigold focus:ring-1
                         focus:ring-marigold/40 transition-all duration-200"
            />
            {errors.startDate && <p className="text-error text-xs mt-1">{errors.startDate}</p>}
          </div>
          <div>
            <label
              htmlFor="end-date"
              className="block font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted mb-2"
            >
              Return
            </label>
            <input
              id="end-date"
              type="date"
              value={endDate}
              min={startDate || today}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-3 bg-black/20 border border-glass-border rounded
                         text-foreground text-sm font-semibold focus:outline-none focus:border-marigold focus:ring-1
                         focus:ring-marigold/40 transition-all duration-200"
            />
            {errors.endDate && <p className="text-error text-xs mt-1">{errors.endDate}</p>}
          </div>
        </div>

        <div className="pb-1">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label
                htmlFor="budget-slider"
                className="font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted"
              >
                Budget
              </label>
              <span className="font-[family-name:var(--font-space-mono)] text-base font-bold text-marigold">
                {formatBudgetLabel(budget)}
              </span>
            </div>
            <input
              id="budget-slider"
              type="range"
              min={1000}
              max={100000}
              step={1000}
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className="w-full cursor-pointer"
            />
          </div>
        </div>

        <div>
            <label className="block font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted mb-2">
              Travel vibe
            </label>
            <div className="flex flex-wrap gap-2">
              {VIBES.map((vibe) => {
                const isSelected = selectedVibes.includes(vibe.value);
                return (
                  <motion.button
                    key={vibe.value}
                    type="button"
                    onClick={() => toggleVibe(vibe.value)}
                    whileTap={{ scale: 0.96 }}
                    className={`px-3 py-2 rounded-full border font-[family-name:var(--font-space-mono)] text-[11px] uppercase tracking-wide transition-all duration-150 ${
                      isSelected
                        ? "border-marigold bg-marigold text-[#24160a] font-bold"
                        : "border-glass-border text-foreground-muted hover:border-foreground hover:text-foreground"
                    }`}
                    id={`vibe-${vibe.value}`}
                    title={vibe.desc}
                  >
                    {vibe.label}
                  </motion.button>
                );
              })}
            </div>
            {errors.vibes && <p className="text-error text-xs mt-2">{errors.vibes}</p>}
        </div>

        {/* Submit */}
        <motion.button
          type="submit"
          disabled={isLoading}
          whileHover={isLoading ? {} : { scale: 1.01 }}
          whileTap={isLoading ? {} : { scale: 0.98 }}
          className={`w-full sm:w-auto px-[26px] py-[15px] rounded-[3px] font-[family-name:var(--font-space-mono)] text-[0.78rem] uppercase tracking-[0.06em] transition-all duration-300 ${
            isLoading
              ? "bg-marigold/40 cursor-not-allowed text-[#24160a]/70"
              : "bg-marigold text-[#24160a] hover:shadow-[0_6px_24px_rgba(242,169,59,0.3)]"
          }`}
          id="generate-trip-btn"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Planning your trip...
            </span>
          ) : (
            "Generate itinerary"
          )}
        </motion.button>
      </form>

      {/* ── Perforated ticket stub ───────────────────────────── */}
      <div className="ticket-perforated relative flex items-center justify-center min-h-[120px] min-[860px]:min-h-0 bg-[repeating-linear-gradient(135deg,var(--rust)_0_10px,var(--marigold-2)_10px_20px)]">
        <div className="absolute inset-0 bg-background opacity-[0.86]" />
        <div className="relative z-[2] px-6 py-4 min-[860px]:py-0 min-[860px]:[writing-mode:vertical-rl] font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-[0.16em] text-foreground-muted text-center">
          Boarding · YatraAI · Domestic India
        </div>
      </div>
    </motion.div>
  );
}
