"use client";

import { useEffect, useRef, useState } from "react";

interface HeroSearchBarProps {
  onSubmit: (prompt: string) => void;
  isLoading: boolean;
}

const EXAMPLE_PROMPTS = [
  "Plan five days from Delhi to Manali for two…",
  "A relaxed Goa trip for a couple in November…",
  "Three-day heritage trip from Mumbai to Jaipur…",
  "Weekend road trip from Bengaluru to Coorg…",
  "Five days in Rajasthan under ₹25,000…",
  "Kerala backwaters for a family of four…",
];

export default function HeroSearchBar({ onSubmit, isLoading }: HeroSearchBarProps) {
  const [prompt, setPrompt] = useState("");
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [displayedPlaceholder, setDisplayedPlaceholder] = useState("");
  const [isTyping, setIsTyping] = useState(true);
  const charIndexRef = useRef(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Typing animation for placeholder
  useEffect(() => {
    if (prompt.length > 0) return; // Stop animation when user types

    const currentPrompt = EXAMPLE_PROMPTS[placeholderIndex];
    let timeout: ReturnType<typeof setTimeout>;

    if (isTyping) {
      if (charIndexRef.current <= currentPrompt.length) {
        timeout = setTimeout(() => {
          setDisplayedPlaceholder(currentPrompt.slice(0, charIndexRef.current));
          charIndexRef.current++;
        }, 45);
      } else {
        // Pause at full text
        timeout = setTimeout(() => {
          setIsTyping(false);
        }, 2200);
      }
    } else {
      // Delete animation
      if (charIndexRef.current > 0) {
        timeout = setTimeout(() => {
          charIndexRef.current--;
          setDisplayedPlaceholder(currentPrompt.slice(0, charIndexRef.current));
        }, 20);
      } else {
        // Move to next prompt
        setPlaceholderIndex((prev) => (prev + 1) % EXAMPLE_PROMPTS.length);
        setIsTyping(true);
      }
    }

    return () => clearTimeout(timeout);
  }, [displayedPlaceholder, isTyping, placeholderIndex, prompt.length]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim().length >= 3 && !isLoading) {
      onSubmit(prompt.trim());
    }
  };

  return (
    <div className="hero-search-wrapper">
      <form onSubmit={handleSubmit} className="hero-search-bar">
        <input
          ref={inputRef}
          id="hero-search-input"
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={displayedPlaceholder || "Describe your dream trip…"}
          className="hero-search-input"
          maxLength={2000}
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={prompt.trim().length < 3 || isLoading}
          className="hero-search-button"
        >
          {isLoading ? "Planning…" : "Explore"}
          {!isLoading && (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </button>
      </form>
    </div>
  );
}
