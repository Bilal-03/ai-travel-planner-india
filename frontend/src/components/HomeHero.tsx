"use client";

import { motion } from "framer-motion";
import DepartureBoard from "./DepartureBoard";

export default function HomeHero() {
  return (
    <section className="gradient-hero px-4 pt-16 pb-10 md:pt-24 md:pb-16">
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-[1.05fr_0.95fr] gap-10 lg:gap-14 items-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="flex items-center gap-2 mb-4">
            <span className="text-3xl">✈️</span>
            <span className="font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-[0.16em] text-marigold">
              India, end to end
            </span>
          </div>

          <h1 className="font-[family-name:var(--font-teko)] font-semibold uppercase leading-[0.92] text-5xl sm:text-6xl md:text-7xl text-foreground">
            <span className="block">Namaste.</span>
            <span className="block">Where are we</span>
            <span className="block text-marigold">heading today?</span>
          </h1>

          <p className="mt-6 max-w-md text-lg text-foreground-secondary text-balance">
            Give YatraAI your cities and dates. It plans the routes, the stays, the food, and a
            budget that actually adds up — grounded in real places, not a generic listicle.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="#trip-form"
              className="font-[family-name:var(--font-space-mono)] text-sm uppercase tracking-wide px-7 py-4 rounded-[3px] bg-marigold text-[#24160a] font-bold hover:shadow-[0_6px_24px_rgba(242,169,59,0.28)] transition-shadow duration-200"
            >
              Plan my journey
            </a>
            <a
              href="#destinations"
              className="font-[family-name:var(--font-space-mono)] text-sm uppercase tracking-wide px-7 py-4 rounded-[3px] border border-glass-border text-foreground hover:border-foreground transition-colors duration-200"
            >
              See where people go
            </a>
          </div>

          <p className="mt-4 font-[family-name:var(--font-space-mono)] text-xs text-foreground-muted tracking-wide">
            No sign-up · Free to plan · Built for domestic India travel
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
        >
          <DepartureBoard />
        </motion.div>
      </div>
    </section>
  );
}
