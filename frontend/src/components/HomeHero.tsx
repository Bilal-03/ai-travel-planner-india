"use client";

import { motion } from "framer-motion";
import HeroSearchBar from "./HeroSearchBar";

interface HomeHeroProps {
  onSearch: (prompt: string) => void;
  isLoading: boolean;
}

export default function HomeHero({ onSearch, isLoading }: HomeHeroProps) {
  return (
    <section id="plan" className="hero-section gradient-hero">
      {/* Floating postcard images */}
      <img
        src="/destinations/jaipur.png"
        alt=""
        className="hero-float-image animate-float-slow hidden lg:block"
        style={{ width: 140, height: 100, top: "18%", left: "5%", transform: "rotate(-6deg)" }}
        aria-hidden="true"
      />
      <img
        src="/destinations/goa.png"
        alt=""
        className="hero-float-image animate-float hidden lg:block"
        style={{ width: 120, height: 85, top: "28%", right: "6%", transform: "rotate(4deg)", animationDelay: "1s" }}
        aria-hidden="true"
      />
      <img
        src="/destinations/kerala.png"
        alt=""
        className="hero-float-image animate-float-slow hidden xl:block"
        style={{ width: 110, height: 78, bottom: "18%", left: "8%", transform: "rotate(3deg)", animationDelay: "2s" }}
        aria-hidden="true"
      />
      <img
        src="/destinations/varanasi.png"
        alt=""
        className="hero-float-image animate-float hidden xl:block"
        style={{ width: 130, height: 92, bottom: "22%", right: "4%", transform: "rotate(-4deg)", animationDelay: "0.5s" }}
        aria-hidden="true"
      />

      {/* Main hero content */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
        style={{ position: "relative", zIndex: 1 }}
      >
        <h1 className="hero-headline text-balance">
          Plan your next{" "}
          <span className="gradient-text">Indian adventure</span>
        </h1>

        <p className="hero-subtitle text-balance">
          Describe your trip in one sentence. YatraAI plans the routes, stays,
          food, and budget — grounded in real places, not a generic listicle.
        </p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <HeroSearchBar onSubmit={onSearch} isLoading={isLoading} />
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          style={{
            marginTop: "1.5rem",
            fontSize: "0.82rem",
            fontWeight: 500,
            color: "var(--foreground-muted)",
            letterSpacing: "0.02em",
          }}
        >
          No sign-up · Free to plan · Built for domestic India travel
        </motion.p>
      </motion.div>
    </section>
  );
}
