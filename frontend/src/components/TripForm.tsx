"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import CityAutocomplete from "./CityAutocomplete";
import {
  AccommodationPreference,
  DietaryPreference,
  TravelPreference,
  TravelVibe,
  TripPace,
  TripRequest,
  TransportMode,
} from "@/lib/api";

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

export default function TripForm({ onSubmit, isLoading }: TripFormProps) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [budget, setBudget] = useState(15000);
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [travelPreference, setTravelPreference] = useState<TravelPreference>("balanced");
  const [pace, setPace] = useState<TripPace>("balanced");
  const [selectedVibes, setSelectedVibes] = useState<TravelVibe[]>(["culture"]);
  const [transportMode, setTransportMode] = useState<TransportMode | undefined>();
  const [accommodationPreference, setAccommodationPreference] = useState<AccommodationPreference>("budget");
  const [dietaryPreference, setDietaryPreference] = useState<DietaryPreference | undefined>();
  const [seniorCitizens, setSeniorCitizens] = useState(0);
  const [accessibilityRequirements, setAccessibilityRequirements] = useState("");
  const [allowEarlyMorningTravel, setAllowEarlyMorningTravel] = useState(false);
  const [allowLateNightTravel, setAllowLateNightTravel] = useState(false);
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
    if (origin && destination && origin.trim().toLowerCase() === destination.trim().toLowerCase()) {
      newErrors.destination = "Choose a different destination";
    }
    if (startDate && endDate && new Date(endDate) < new Date(startDate)) {
      newErrors.endDate = "Return date cannot be before departure";
    }
    if (budget < (adults + children) * 1500) newErrors.budget = "This total is too low for your travel party";
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
      transport_mode: transportMode,
      accommodation_preference: accommodationPreference,
      adults,
      children,
      travel_preference: travelPreference,
      pace,
      dietary_preference: dietaryPreference,
      senior_citizens: seniorCitizens,
      accessibility_requirements: accessibilityRequirements.trim() || undefined,
      allow_early_morning_travel: allowEarlyMorningTravel,
      allow_late_night_travel: allowLateNightTravel,
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

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-[18px]">
          <div>
            <label className="block font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted mb-2">
              Travellers
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className="text-xs text-foreground-secondary">Adults
                <input type="number" min={1} max={20} value={adults} onChange={(event) => setAdults(Math.max(1, Number(event.target.value) || 1))} className="mt-1 w-full rounded border border-glass-border bg-black/20 px-3 py-2 text-sm text-foreground" />
              </label>
              <label className="text-xs text-foreground-secondary">Children
                <input type="number" min={0} max={20} value={children} onChange={(event) => setChildren(Math.max(0, Number(event.target.value) || 0))} className="mt-1 w-full rounded border border-glass-border bg-black/20 px-3 py-2 text-sm text-foreground" />
              </label>
            </div>
          </div>
          <div>
            <label htmlFor="trip-budget" className="block font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted mb-2">
              Total trip budget for {adults + children} traveller{adults + children === 1 ? "" : "s"}, including transport and stay
            </label>
            <div className="flex rounded border border-glass-border bg-black/20 focus-within:border-marigold">
              <span className="px-3 py-2 text-foreground-muted">₹</span>
              <input id="trip-budget" type="number" min={(adults + children) * 1500} max={1000000} step={500} value={budget} onChange={(event) => setBudget(Number(event.target.value) || 0)} className="min-w-0 flex-1 bg-transparent py-2 pr-3 text-sm font-semibold text-foreground outline-none" />
            </div>
            {errors.budget && <p className="text-error text-xs mt-1">{errors.budget}</p>}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-[18px]">
          <div>
            <label className="block font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted mb-2">Travel preference</label>
            <div className="grid grid-cols-3 gap-2">
              {(["cheapest", "fastest", "balanced"] as TravelPreference[]).map((preference) => (
                <button key={preference} type="button" onClick={() => setTravelPreference(preference)} className={`rounded border px-2 py-2 text-xs capitalize transition-colors ${travelPreference === preference ? "border-marigold bg-marigold text-[#24160a]" : "border-glass-border text-foreground-muted hover:text-foreground"}`}>{preference}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="block font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted mb-2">Pace</label>
            <div className="grid grid-cols-3 gap-2">
              {(["relaxed", "balanced", "packed"] as TripPace[]).map((option) => (
                <button key={option} type="button" onClick={() => setPace(option)} className={`rounded border px-2 py-2 text-xs capitalize transition-colors ${pace === option ? "border-marigold bg-marigold text-[#24160a]" : "border-glass-border text-foreground-muted hover:text-foreground"}`}>{option}</button>
              ))}
            </div>
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

        <details className="rounded border border-glass-border bg-black/10 p-3">
          <summary className="cursor-pointer font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-secondary">
            More preferences
          </summary>
          <div className="mt-4 space-y-4">
            <div>
              <span className="block text-xs text-foreground-secondary mb-2">Transport preference</span>
              <div className="grid grid-cols-4 gap-2">
                <button type="button" onClick={() => setTransportMode(undefined)} className={`rounded border px-2 py-2 text-xs ${!transportMode ? "border-marigold bg-marigold text-[#24160a]" : "border-glass-border text-foreground-muted"}`}>Any</button>
                {(["train", "flight", "road"] as TransportMode[]).map((mode) => (
                  <button key={mode} type="button" onClick={() => setTransportMode(mode)} className={`rounded border px-2 py-2 text-xs capitalize ${transportMode === mode ? "border-marigold bg-marigold text-[#24160a]" : "border-glass-border text-foreground-muted"}`}>{mode}</button>
                ))}
              </div>
            </div>

            <div>
              <span className="block text-xs text-foreground-secondary mb-2">Hotel level</span>
              <div className="grid grid-cols-3 gap-2">
                {(["budget", "standard", "comfort"] as AccommodationPreference[]).map((tier) => (
                  <button key={tier} type="button" onClick={() => setAccommodationPreference(tier)} className={`rounded border px-2 py-2 text-xs capitalize ${accommodationPreference === tier ? "border-marigold bg-marigold text-[#24160a]" : "border-glass-border text-foreground-muted"}`}>{tier}</button>
                ))}
              </div>
            </div>

            <div>
              <span className="block text-xs text-foreground-secondary mb-2">Food preference</span>
              <div className="grid grid-cols-3 gap-2">
                <button type="button" onClick={() => setDietaryPreference(undefined)} className={`rounded border px-2 py-2 text-xs ${!dietaryPreference ? "border-marigold bg-marigold text-[#24160a]" : "border-glass-border text-foreground-muted"}`}>No preference</button>
                <button type="button" onClick={() => setDietaryPreference("vegetarian")} className={`rounded border px-2 py-2 text-xs ${dietaryPreference === "vegetarian" ? "border-marigold bg-marigold text-[#24160a]" : "border-glass-border text-foreground-muted"}`}>Vegetarian</button>
                <button type="button" onClick={() => setDietaryPreference("non_vegetarian")} className={`rounded border px-2 py-2 text-xs ${dietaryPreference === "non_vegetarian" ? "border-marigold bg-marigold text-[#24160a]" : "border-glass-border text-foreground-muted"}`}>Non-vegetarian</button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-[150px_1fr] gap-3">
              <label className="text-xs text-foreground-secondary">Senior citizens
                <input type="number" min={0} max={adults} value={seniorCitizens} onChange={(event) => setSeniorCitizens(Math.min(adults, Math.max(0, Number(event.target.value) || 0)))} className="mt-1 w-full rounded border border-glass-border bg-black/20 px-3 py-2 text-sm text-foreground" />
              </label>
              <label className="text-xs text-foreground-secondary">Accessibility requirements
                <input type="text" maxLength={500} value={accessibilityRequirements} onChange={(event) => setAccessibilityRequirements(event.target.value)} placeholder="Wheelchair access, step-free routes…" className="mt-1 w-full rounded border border-glass-border bg-black/20 px-3 py-2 text-sm text-foreground" />
              </label>
            </div>

            <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-foreground-secondary">
              <label className="flex items-center gap-2"><input type="checkbox" checked={allowEarlyMorningTravel} onChange={(event) => setAllowEarlyMorningTravel(event.target.checked)} /> Early-morning travel is okay</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={allowLateNightTravel} onChange={(event) => setAllowLateNightTravel(event.target.checked)} /> Late-night travel is okay</label>
            </div>
          </div>
        </details>

        {/* Submit */}
        <div className="flex justify-center">
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
        </div>
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
