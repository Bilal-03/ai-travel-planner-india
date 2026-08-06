"use client";

import FeatureShowcase from "./FeatureShowcase";
import { useEffect, useRef } from "react";

const SHOWCASES = [
  {
    label: "AI-Powered Planning",
    title: "Ask anything, get a real plan",
    description:
      "Describe your trip naturally — cities, dates, budget, vibe. Gemini builds a day-by-day itinerary grounded in real points of interest, not invented landmarks.",
    icon: "🤖",
    reversed: false,
  },
  {
    label: "Transport & Stays",
    title: "Flights, trains, and stays — compared",
    description:
      "See real transport options side by side. Compare flights and trains on price and time, and pick the one that fits your plan. Stay estimates help you budget before booking.",
    icon: "🚆",
    reversed: true,
  },
  {
    label: "Budget Intelligence",
    title: "A budget that actually holds",
    description:
      "Transport, stays, food, activities, and a buffer — broken down before you commit. No surprise costs. The budget updates as you refine your plan.",
    icon: "💰",
    reversed: false,
  },
];

const MINI_FEATURES = [
  { icon: "⛅", title: "Weather-aware", desc: "Forecasts shape the plan with indoor backups on rainy days" },
  { icon: "🗺️", title: "Interactive maps", desc: "Routes and POIs laid out visually on OpenStreetMap" },
  { icon: "🔗", title: "One-link sharing", desc: "Share by link, WhatsApp, or QR — no sign-up needed" },
  { icon: "🖨️", title: "Print & PDF", desc: "Print or save your itinerary as a PDF from the browser" },
  { icon: "📱", title: "Offline ready", desc: "Keep recent itineraries available without internet" },
  { icon: "🧳", title: "Packing lists", desc: "Auto-generated weather-aware checklist for your trip" },
];

export default function FeaturesRail() {
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = gridRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("revealed");
          observer.unobserve(el);
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="features">
      {/* Section header */}
      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "clamp(3rem, 8vh, 5rem) 1.75rem 0" }}>
        <span className="feature-showcase-label">How it works</span>
        <h2
          style={{
            fontFamily: "var(--font-playfair, 'Playfair Display', Georgia, serif)",
            fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)",
            fontWeight: 700,
            lineHeight: 1.15,
            color: "var(--foreground)",
            marginTop: "0.5rem",
          }}
        >
          Everything a trip needs, in one place
        </h2>
        <p style={{ color: "var(--foreground-secondary)", marginTop: "0.75rem", maxWidth: "54ch", fontSize: "1.05rem" }}>
          Six things happen every time you generate a plan — not six separate tools to juggle.
        </p>
      </div>

      {/* Alternating showcases */}
      {SHOWCASES.map((showcase) => (
        <FeatureShowcase key={showcase.title} {...showcase} />
      ))}

      {/* Mini feature grid */}
      <div ref={gridRef} className="feature-grid reveal">
        {MINI_FEATURES.map((f) => (
          <div key={f.title} className="feature-grid-item">
            <div className="feature-grid-icon">{f.icon}</div>
            <div>
              <div className="feature-grid-title">{f.title}</div>
              <div className="feature-grid-desc">{f.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
