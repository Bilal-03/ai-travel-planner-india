"use client";

import { motion } from "framer-motion";

interface Feature {
  icon: string;
  title: string;
  desc: string;
}

const FEATURES: Feature[] = [
  {
    icon: "🧭",
    title: "Plans grounded in real places",
    desc: "Gemini builds the day-by-day, checked against real points of interest — not invented landmarks.",
  },
  {
    icon: "🚆",
    title: "Flights and trains, side by side",
    desc: "Compare modes on price and time, and see which one YatraAI would actually take.",
  },
  {
    icon: "⛅",
    title: "Built around the weather",
    desc: "Forecasts shape the plan — indoor backups slot in automatically on rainy days.",
  },
  {
    icon: "💰",
    title: "A budget that holds",
    desc: "See transport, stays, food, and activities broken down before you commit to anything.",
  },
  {
    icon: "🗺️",
    title: "Every stop, on the map",
    desc: "Routes and points of interest laid out visually, so the plan is easy to follow on the day.",
  },
  {
    icon: "🔗",
    title: "One link, no sign-up",
    desc: "Share the whole itinerary by link, WhatsApp, or QR code — nobody needs an account.",
  },
];

export default function FeaturesRail() {
  return (
    <section className="px-7 pt-5 pb-[100px]">
      <div className="max-w-[1180px] mx-auto">
        <div className="max-w-[60ch] mb-[56px]">
          <span className="font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-[0.16em] text-marigold">
            How it helps
          </span>
          <h2 className="mt-3 font-[family-name:var(--font-teko)] font-semibold uppercase tracking-wide text-[clamp(2rem,4vw,2.9rem)] text-foreground">
            Everything a trip needs, in one line
          </h2>
          <p className="mt-[14px] font-medium text-foreground-secondary">
            Six things happen every time you generate a plan — not six separate tools to juggle.
          </p>
        </div>

        <div className="relative">
          <div className="hidden min-[900px]:block absolute top-[22px] left-0 right-0 h-[2px] rail-line" />
          <div className="grid grid-cols-1 sm:grid-cols-2 min-[900px]:grid-cols-3 gap-x-[30px] gap-y-10">
            {FEATURES.map((f, idx) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ delay: idx * 0.06, duration: 0.5 }}
                className="relative pt-11 min-[900px]:pt-0"
              >
                <div className="relative z-10 w-11 h-11 rounded-full bg-surface border-2 border-marigold flex items-center justify-center text-xl mb-4">
                  {f.icon}
                </div>
                <h3 className="font-extrabold text-[1.12rem] text-foreground mb-2">{f.title}</h3>
                <p className="text-[0.92rem] font-medium text-foreground-secondary">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
