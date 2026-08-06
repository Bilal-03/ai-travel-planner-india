"use client";

import { useEffect, useRef } from "react";

interface FeatureShowcaseProps {
  label: string;
  title: string;
  description: string;
  icon: string;
  reversed?: boolean;
}

export default function FeatureShowcase({
  label,
  title,
  description,
  icon,
  reversed = false,
}: FeatureShowcaseProps) {
  const sectionRef = useRef<HTMLDivElement>(null);

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
      { threshold: 0.15, rootMargin: "-40px" }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={sectionRef}
      className={`feature-showcase reveal ${reversed ? "reversed" : ""}`}
    >
      <div className="feature-showcase-content">
        <span className="feature-showcase-label">{label}</span>
        <h3 className="feature-showcase-title">{title}</h3>
        <p className="feature-showcase-desc">{description}</p>
      </div>
      <div className="feature-showcase-image" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: "5rem", opacity: 0.6 }}>{icon}</span>
      </div>
    </div>
  );
}
