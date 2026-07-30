"use client";

import { useEffect, useRef, useState } from "react";

type Route = { route: string; mode: string; duration: string; fare: string; status: string; cls: "cnfm" | "wl" };
const ROUTES: Route[] = [
  { route: "DEL → GOA", mode: "✈ Flight", duration: "8h 40m", fare: "₹4,499", status: "CNFM", cls: "cnfm" }, { route: "DEL → JAIPUR", mode: "🚆 Train", duration: "4h 30m", fare: "₹899", status: "CNFM", cls: "cnfm" }, { route: "BLR → HAMPI", mode: "🚆 Train", duration: "7h 10m", fare: "₹1,150", status: "CNFM", cls: "cnfm" }, { route: "BLR → GOA", mode: "✈ Flight", duration: "1h 05m", fare: "₹2,899", status: "CNFM", cls: "cnfm" }, { route: "MUM → MANALI", mode: "🚆 Train", duration: "16h 20m", fare: "₹1,650", status: "WL 4", cls: "wl" }, { route: "MUM → RISHIKESH", mode: "🚆 Train", duration: "15h 45m", fare: "₹1,420", status: "CNFM", cls: "cnfm" }, { route: "HYD → KERALA", mode: "🚆 Train", duration: "11h 30m", fare: "₹1,890", status: "CNFM", cls: "cnfm" }, { route: "DEL → RISHIKESH", mode: "🚆 Train", duration: "6h 50m", fare: "₹720", status: "CNFM", cls: "cnfm" }, { route: "DEL → MANALI", mode: "🚆 Train", duration: "12h 30m", fare: "₹980", status: "RAC 2", cls: "wl" }, { route: "HYD → GOA", mode: "✈ Flight", duration: "1h 15m", fare: "₹3,299", status: "CNFM", cls: "cnfm" },
];
const ROW_COUNT = 5;

export default function DepartureBoard() {
  const [rows, setRows] = useState<Route[]>(() => ROUTES.slice(0, ROW_COUNT));
  const [flippingIndex, setFlippingIndex] = useState<number | null>(null);
  const tickRef = useRef(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const interval = window.setInterval(() => { const tick = tickRef.current; const rowIndex = tick % ROW_COUNT; setFlippingIndex(rowIndex); window.setTimeout(() => { setRows((previous) => { const next = [...previous]; next[rowIndex] = ROUTES[(tick + ROW_COUNT) % ROUTES.length]; return next; }); setFlippingIndex(null); }, 220); tickRef.current += 1; }, 2200);
    return () => window.clearInterval(interval);
  }, []);

  return <section className="board" aria-label="Sample YatraAI trip options">
    <div className="board-head"><span>Route board</span><span className="board-live"><i />Demo preview</span></div>
    <div className="board-labels"><span>Route</span><span>Duration</span><span>Fare</span><span>Mode</span><span>Status</span></div>
    {rows.map((item, index) => <div className={`board-row${flippingIndex === index ? " flipping" : ""}`} key={index}>
      <strong><span className="flip">{item.route}</span></strong><span><span className="flip">{item.duration}</span></span><b><span className="flip">{item.fare}</span></b><span><span className="flip">{item.mode}</span></span><em className={item.cls}><span className="flip">{item.status}</span></em>
    </div>)}
    <p className="board-foot">SAMPLE ROUTES SHOWN FOR ILLUSTRATION — REAL FARES ARE ESTIMATED PER TRIP YOU PLAN.</p>
  </section>;
}
