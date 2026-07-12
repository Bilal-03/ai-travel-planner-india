"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

const STEPS = [
  { icon: "🗺️", label: "Geocoding cities", desc: "Finding coordinates..." },
  { icon: "✈️", label: "Searching flights", desc: "Checking Amadeus for best deals..." },
  { icon: "🚂", label: "Finding trains", desc: "Looking up train routes..." },
  { icon: "📍", label: "Discovering places", desc: "Scanning OpenStreetMap for POIs..." },
  { icon: "🌤️", label: "Checking weather", desc: "Getting forecasts for your dates..." },
  { icon: "🤖", label: "AI planning", desc: "Gemini is crafting your itinerary..." },
  { icon: "✅", label: "Validating plan", desc: "Checking budget & feasibility..." },
  { icon: "🗺️", label: "Computing routes", desc: "Mapping your daily routes..." },
];

export default function LoadingState() {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const progress = ((currentStep + 1) / STEPS.length) * 100;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass gradient-border p-8 rounded-2xl max-w-lg mx-auto text-center"
    >
      {/* Animated Travel Icon */}
      <motion.div
        className="text-6xl mb-6"
        animate={{ y: [0, -12, 0] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        {STEPS[currentStep].icon}
      </motion.div>

      {/* Progress Bar */}
      <div className="w-full h-2 bg-glass-bg rounded-full overflow-hidden mb-6">
        <motion.div
          className="h-full bg-gradient-to-r from-primary to-accent rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>

      {/* Step Info */}
      <motion.div
        key={currentStep}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h3 className="text-xl font-bold font-[family-name:var(--font-outfit)] text-foreground mb-1">
          {STEPS[currentStep].label}
        </h3>
        <p className="text-foreground-muted text-sm">
          {STEPS[currentStep].desc}
        </p>
      </motion.div>

      {/* Step Dots */}
      <div className="flex justify-center gap-2 mt-6">
        {STEPS.map((_, idx) => (
          <motion.div
            key={idx}
            className={`w-2 h-2 rounded-full transition-colors duration-300 ${
              idx <= currentStep ? "bg-primary" : "bg-glass-highlight"
            }`}
            animate={idx === currentStep ? { scale: [1, 1.3, 1] } : {}}
            transition={{ duration: 0.6, repeat: Infinity }}
          />
        ))}
      </div>

      <p className="text-foreground-muted text-xs mt-4">
        This usually takes 15–30 seconds
      </p>
    </motion.div>
  );
}
