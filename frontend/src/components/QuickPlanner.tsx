"use client";

import { FormEvent, useMemo, useState } from "react";
import { TripRequest, TravelVibe, TripPace } from "@/lib/api";

interface QuickPlannerProps {
  onReview: (draft: Partial<TripRequest>, prompt: string) => void;
  isLoading: boolean;
}

interface QuickBrief {
  draft: Partial<TripRequest>;
  originLabel: string;
  destinationLabel: string;
  dateLabel: string;
  travellerLabel: string;
  budgetLabel: string;
  confidence: "ready" | "needs-origin";
}

const EXAMPLE_PROMPTS = [
  "Plan a five-day budget trip from Delhi to Manali.",
  "Create a relaxing Goa trip for a couple.",
  "Plan a senior-friendly pilgrimage to Varanasi.",
  "Suggest a weekend road trip from Bengaluru.",
  "Plan a family trip to Jaipur under ₹40,000.",
];

const CITY_NAMES = [
  "Bengaluru",
  "Varanasi",
  "Rishikesh",
  "Jaisalmer",
  "Ahmedabad",
  "Hyderabad",
  "Amritsar",
  "Chennai",
  "Kolkata",
  "Mumbai",
  "Mysuru",
  "Udaipur",
  "Manali",
  "Jaipur",
  "Shimla",
  "Agra",
  "Kochi",
  "Delhi",
  "Goa",
  "Pune",
];

function normalize(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
}

function findCity(value: string): string | undefined {
  const normalized = normalize(value);
  return CITY_NAMES.find((city) => normalized.includes(normalize(city)));
}

function futureDate(daysFromNow: number): string {
  const date = new Date();
  date.setHours(12, 0, 0, 0);
  date.setDate(date.getDate() + daysFromNow);
  return date.toISOString().slice(0, 10);
}

function parseVibes(text: string): TravelVibe[] {
  const normalized = normalize(text);
  const vibes: TravelVibe[] = [];
  const add = (vibe: TravelVibe, ...keywords: string[]) => {
    if (keywords.some((keyword) => normalized.includes(keyword)) && !vibes.includes(vibe)) vibes.push(vibe);
  };
  add("relaxation", "relax", "slow", "peace", "beach");
  add("spiritual", "pilgrimage", "temple", "spiritual", "faith");
  add("adventure", "road trip", "trek", "adventure", "outdoor");
  add("food", "food", "culinary");
  add("culture", "culture", "heritage", "history");
  return vibes.length ? vibes : ["culture"];
}

