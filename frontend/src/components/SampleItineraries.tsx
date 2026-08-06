"use client";

import { useEffect, useRef } from "react";

interface SampleTrip {
  title: string;
  image: string;
  duration: string;
  budget: string;
  tags: string[];
}

const SAMPLE_TRIPS: SampleTrip[] = [
  {
    title: "Golden Triangle Heritage Tour",
    image: "/destinations/jaipur.png",
    duration: "5 days",
    budget: "₹18,000 – ₹25,000",
    tags: ["Heritage", "Culture"],
  },
  {
    title: "Kerala Backwater Retreat",
    image: "/destinations/kerala.png",
    duration: "4 days",
    budget: "₹22,000 – ₹30,000",
    tags: ["Nature", "Relaxation"],
  },
  {
    title: "Himalayan Adventure in Manali",
    image: "/destinations/manali.png",
    duration: "6 days",
    budget: "₹15,000 – ₹22,000",
    tags: ["Adventure", "Mountains"],
  },
];

export default function SampleItineraries() {
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = sectionRef.current;
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
    <section
      ref={sectionRef}
      className="reveal"
      style={{ maxWidth: 1180, margin: "0 auto", padding: "clamp(3rem, 8vh, 6rem) 1.75rem" }}
    >
      <div style={{ marginBottom: "2.5rem" }}>
        <span className="feature-showcase-label">Popular trips</span>
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
          Trips travelers love
        </h2>
        <p style={{ color: "var(--foreground-secondary)", marginTop: "0.75rem", maxWidth: "48ch", fontSize: "1.05rem" }}>
          Get inspired by these popular itineraries — or describe your own and let YatraAI plan it for you.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem" }}>
        {SAMPLE_TRIPS.map((trip) => (
          <article key={trip.title} className="sample-card">
            <img
              src={trip.image}
              alt={trip.title}
              className="sample-card-image"
              loading="lazy"
            />
            <div className="sample-card-body">
              <h3 className="sample-card-title">{trip.title}</h3>
              <div className="sample-card-meta">
                <span>📅 {trip.duration}</span>
                <span>💰 {trip.budget}</span>
              </div>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
                {trip.tags.map((tag) => (
                  <span key={tag} className="sample-card-tag">{tag}</span>
                ))}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
