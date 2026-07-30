"use client";

import { useEffect, useState } from "react";

const ROUTES = [
  { route: "DEL → JAI", mode: "TRAIN", duration: "4h 20m", fare: "₹ 820", status: "CNFM" },
  { route: "BOM → GOI", mode: "FLIGHT", duration: "1h 15m", fare: "₹ 2,890", status: "CNFM" },
  { route: "BLR → KOC", mode: "TRAIN", duration: "9h 10m", fare: "₹ 1,140", status: "WL 12" },
];

export default function DepartureBoard() {
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setOffset((value) => (value + 1) % ROUTES.length), 3200);
    return () => window.clearInterval(timer);
  }, []);
  const rows = ROUTES.map((_, index) => ROUTES[(index + offset) % ROUTES.length]);

  return <section className="board" aria-label="Sample YatraAI trip options">
    <div className="board-head"><span>YatraAI departure board</span><span className="board-live"><i /> live preview</span></div>
    <div className="board-labels"><span>Route</span><span>Mode</span><span>Duration</span><span>Fare</span><span>Status</span></div>
    {rows.map((item) => <div className="board-row" key={item.route}>
      <strong>{item.route}</strong><span>{item.mode}</span><span>{item.duration}</span><b>{item.fare}</b><em className={item.status.startsWith("CNFM") ? "cnfm" : "wl"}>{item.status}</em>
    </div>)}
    <p className="board-foot">FARES ARE ESTIMATES · LIVE PROVIDER CHECKS AVAILABLE</p>
  </section>;
}
