"use client";

import { motion } from "framer-motion";

interface Destination {
  city: string;
  meta: string;
  image: string;
}

const DESTINATIONS: Destination[] = [
  { city: "Goa", meta: "Beaches & sunsets", image: "/destinations/goa.png" },
  { city: "Hampi", meta: "Ancient ruins", image: "/destinations/hampi.png" },
  { city: "Rishikesh", meta: "River & hills", image: "/destinations/rishikesh.png" },
  { city: "Manali", meta: "Mountain escapes", image: "/destinations/manali.png" },
  { city: "Jaipur", meta: "Forts & palaces", image: "/destinations/jaipur.png" },
  { city: "Kerala", meta: "Backwaters & coasts", image: "/destinations/kerala.png" },
  { city: "Varanasi", meta: "Ghats & temples", image: "/destinations/varanasi.png" },
  { city: "Mumbai", meta: "Coast & culture", image: "/destinations/mumbai.png" },
];

export default function DestinationPostcards() {
  return (
    <section id="destinations" style={{ maxWidth: 1180, margin: "0 auto", padding: "clamp(2rem, 5vh, 4rem) 1.75rem clamp(4rem, 10vh, 7rem)" }}>
      <div style={{ marginBottom: "2.5rem" }}>
        <span className="feature-showcase-label">Where people are heading</span>
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
          Eight starting points
        </h2>
        <p style={{ color: "var(--foreground-secondary)", marginTop: "0.75rem", maxWidth: "48ch", fontSize: "1.05rem" }}>
          From backwaters to high passes — a sense of the range YatraAI plans for.
        </p>
      </div>

      <div className="destination-grid">
        {DESTINATIONS.map((d, idx) => (
          <motion.article
            key={d.city}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ delay: idx * 0.06, duration: 0.5 }}
            className="destination-card"
          >
            <img
              src={d.image}
              alt={`${d.city} — ${d.meta}`}
              className="destination-card-image"
              loading="lazy"
            />
            <div className="destination-card-body">
              <div className="destination-card-city">{d.city}</div>
              <div className="destination-card-meta">{d.meta}</div>
            </div>
          </motion.article>
        ))}
      </div>
    </section>
  );
}
