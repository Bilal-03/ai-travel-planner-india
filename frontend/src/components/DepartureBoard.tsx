"use client";

import { useEffect, useState } from "react";

const ROUTES = [
  { route: "DEL → GOA", mode: "✈ FLIGHT", duration: "8h 40m", fare: "₹4,499", status: "CNFM" },
  { route: "DEL → JAIPUR", mode: "🚆 TRAIN", duration: "4h 30m", fare: "₹899", status: "CNFM" },
  { route: "BLR → HAMPI", mode: "🚆 TRAIN", duration: "7h 10m", fare: "₹1,150", status: "CNFM" },
  { route: "BLR → GOA", mode: "✈ FLIGHT", duration: "1h 05m", fare: "₹2,899", status: "CNFM" },
  { route: "MUM → MANALI", mode: "🚆 TRAIN", duration: "16h 20m", fare: "₹1,650", status: "WL 4" },
  { route: "MUM → RISHIKESH", mode: "🚆 TRAIN", duration: "15h 45m", fare: "₹1,420", status: "CNFM" },
  { route: "HYD → KERALA", mode: "🚆 TRAIN", duration: "11h 30m", fare: "₹1,890", status: "CNFM" },
  { route: "DEL → RISHIKESH", mode: "🚆 TRAIN", duration: "6h 50m", fare: "₹720", status: "CNFM" },
];

export default function DepartureBoard() {
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setOffset((value) => (value + 1) % ROUTES.length), 3200);
    return () => window.clearInterval(timer);
  }, []);
  const rows = Array.from({ length: 5 }, (_, index) => ROUTES[(index + offset) % ROUTES.length]);

  return <section className="board" aria-label="Sample YatraAI trip options">
    <div className="board-head"><span>Route board</span><span className="board-live"><i /> demo preview</span></div>
    <div className="board-labels"><span>Route</span><span>Duration</span><span>Fare</span><span>Mode</span><span>Status</span></div>
    {rows.map((item) => <div className="board-row" key={item.route}>
      <strong>{item.route}</strong><span>{item.duration}</span><b>{item.fare}</b><span>{item.mode}</span><em className={item.status.startsWith("CNFM") ? "cnfm" : "wl"}>{item.status}</em>
    </div>)}
    <p className="board-foot">SAMPLE ROUTES SHOWN FOR ILLUSTRATION — REAL FARES ARE ESTIMATED PER TRIP YOU PLAN.</p>
  </section>;
}
