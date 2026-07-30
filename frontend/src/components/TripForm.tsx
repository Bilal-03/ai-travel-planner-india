"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import CityAutocomplete from "./CityAutocomplete";
import { TravelVibe, TripRequest } from "@/lib/api";

interface TripFormProps {
  onSubmit: (data: TripRequest) => void;
  isLoading: boolean;
  initialDestination?: string;
}

const VIBES: { value: TravelVibe; label: string; desc: string }[] = [
  { value: "adventure", label: "Adventure", desc: "Thrills & outdoors" },
  { value: "culture", label: "Culture", desc: "History & heritage" },
  { value: "food", label: "Food", desc: "Cuisine & flavors" },
  { value: "relaxation", label: "Relaxation", desc: "Peace & calm" },
  { value: "spiritual", label: "Spiritual", desc: "Temples & faith" },
  { value: "nightlife", label: "Nightlife", desc: "Bars & clubs" },
];

function formatBudgetLabel(value: number): string { return `₹${value.toLocaleString("en-IN")}`; }

export default function TripForm({ onSubmit, isLoading, initialDestination = "" }: TripFormProps) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState(initialDestination);
  const [isOriginSelected, setIsOriginSelected] = useState(false);
  const [isDestinationSelected, setIsDestinationSelected] = useState(Boolean(initialDestination));
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
    if (!origin || !isOriginSelected) newErrors.origin = "Choose an origin from the suggestions";
    if (!destination || !isDestinationSelected) newErrors.destination = "Choose a destination from the suggestions";
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
      className="planner-ticket"
      id="trip-form"
    >
      <div className="planner-main">
      <div className="mb-8">
        <p className="section-eyebrow">Book the plan, not just the ticket</p>
        <h2 className="font-display mt-3 text-5xl text-foreground">Plan your journey</h2>
        <p className="mt-3 max-w-2xl text-sm font-medium leading-6 text-foreground-secondary">Tell us where you&apos;re starting, where you&apos;re headed, and what the trip is for. YatraAI handles the rest.</p>
      </div>

      {/* Origin & Destination */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div className="relative z-20 planner-field">
          <CityAutocomplete
            label="From"
            placeholder="e.g. Delhi"
            value={origin}
            onChange={setOrigin}
            onSelectionChange={setIsOriginSelected}
            id="origin-city"
          />
          {errors.origin && (
            <p className="text-error text-xs mt-1">{errors.origin}</p>
          )}
        </div>
        <div className="relative z-10 planner-field">
          <CityAutocomplete
            label="To"
            placeholder="e.g. Goa"
            value={destination}
            onChange={setDestination}
            onSelectionChange={setIsDestinationSelected}
            id="destination-city"
          />
          {errors.destination && (
            <p className="text-error text-xs mt-1">{errors.destination}</p>
          )}
        </div>
      </div>

      {/* Dates */}
      <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-2">
        <div className="planner-field">
          <label htmlFor="start-date" className="block text-sm font-medium text-foreground-secondary mb-2">
            Depart
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
        <div className="planner-field">
          <label htmlFor="end-date" className="block text-sm font-medium text-foreground-secondary mb-2">
            Return
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
      <div className="planner-budget mt-6">
        <div className="flex items-center justify-between mb-2"><label htmlFor="budget-slider" className="block text-sm font-medium text-foreground-secondary">
          Budget
        </label>
          <span className="text-xl font-bold gradient-text">
            {formatBudgetLabel(budget)}
          </span>
        </div>
        <input
          id="budget-slider"
          type="range"
          min={1000}
          max={100000}
          step={500}
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
          className="w-full cursor-pointer"
        />
      </div>

      {/* Vibe Selector */}
      <div className="planner-vibes mt-7">
        <label className="block text-sm font-medium text-foreground-secondary mb-3">
          Travel Vibe
        </label>
        <div className="flex flex-wrap gap-2">
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
                  planner-vibe transition-all duration-200
                  ${
                    isSelected
                      ? "active"
                      : ""
                  }
                `}
                id={`vibe-${vibe.value}`}
              >
                {vibe.label}
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
          planner-submit transition-all duration-300
          ${
            isLoading
              ? "opacity-50 cursor-not-allowed"
              : ""
          }
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
          "Generate itinerary"
        )}
      </motion.button>
      </div>
      <div className="planner-stub" aria-hidden="true"><span>Boarding · YatraAI · Domestic India</span></div>
    </motion.form>
  );
}
