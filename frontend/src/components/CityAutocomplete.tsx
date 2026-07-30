"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { api, CitySearchResult } from "@/lib/api";

interface CityAutocompleteProps {
  label: string;
  placeholder: string;
  value: string;
  onChange: (city: string) => void;
  onSelectionChange?: (selected: boolean) => void;
  icon: React.ReactNode;
  id: string;
}

export default function CityAutocomplete({
  label,
  placeholder,
  value,
  onChange,
  onSelectionChange,
  icon,
  id,
}: CityAutocompleteProps) {
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState<CitySearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const searchCities = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      return;
    }

    setIsLoading(true);
    try {
      const cities = await api.searchCities(q);
      setResults(cities);
      setIsOpen(cities.length > 0);
      setActiveIndex(-1);
    } catch {
      // Fallback: show nothing on error
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    onChange(val);
    onSelectionChange?.(false);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => searchCities(val), 300);
  };

  const handleSelect = (city: CitySearchResult) => {
    setQuery(city.display_name);
    onChange(city.name);
    onSelectionChange?.(true);
    setIsOpen(false);
    setResults([]);
    setActiveIndex(-1);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" && results.length > 0) {
      event.preventDefault();
      setIsOpen(true);
      setActiveIndex((current) => Math.min(current + 1, results.length - 1));
    } else if (event.key === "ArrowUp" && results.length > 0) {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter" && isOpen && activeIndex >= 0) {
      event.preventDefault();
      handleSelect(results[activeIndex]);
    } else if (event.key === "Escape") {
      setIsOpen(false);
      setActiveIndex(-1);
    }
  };

  return (
    <div ref={wrapperRef} className="relative">
      <label
        htmlFor={id}
        className="block text-sm font-medium text-foreground-secondary mb-2"
      >
        {label}
      </label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted text-lg">
          {icon}
        </span>
        <input
          id={id}
          type="text"
          value={query}
          onChange={handleInputChange}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={isOpen}
          aria-controls={`${id}-results`}
          aria-activedescendant={activeIndex >= 0 ? `${id}-option-${activeIndex}` : undefined}
          className="w-full pl-10 pr-4 py-3 bg-glass-bg border border-glass-border rounded-xl
                     text-foreground placeholder:text-foreground-muted
                     focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30
                     transition-all duration-200"
        />
        {isLoading && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2">
            <svg className="animate-spin h-4 w-4 text-primary" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </span>
        )}
      </div>

      {/* Dropdown */}
      {isOpen && results.length > 0 && (
        <div id={`${id}-results`} role="listbox" className="absolute z-50 w-full mt-2 bg-surface border border-glass-border rounded-xl overflow-hidden shadow-lg animate-slide-up">
          {results.map((city, idx) => (
            <button
              key={`${city.name}-${idx}`}
              id={`${id}-option-${idx}`}
              type="button"
              role="option"
              aria-selected={idx === activeIndex}
              onClick={() => handleSelect(city)}
              onMouseEnter={() => setActiveIndex(idx)}
              className={`w-full px-4 py-3 text-left hover:bg-glass-highlight
                         transition-colors duration-150 flex items-center gap-3
                         border-b border-glass-border last:border-0 ${idx === activeIndex ? "bg-glass-highlight" : ""}`}
            >
              <span className="text-primary">📍</span>
              <div>
                <div className="text-foreground font-medium">{city.name}</div>
                {city.state && (
                  <div className="text-foreground-muted text-xs">{city.state}</div>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
