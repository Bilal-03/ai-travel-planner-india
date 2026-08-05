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

export function DestinationInspiration({ itinerary }: Pick<TripUpdateProps, "itinerary">) {
  const photo = itinerary.destination_photos[0];
  if (!photo) return null;

  return (
    <section className="rounded-xl border border-glass-border bg-glass-bg p-4">
      <h3 className="font-semibold text-foreground">📸 Destination inspiration</h3>
      <figure className="destination-frame relative mt-3 h-44 overflow-hidden rounded-xl bg-surface">
        {/* Destination providers return dynamic remote URLs; using a plain image avoids an unsafe allowlist bypass. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={photo.url} alt={photo.alt} className="h-full w-full object-cover" />
        <figcaption className="absolute inset-x-0 bottom-0 bg-black/55 px-3 py-2 text-xs text-white">
          {photo.photographer_url ? <a className="underline" href={photo.photographer_url} target="_blank" rel="noreferrer">Photo by {photo.photographer_name || "Unsplash"} on Unsplash</a> : "Destination inspiration"}
        </figcaption>
      </figure>
    </section>
  );
}

export function PrintTripButton({ itinerary, className = "" }: { itinerary: Itinerary; className?: string }) {
  return (
    <button
      type="button"
      data-testid="print-trip-button"
      onClick={() => { track("trip_exported", { tripId: itinerary.id, kind: "single", metadata: { source: "print" } }); window.print(); }}
      className={`inline-flex items-center justify-center rounded-xl border border-glass-border px-3 py-2 text-sm font-medium text-foreground hover:bg-glass-highlight print:hidden ${className}`}
    >
      🖨️ Print or save as PDF
    </button>
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
        <div className="flex items-center justify-between gap-3"><div><h3 className="font-semibold text-foreground">🧳 Packing list</h3><p className="text-xs text-foreground-muted">Built from your dates, weather, and planning context.</p></div><button onClick={createPackingList} disabled={isPacking} className="rounded-lg border border-primary/50 px-3 py-2 text-sm font-medium text-primary disabled:opacity-50">{isPacking ? "Creating…" : itinerary.packing_list.length ? "Refresh" : "Generate"}</button></div>
        {itinerary.packing_list.length > 0 && <ul className="mt-3 space-y-2">{itinerary.packing_list.map((item) => <li key={`${item.category}-${item.item}`} className="text-sm text-foreground-secondary"><span className="mr-2 text-accent">✓</span><strong className="text-foreground">{item.item}</strong><span className="text-foreground-muted"> — {item.reason}</span></li>)}</ul>}
      </section>
      <PrintTripButton itinerary={itinerary} className="w-full" />
      {error && <p className="text-sm text-error">{error}</p>}
    </div>
  );
}
