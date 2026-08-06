"use client";

import { useEffect, useState } from "react";

interface HeaderProps {
  onLogoClick?: () => void;
}

export default function Header({ onLogoClick }: HeaderProps) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header
      className="sticky top-0 z-50 transition-all duration-300"
      style={{
        background: scrolled ? "rgba(250, 247, 242, 0.88)" : "transparent",
        backdropFilter: scrolled ? "blur(16px)" : "none",
        WebkitBackdropFilter: scrolled ? "blur(16px)" : "none",
        borderBottom: scrolled ? "1px solid rgba(0,0,0,0.06)" : "1px solid transparent",
        boxShadow: scrolled ? "0 1px 8px rgba(0,0,0,0.04)" : "none",
      }}
    >
      <div className="max-w-[1180px] mx-auto flex items-center justify-between px-7 py-4">
        {/* Logo */}
        <button
          onClick={onLogoClick}
          type="button"
          className="flex items-center gap-2"
        >
          <span
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "linear-gradient(135deg, var(--rust), var(--marigold))",
              color: "white",
              fontSize: "0.85rem",
              fontWeight: 700,
            }}
          >
            ✦
          </span>
          <span
            style={{
              fontFamily: "var(--font-playfair, 'Playfair Display', Georgia, serif)",
              fontWeight: 700,
              fontSize: "1.35rem",
              color: "var(--foreground)",
            }}
          >
            Yatra<span style={{ color: "var(--marigold)" }}>AI</span>
          </span>
        </button>

        {/* Nav links */}
        <nav className="hidden sm:flex items-center gap-8">
          <a
            href="#features"
            className="text-sm font-medium transition-colors"
            style={{ color: "var(--foreground-secondary)" }}
            onMouseOver={(e) => (e.currentTarget.style.color = "var(--foreground)")}
            onMouseOut={(e) => (e.currentTarget.style.color = "var(--foreground-secondary)")}
          >
            How it works
          </a>
          <a
            href="#destinations"
            className="text-sm font-medium transition-colors"
            style={{ color: "var(--foreground-secondary)" }}
            onMouseOver={(e) => (e.currentTarget.style.color = "var(--foreground)")}
            onMouseOut={(e) => (e.currentTarget.style.color = "var(--foreground-secondary)")}
          >
            Destinations
          </a>
        </nav>

        {/* CTA */}
        <a
          href="#plan"
          className="hero-search-button"
          style={{ padding: "0.6rem 1.2rem", fontSize: "0.85rem" }}
        >
          Plan a trip
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </a>
      </div>
    </header>
  );
}
