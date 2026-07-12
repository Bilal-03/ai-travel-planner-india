"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import CityAutocomplete from "./CityAutocomplete";
import { TravelVibe, TripRequest, getVibeEmoji } from "@/lib/api";

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
    <motion.form
      onSubmit={handleSubmit}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="glass gradient-border p-6 md:p-8 rounded-2xl max-w-2xl mx-auto space-y-6"
      id="trip-form"
    >
      <div className="text-center mb-2">
        <h2
          className="text-2xl md:text-3xl font-bold font-[family-name:var(--font-outfit)] gradient-text"
        >
          Plan Your Journey
        </h2>
        <p className="text-foreground-muted text-sm mt-1">
          Tell us where you want to go and we'll plan the perfect trip
        </p>
      </div>

      {/* Origin & Destination */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="relative z-20">
          <CityAutocomplete
            label="From"
            placeholder="e.g. Delhi"
            value={origin}
            onChange={setOrigin}
            icon="🛫"
            id="origin-city"
          />
          {errors.origin && (
            <p className="text-error text-xs mt-1">{errors.origin}</p>
          )}
        </div>
        <div className="relative z-10">
          <CityAutocomplete
            label="To"
            placeholder="e.g. Goa"
            value={destination}
            onChange={setDestination}
            icon="🛬"
            id="destination-city"
          />
          {errors.destination && (
            <p className="text-error text-xs mt-1">{errors.destination}</p>
          )}
        </div>
      </div>

      {/* Dates */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="start-date" className="block text-sm font-medium text-foreground-secondary mb-2">
            Start Date
          </label>
          <input
            id="start-date"
            type="date"
            value={startDate}
            min={today}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full px-4 py-3 bg-glass-bg border border-glass-border rounded-xl
                       text-foreground focus:outline-none focus:border-primary focus:ring-1
                       focus:ring-primary/30 transition-all duration-200"
          />
          {errors.startDate && (
            <p className="text-error text-xs mt-1">{errors.startDate}</p>
          )}
        </div>
        <div>
          <label htmlFor="end-date" className="block text-sm font-medium text-foreground-secondary mb-2">
            End Date
          </label>
          <input
            id="end-date"
            type="date"
            value={endDate}
            min={startDate || today}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full px-4 py-3 bg-glass-bg border border-glass-border rounded-xl
                       text-foreground focus:outline-none focus:border-primary focus:ring-1
                       focus:ring-primary/30 transition-all duration-200"
          />
          {errors.endDate && (
            <p className="text-error text-xs mt-1">{errors.endDate}</p>
          )}
        </div>
      </div>

      {/* Budget Slider */}
      <div>
        <label htmlFor="budget-slider" className="block text-sm font-medium text-foreground-secondary mb-2">
          Budget
        </label>
        <div className="flex items-center justify-between mb-2">
          <span className="text-foreground-muted text-xs">₹1,000</span>
          <span className="text-xl font-bold gradient-text">
            {formatBudgetLabel(budget)}
          </span>
          <span className="text-foreground-muted text-xs">₹1,00,000</span>
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
        <div className="flex justify-between text-xs text-foreground-muted mt-1">
          <span>Budget</span>
          <span>Luxury</span>
        </div>
      </div>

      {/* Vibe Selector */}
      <div>
        <label className="block text-sm font-medium text-foreground-secondary mb-3">
          Travel Vibe
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {VIBES.map((vibe) => {
            const isSelected = selectedVibes.includes(vibe.value);
            return (
              <motion.button
                key={vibe.value}
                type="button"
                onClick={() => toggleVibe(vibe.value)}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className={`
                  p-3 rounded-xl border text-left transition-all duration-200
                  ${
                    isSelected
                      ? "border-primary bg-primary/15 shadow-[0_0_20px_rgba(99,102,241,0.15)]"
                      : "border-glass-border bg-glass-bg hover:border-glass-highlight"
                  }
                `}
                id={`vibe-${vibe.value}`}
              >
                <div className="text-2xl mb-1">{getVibeEmoji(vibe.value)}</div>
                <div className="font-medium text-sm text-foreground">
                  {vibe.label}
                </div>
                <div className="text-xs text-foreground-muted">{vibe.desc}</div>
              </motion.button>
            );
          })}
        </div>
        {errors.vibes && (
          <p className="text-error text-xs mt-2">{errors.vibes}</p>
        )}
      </div>

      {/* Submit */}
      <motion.button
        type="submit"
        disabled={isLoading}
        whileHover={isLoading ? {} : { scale: 1.02 }}
        whileTap={isLoading ? {} : { scale: 0.98 }}
        className={`
          w-full py-4 rounded-xl font-semibold text-lg transition-all duration-300
          ${
            isLoading
              ? "bg-primary/50 cursor-not-allowed"
              : "bg-gradient-to-r from-primary to-primary-light hover:shadow-[0_0_30px_rgba(99,102,241,0.3)]"
          }
          text-white
        `}
        id="generate-trip-btn"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Planning your trip...
          </span>
        ) : (
          "✨ Generate My Itinerary"
        )}
      </motion.button>
    </motion.form>
  );
}
