"use client";

import { motion } from "framer-motion";
import DepartureBoard from "./DepartureBoard";

export default function HomeHero() {
  return (
    <section className="px-7 pt-[76px] pb-[60px]">
      <div className="max-w-[1180px] mx-auto grid grid-cols-1 lg:grid-cols-[1.05fr_0.95fr] gap-10 items-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="font-[family-name:var(--font-space-mono)] text-[0.72rem] uppercase tracking-[0.16em] text-marigold">
            India, end to end
          </span>

          <h1 className="mt-[14px] font-[family-name:var(--font-teko)] font-semibold uppercase leading-[0.95] text-[clamp(3.2rem,8.4vw,6.2rem)] text-foreground">
            <span className="block">Namaste.</span>
            <span className="block">Where are we</span>
            <span className="block text-marigold">heading today?</span>
          </h1>

          <p className="mt-[22px] max-w-[46ch] text-[clamp(1rem,1.6vw,1.15rem)] font-medium text-foreground-secondary">
            Give YatraAI your cities and dates. It plans the routes, the stays, the food, and a
            budget that actually adds up — grounded in real places, not a generic listicle.
          </p>

          <div className="mt-8 flex flex-wrap gap-[14px]">
            <a
              href="#plan"
              className="font-[family-name:var(--font-space-mono)] text-[0.78rem] uppercase tracking-[0.06em] px-[26px] py-[15px] rounded-[3px] bg-marigold text-[#24160a] hover:shadow-[0_6px_24px_rgba(242,169,59,0.28)] transition-shadow duration-200"
            >
              Plan my journey
            </a>
            <a
              href="#destinations"
              className="font-[family-name:var(--font-space-mono)] text-[0.78rem] uppercase tracking-[0.06em] px-[26px] py-[15px] rounded-[3px] border border-white/25 text-foreground hover:border-foreground transition-colors duration-200"
            >
              See where people go
            </a>
          </div>

          <p className="mt-[18px] font-[family-name:var(--font-space-mono)] text-[0.7rem] text-foreground-muted tracking-[0.04em]">
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