function parseQuickBrief(prompt: string): QuickBrief {
  const normalized = normalize(prompt);
  const explicitRoute = normalized.match(/from (.+?) to (.+?)(?:\.|,| for | under | with |$)/);
  const explicitOrigin = explicitRoute ? findCity(explicitRoute[1]) : findCity(normalized.match(/from (.+?)(?:\.|,| to | for | under | with |$)/)?.[1] || "");
  const explicitDestination = explicitRoute ? findCity(explicitRoute[2]) : undefined;
  const mentionedCities = CITY_NAMES.filter((city) => normalized.includes(normalize(city)));
  const destination = explicitDestination
    || (normalized.includes("to ") ? findCity(normalized.split("to ")[1]) : undefined)
    || mentionedCities.find((city) => city !== explicitOrigin)
    || "";
  const origin = explicitOrigin || "";

  const dayMatch = normalized.match(/(\d+)\s*[- ]?day/);
  const days = Math.min(Math.max(Number(dayMatch?.[1] || (normalized.includes("weekend") ? 2 : 4)), 2), 14);
  const startDate = futureDate(21);
  const end = new Date(`${startDate}T12:00:00`);
  end.setDate(end.getDate() + days - 1);
  const endDate = end.toISOString().slice(0, 10);

  const budgetMatch = normalized.match(/(?:under|below|budget(?: of)?|₹)\s*([\d,]+)/);
  const parsedBudget = budgetMatch ? Number(budgetMatch[1].replace(/,/g, "")) : 15000;
  const adults = normalized.includes("couple") ? 2 : Number(normalized.match(/(\d+)\s*(?:people|travellers|adults)/)?.[1] || 2);
  const children = normalized.includes("family") ? 2 : 0;
  const seniorCitizens = normalized.includes("senior") ? 1 : 0;
  const pace: TripPace = normalized.includes("relax") || normalized.includes("senior") ? "relaxed" : "balanced";
  const vibes = parseVibes(normalized);

  const draft: Partial<TripRequest> = {
    origin: origin || undefined,
    destination: destination || undefined,
    start_date: startDate,
    end_date: endDate,
    budget: Math.max(parsedBudget, (adults + children) * 1500),
    adults: Math.max(1, Math.min(adults, 20)),
    children,
    senior_citizens: Math.min(seniorCitizens, Math.max(1, adults)),
    vibes,
    pace,
    travel_preference: normalized.includes("cheapest") || normalized.includes("budget") ? "cheapest" : "balanced",
    transport_mode: normalized.includes("road trip") ? "road" : undefined,
    free_text_notes: prompt.trim(),
  };

  return {
    draft,
    originLabel: origin || "Choose a starting city",
    destinationLabel: destination || "Choose a destination",
    dateLabel: `${days} days · ${new Date(`${startDate}T12:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}`,
    travellerLabel: `${adults + children} traveller${adults + children === 1 ? "" : "s"}${seniorCitizens ? " · senior-friendly" : ""}`,
    budgetLabel: `₹${Math.max(parsedBudget, (adults + children) * 1500).toLocaleString("en-IN")}`,
    confidence: origin ? "ready" : "needs-origin",
  };
}

export default function QuickPlanner({ onReview, isLoading }: QuickPlannerProps) {
  const [prompt, setPrompt] = useState("");
  const brief = useMemo(() => (prompt.trim().length >= 3 ? parseQuickBrief(prompt) : null), [prompt]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (brief) onReview(brief.draft, prompt.trim());
  };

  return (
    <section className="mx-auto mb-8 max-w-[1180px] rounded-[10px] border border-marigold/30 bg-[linear-gradient(120deg,rgba(196,82,43,0.18),rgba(28,128,121,0.12))] p-5 shadow-[0_24px_60px_-36px_rgba(242,169,59,0.55)] sm:p-7" aria-labelledby="quick-plan-heading">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(260px,0.72fr)] lg:items-end">
        <div>
          <div className="flex items-center gap-2 font-[family-name:var(--font-space-mono)] text-[11px] uppercase tracking-[0.16em] text-marigold">
            <span className="h-2 w-2 rounded-full bg-marigold" aria-hidden="true" /> Quick planning
          </div>
          <h2 id="quick-plan-heading" className="mt-2 font-[family-name:var(--font-teko)] text-[clamp(2rem,4vw,3rem)] font-semibold uppercase leading-none text-foreground">
            Start with a sentence.
          </h2>
          <p className="mt-2 max-w-[58ch] text-sm font-medium text-foreground-secondary">
            Describe the trip in your own words. YatraAI will pull out a starting brief, then show the detailed planner so you can review every assumption before generating.
          </p>
          <form onSubmit={submit} className="mt-5 flex flex-col gap-2 sm:flex-row">
            <label htmlFor="quick-plan-prompt" className="sr-only">Describe your trip</label>
            <input
              id="quick-plan-prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="e.g. Plan five relaxed days from Delhi to Goa under ₹30,000"
              className="min-w-0 flex-1 rounded-[3px] border border-glass-border bg-black/25 px-4 py-3 text-sm font-medium text-foreground outline-none transition-colors placeholder:text-foreground-muted focus:border-marigold focus:ring-1 focus:ring-marigold/40"
              maxLength={500}
            />
            <button type="submit" disabled={!brief || isLoading} className="rounded-[3px] bg-marigold px-5 py-3 font-[family-name:var(--font-space-mono)] text-xs font-bold uppercase tracking-wide text-[#24160a] transition hover:shadow-[0_6px_24px_rgba(242,169,59,0.3)] disabled:cursor-not-allowed disabled:opacity-50">
              Review brief
            </button>
          </form>
          <div className="mt-3 flex flex-wrap gap-2" aria-label="Suggested prompts">
            {EXAMPLE_PROMPTS.map((example) => (
              <button key={example} type="button" onClick={() => setPrompt(example)} className="rounded-full border border-glass-border bg-black/10 px-3 py-1.5 text-left text-[11px] text-foreground-secondary transition hover:border-marigold hover:text-foreground">
                {example}
              </button>
            ))}
          </div>
        </div>

        <div className="min-h-[170px] rounded-[6px] border border-glass-border bg-background/45 p-4" aria-live="polite">
          {brief ? (
            <>
              <div className="flex items-center justify-between gap-3">
                <span className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-foreground-muted">Extracted starting brief</span>
                <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${brief.confidence === "ready" ? "bg-success/15 text-success" : "bg-warning/15 text-warning"}`}>
                  {brief.confidence === "ready" ? "Ready to review" : "Origin needed"}
                </span>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
                <div><dt className="text-foreground-muted">Route</dt><dd className="mt-0.5 font-semibold text-foreground">{brief.originLabel} → {brief.destinationLabel}</dd></div>
                <div><dt className="text-foreground-muted">Dates</dt><dd className="mt-0.5 font-semibold text-foreground">{brief.dateLabel}</dd></div>
                <div><dt className="text-foreground-muted">Travellers</dt><dd className="mt-0.5 font-semibold text-foreground">{brief.travellerLabel}</dd></div>
                <div><dt className="text-foreground-muted">Working budget</dt><dd className="mt-0.5 font-semibold text-foreground">{brief.budgetLabel}</dd></div>
              </dl>
              <p className="mt-4 text-[11px] leading-relaxed text-foreground-muted">Review the highlighted fields below before you ask YatraAI to generate the itinerary.</p>
            </>
          ) : (
            <div className="flex h-full flex-col justify-center">
              <span className="text-2xl" aria-hidden="true">✍️</span>
              <p className="mt-2 text-sm font-semibold text-foreground">Your trip brief will appear here.</p>
              <p className="mt-1 text-xs text-foreground-muted">Try one of the suggested prompts or write your own.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
