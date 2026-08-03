"use client";

import { useEffect, useRef, useState } from "react";

interface RouteEntry {
  route: string;
  duration: string;
  fare: string;
  mode: string;
  label: string;
}

// Sample rows only — illustrative of the board mechanic, not live data.
// Real fares come from the trip form below, via the existing transport API.
const ROUTE_SETS: RouteEntry[] = [
  { route: "DEL → GOA", duration: "8h 40m", fare: "₹4,499", mode: "✈ Flight", label: "Sample" },
  { route: "DEL → JAIPUR", duration: "4h 30m", fare: "₹899", mode: "🚆 Train", label: "Train" },
  { route: "BLR → HAMPI", duration: "7h 10m", fare: "₹1,150", mode: "🚆 Train", label: "Budget option" },
  { route: "BLR → GOA", duration: "1h 05m", fare: "₹2,899", mode: "✈ Flight", label: "Flight" },
  { route: "MUM → MANALI", duration: "16h 20m", fare: "₹1,650", mode: "🚆 Train", label: "Sample" },
  { route: "MUM → RISHIKESH", duration: "15h 45m", fare: "₹1,420", mode: "🚆 Train", label: "Train" },
  { route: "HYD → KERALA", duration: "11h 30m", fare: "₹1,890", mode: "🚆 Train", label: "Budget option" },
  { route: "DEL → RISHIKESH", duration: "6h 50m", fare: "₹720", mode: "🚆 Train", label: "Train" },
  { route: "DEL → MANALI", duration: "12h 30m", fare: "₹980", mode: "🚆 Train", label: "Sample" },
  { route: "HYD → GOA", duration: "1h 15m", fare: "₹3,299", mode: "✈ Flight", label: "Flight" },
];

const ROW_COUNT = 5;

export default function DepartureBoard() {
  const [rows, setRows] = useState<RouteEntry[]>(ROUTE_SETS.slice(0, ROW_COUNT));
  const [flippingIdx, setFlippingIdx] = useState<number | null>(null);
  const tickRef = useRef(0);

  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) return;

    let flipTimeout: ReturnType<typeof setTimeout>;

    const interval = setInterval(() => {
      const rowIndex = tickRef.current % ROW_COUNT;
      const nextData = ROUTE_SETS[(tickRef.current + ROW_COUNT) % ROUTE_SETS.length];
      tickRef.current += 1;

      setFlippingIdx(rowIndex);
      flipTimeout = setTimeout(() => {
        setRows((prev) => {
          const next = [...prev];
          next[rowIndex] = nextData;
          return next;
        });
        setFlippingIdx(null);
      }, 220);
    }, 2200);

    return () => {
      clearInterval(interval);
      clearTimeout(flipTimeout);
    };
  }, []);

  return (
    <div className="relative overflow-hidden rounded-md border border-glass-border bg-gradient-to-b from-[#0a0f28] to-surface p-4 sm:p-5 shadow-[0_30px_60px_-20px_rgba(0,0,0,0.6)]">
      <div className="absolute inset-x-0 top-0 h-1 bg-[repeating-linear-gradient(90deg,var(--marigold)_0_14px,var(--background-secondary)_14px_28px)]" />

      <div className="flex items-center justify-between pb-3 mb-2 border-b border-glass-border">
        <span className="font-[family-name:var(--font-space-mono)] text-[11px] uppercase tracking-[0.12em] text-foreground">
          Route board
        </span>
        <span className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-wide text-teal-india flex items-center gap-1.5">
          <span className="board-dot inline-block w-1.5 h-1.5 rounded-full bg-teal-india" />
          Demo preview
        </span>
      </div>

      <div className="hidden sm:grid grid-cols-[1.6fr_0.9fr_0.8fr_0.6fr_0.8fr] gap-2 px-2 pb-2 font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-wide text-foreground-muted">
        <span>Route</span>
        <span>Duration</span>
        <span>Fare</span>
        <span>Mode</span>
        <span>Label</span>
      </div>

      <div>
        {rows.map((row, idx) => (
          <div
            key={idx}
            className={`grid grid-cols-2 sm:grid-cols-[1.6fr_0.9fr_0.8fr_0.6fr_0.8fr] gap-y-1 gap-x-2 items-center px-2 py-3 rounded font-[family-name:var(--font-space-mono)] ${
              idx % 2 === 0 ? "bg-white/[0.02]" : ""
            }`}
          >
            <span className={`flip col-span-2 sm:col-span-1 text-sm sm:text-[15px] text-foreground ${flippingIdx === idx ? "flipping" : ""}`}>
              {row.route}
            </span>
            <span className={`flip text-xs sm:text-sm text-foreground-muted ${flippingIdx === idx ? "flipping" : ""}`}>
              {row.duration}
            </span>
            <span className={`flip text-xs sm:text-sm text-marigold ${flippingIdx === idx ? "flipping" : ""}`}>
              {row.fare}
            </span>
            <span className={`flip text-xs sm:text-sm text-foreground-secondary ${flippingIdx === idx ? "flipping" : ""}`}>
              {row.mode}
            </span>
            <span className={`flip text-[10px] px-2 py-0.5 rounded w-fit bg-glass-highlight text-foreground-secondary ${flippingIdx === idx ? "flipping" : ""}`}>
              {row.label}
            </span>
          </div>
        ))}
      </div>

      <p className="mt-2 pt-3 border-t border-glass-border font-[family-name:var(--font-space-mono)] text-[10px] text-foreground-muted leading-relaxed">
        Sample routes shown for illustration — real fares are estimated per trip you plan below.
      </p>
    </div>
  );
}
