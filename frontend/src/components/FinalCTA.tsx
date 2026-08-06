"use client";

import HeroSearchBar from "./HeroSearchBar";

interface FinalCTAProps {
  onSearch: (prompt: string) => void;
  isLoading: boolean;
}

export default function FinalCTA({ onSearch, isLoading }: FinalCTAProps) {
  return (
    <section className="final-cta">
      <h2 className="final-cta-headline">Where are you headed?</h2>
      <p
        style={{
          maxWidth: "48ch",
          margin: "1rem auto 0",
          fontSize: "1.05rem",
          color: "var(--foreground-secondary)",
          lineHeight: 1.6,
        }}
      >
        Describe your next Indian adventure. YatraAI will handle the rest.
      </p>
      <HeroSearchBar onSubmit={onSearch} isLoading={isLoading} />
      <p
        style={{
          marginTop: "1.5rem",
          fontSize: "0.82rem",
          color: "var(--foreground-muted)",
        }}
      >
        Free to use · No account required · Powered by Gemini AI
      </p>
    </section>
  );
}
