"use client";

import { useState } from "react";
import { Itinerary } from "@/lib/api";
import { track } from "@/lib/analytics";

interface TripUpdateProps {
  itinerary: Itinerary;
  onUpdate: (itinerary: Itinerary) => void;
}

export function RefineItineraryAction({ itinerary, onUpdate }: TripUpdateProps) {
  const [instruction, setInstruction] = useState("");
  const [isRefining, setIsRefining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refine = async (event: React.FormEvent) => {
    event.preventDefault();
    if (instruction.trim().length < 3) return;
    setIsRefining(true);
    setError(null);
    try {
      const { api } = await import("@/lib/api");
      onUpdate(await api.refineTrip(itinerary.id, instruction.trim()));
      setInstruction("");
    } catch {
      setError("Couldn’t refine this itinerary. Please try again.");
    } finally {
      setIsRefining(false);
    }
  };

  return (
    <details className="relative print:hidden">
      <summary className="cursor-pointer list-none rounded-lg border border-primary/50 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/10">
        ✨ Refine
      </summary>
      <form onSubmit={refine} className="absolute right-0 top-11 z-20 w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-glass-border bg-background p-3 shadow-xl">
        <label className="block text-xs text-foreground-muted">Tell YatraAI what to change</label>
        <div className="mt-2 flex gap-2">
          <input value={instruction} onChange={(event) => setInstruction(event.target.value)} maxLength={500} placeholder="Make day 3 cheaper" className="min-w-0 flex-1 rounded-lg border border-glass-border bg-glass-bg px-3 py-2 text-sm text-foreground outline-none focus:border-primary" />
          <button disabled={isRefining || instruction.trim().length < 3} className="warm-button rounded-lg px-3 py-2 text-sm font-medium text-white disabled:opacity-50">{isRefining ? "…" : "Apply"}</button>
        </div>
        {error && <p className="mt-2 text-xs text-error">{error}</p>}
      </form>
    </details>
  );
}

export function StaySuggestions({ itinerary }: Pick<TripUpdateProps, "itinerary">) {
  const hotelSearch = `https://www.google.com/travel/search?q=${encodeURIComponent(`Hotels in ${itinerary.destination.name} ${itinerary.start_date} ${itinerary.end_date}`)}`;
  const bookingSearch = `https://www.booking.com/searchresults.html?${new URLSearchParams({ ss: `${itinerary.destination.name}, India`, checkin: itinerary.start_date, checkout: itinerary.end_date }).toString()}`;

  return (
    <section className="rounded-xl border border-glass-border bg-glass-bg p-4">
      <h3 className="font-semibold text-foreground">🏨 Stay suggestions</h3>
      <p className="mt-1 text-xs text-foreground-muted">Compare accommodation for your dates and chosen hotel level.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <a href={hotelSearch} target="_blank" rel="noreferrer" onClick={() => track("provider_link_clicked", { tripId: itinerary.id, kind: "single", metadata: { provider: "google_hotels" } })} className="rounded-lg border border-primary/50 px-3 py-2 text-xs font-medium text-primary">Google Hotels ↗</a>
        <a href={bookingSearch} target="_blank" rel="noreferrer" onClick={() => track("provider_link_clicked", { tripId: itinerary.id, kind: "single", metadata: { provider: "booking" } })} className="rounded-lg border border-primary/50 px-3 py-2 text-xs font-medium text-primary">Booking.com ↗</a>
      </div>
      {itinerary.destination_photos[0] && (
        <figure className="destination-frame relative mt-4 h-44 overflow-hidden rounded-xl bg-surface">
          {/* Destination providers return dynamic remote URLs; using a plain image avoids an unsafe allowlist bypass. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={itinerary.destination_photos[0].url} alt={itinerary.destination_photos[0].alt} className="h-full w-full object-cover" />
          <figcaption className="absolute inset-x-0 bottom-0 bg-black/55 px-3 py-2 text-xs text-white">
            {itinerary.destination_photos[0].photographer_url ? <a className="underline" href={itinerary.destination_photos[0].photographer_url} target="_blank" rel="noreferrer">Photo by {itinerary.destination_photos[0].photographer_name || "Unsplash"} on Unsplash</a> : "Destination inspiration"}
          </figcaption>
        </figure>
      )}
    </section>
  );
}

export function PackingAndPrint({ itinerary, onUpdate }: TripUpdateProps) {
  const [isPacking, setIsPacking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createPackingList = async () => {
    setIsPacking(true);
    setError(null);
    try {
      const { api } = await import("@/lib/api");
      const packing_list = await api.generatePackingList(itinerary.id);
      onUpdate({ ...itinerary, packing_list });
    } catch {
      setError("Couldn’t create the packing list. Please try again.");
    } finally {
      setIsPacking(false);
    }
  };

  return (
    <div className="space-y-3 print:hidden">
      <section className="glass rounded-xl p-4">
        <div className="flex items-center justify-between gap-3"><div><h3 className="font-semibold text-foreground">🧳 Packing list</h3><p className="text-xs text-foreground-muted">Built from your dates, weather, and trip vibe.</p></div><button onClick={createPackingList} disabled={isPacking} className="rounded-lg border border-primary/50 px-3 py-2 text-sm font-medium text-primary disabled:opacity-50">{isPacking ? "Creating…" : itinerary.packing_list.length ? "Refresh" : "Generate"}</button></div>
        {itinerary.packing_list.length > 0 && <ul className="mt-3 space-y-2">{itinerary.packing_list.map((item) => <li key={`${item.category}-${item.item}`} className="text-sm text-foreground-secondary"><span className="mr-2 text-accent">✓</span><strong className="text-foreground">{item.item}</strong><span className="text-foreground-muted"> — {item.reason}</span></li>)}</ul>}
      </section>
      <button onClick={() => { track("trip_exported", { tripId: itinerary.id, kind: "single", metadata: { source: "print" } }); window.print(); }} className="w-full rounded-xl border border-glass-border py-3 text-sm font-medium text-foreground hover:bg-glass-highlight">🖨️ Print or save as PDF</button>
      {error && <p className="text-sm text-error">{error}</p>}
    </div>
  );
}
