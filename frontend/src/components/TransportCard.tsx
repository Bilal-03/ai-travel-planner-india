"use client";

import { motion } from "framer-motion";
import { TransportOption, formatINR, formatDuration } from "@/lib/api";

interface TransportCardProps {
  option: TransportOption;
  isSelected?: boolean;
  onClick?: () => void;
}

export default function TransportCard({
  option,
  isSelected = false,
  onClick,
}: TransportCardProps) {
  const isFlight = option.mode === "flight";

  return (
    <motion.button
      type="button"
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`
        w-full p-4 rounded-xl border text-left transition-all duration-200 relative
        ${
          isSelected
            ? "border-primary bg-primary/10 shadow-[0_0_20px_rgba(99,102,241,0.15)]"
            : "border-glass-border bg-glass-bg hover:border-glass-highlight"
        }
      `}
    >
      {/* Recommended badge */}
      {option.is_recommended && (
        <span className="absolute -top-2 right-3 px-2 py-0.5 bg-accent text-black text-xs font-bold rounded-full">
          ⭐ Recommended
        </span>
      )}

      {/* Fallback badge */}
      {option.is_fallback && (
        <span className="absolute -top-2 left-3 px-2 py-0.5 bg-glass-highlight text-foreground-muted text-xs rounded-full">
          Estimated
        </span>
      )}

      <div className="flex items-center justify-between">
        {/* Left: mode + provider */}
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg ${
              isFlight ? "bg-flight/15 text-flight" : "bg-train/15 text-train"
            }`}
          >
            {isFlight ? "✈️" : "🚂"}
          </div>
          <div>
            <div className="font-medium text-foreground text-sm">
              {option.provider}
            </div>
            {option.code && (
              <div className="text-foreground-muted text-xs">{option.code}</div>
            )}
          </div>
        </div>

        {/* Right: price */}
        <div className="text-right">
          <div className="font-bold text-lg text-foreground">
            {formatINR(option.price)}
          </div>
          <div className="text-foreground-muted text-xs">per person</div>
        </div>
      </div>

      {/* Bottom: duration + times */}
      <div className="mt-3 flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1 text-foreground-secondary">
          <span>⏱️</span>
          <span>{formatDuration(option.duration_minutes)}</span>
        </div>

        {option.departure_time && option.arrival_time && (
          <div className="flex items-center gap-2 text-foreground-muted text-xs">
            <span>{option.departure_time.length > 5 ? option.departure_time.slice(11, 16) : option.departure_time}</span>
            <span className="text-foreground-muted">→</span>
            <span>{option.arrival_time.length > 5 ? option.arrival_time.slice(11, 16) : option.arrival_time}</span>
          </div>
        )}

        <div className="ml-auto">
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              isFlight
                ? "bg-flight/15 text-flight"
                : "bg-train/15 text-train"
            }`}
          >
            {isFlight ? "Flight" : "Train"}
          </span>
        </div>
      </div>
    </motion.button>
  );
}
