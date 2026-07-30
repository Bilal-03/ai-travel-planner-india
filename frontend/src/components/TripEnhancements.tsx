"use client";

import { useState } from "react";
import { Itinerary } from "@/lib/api";

interface TripEnhancementsProps {
  itinerary: Itinerary;
  onUpdate: (itinerary: Itinerary) => void;
}

export default function TripEnhancements({ itinerary, onUpdate }: TripEnhancementsProps) {
  const [instruction, setInstruction] = useState("");
  const [isRefining, setIsRefining] = useState(false);
  const [isPacking, setIsPacking] = useState(false);
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

  const hotelSearch = `https://www.google.com/travel/search?q=${encodeURIComponent(`Hotels in ${itinerary.destination.name} ${itinerary.start_date} ${itinerary.end_date}`)}`;
  const bookingSearch = `https://www.booking.com/searchresults.html?${new URLSearchParams({ ss: `${itinerary.destination.name}, India`, checkin: itinerary.start_date, checkout: itinerary.end_date }).toString()}`;
  const makeMyTripSearch = "https://www.makemytrip.com/hotels/";

  return (
    <div className="space-y-6 print:hidden">
      {itinerary.destination_photos[0] && (
        <figure className="destination-frame relative overflow-hidden rounded-2xl bg-surface h-64">
          <img src={itinerary.destination_photos[0].url} alt={itinerary.destination_photos[0].alt} className="h-full w-full object-cover" />
          <figcaption className="absolute inset-x-0 bottom-0 bg-black/55 px-4 py-2 text-xs text-white">
            {itinerary.destination_photos[0].photographer_url ? <a className="underline" href={itinerary.destination_photos[0].photographer_url} target="_blank" rel="noreferrer">Photo by {itinerary.destination_photos[0].photographer_name || "Unsplash"} on Unsplash</a> : "Destination inspiration"}
          </figcaption>
        </figure>
      )}

      {itinerary.festivals.length > 0 && (
        <section className="rounded-xl border border-accent/30 bg-accent/10 p-4">
          <h3 className="font-semibold text-foreground">🎉 Festival-aware travel</h3>
          <div className="mt-2 space-y-2">
            {itinerary.festivals.map((festival) => <div key={festival.name} className="text-sm text-foreground-secondary"><strong className="text-foreground">{festival.name}</strong> — {festival.description}<br /><span className="text-foreground-muted">Tip: {festival.travel_tip}</span></div>)}
          </div>
        </section>
      )}

      <section className="glass p-4 rounded-xl">
        <h3 className="font-semibold text-foreground">✨ Refine this itinerary</h3>
        <p className="mt-1 text-xs text-foreground-muted">Try “make day 3 cheaper”, “add a food stop”, or “swap this activity”.</p>
        <form onSubmit={refine} className="mt-3 flex gap-2">
          <input value={instruction} onChange={(event) => setInstruction(event.target.value)} maxLength={500} placeholder="Tell YatraAI what to change" className="min-w-0 flex-1 rounded-lg border border-glass-border bg-glass-bg px-3 py-2 text-sm text-foreground outline-none focus:border-primary" />
          <button disabled={isRefining || instruction.trim().length < 3} className="warm-button rounded-lg px-3 py-2 text-sm font-medium text-white disabled:opacity-50">{isRefining ? "Updating…" : "Update"}</button>
        </form>
      </section>

      <section className="glass p-4 rounded-xl">
        <div className="flex items-center justify-between gap-3"><div><h3 className="font-semibold text-foreground">🧳 Smart packing list</h3><p className="text-xs text-foreground-muted">Built from your dates, weather, and trip vibe.</p></div><button onClick={createPackingList} disabled={isPacking} className="rounded-lg border border-primary/50 px-3 py-2 text-sm font-medium text-primary disabled:opacity-50">{isPacking ? "Creating…" : itinerary.packing_list.length ? "Refresh" : "Generate"}</button></div>
        {itinerary.packing_list.length > 0 && <ul className="mt-3 space-y-2">{itinerary.packing_list.map((item) => <li key={`${item.category}-${item.item}`} className="text-sm text-foreground-secondary"><span className="mr-2 text-accent">✓</span><strong className="text-foreground">{item.item}</strong><span className="text-foreground-muted"> — {item.reason}</span></li>)}</ul>}
      </section>

      <section className="rounded-xl border border-glass-border bg-glass-bg p-4"><span className="block font-semibold text-foreground">🏨 Find a stay</span><span className="text-xs text-foreground-muted">Compare live accommodation for your trip dates.</span><div className="mt-3 flex flex-wrap gap-2"><a href={hotelSearch} target="_blank" rel="noreferrer" className="rounded-lg border border-primary/50 px-3 py-2 text-xs font-medium text-primary">Google Hotels ↗</a><a href={bookingSearch} target="_blank" rel="noreferrer" className="rounded-lg border border-primary/50 px-3 py-2 text-xs font-medium text-primary">Booking.com ↗</a><a href={makeMyTripSearch} target="_blank" rel="noreferrer" className="rounded-lg border border-primary/50 px-3 py-2 text-xs font-medium text-primary">MakeMyTrip ↗</a></div></section>
      <button onClick={() => window.print()} className="w-full rounded-xl border border-glass-border py-3 text-sm font-medium text-foreground hover:bg-glass-highlight">🖨️ Print or save as PDF</button>
      {error && <p className="text-sm text-error">{error}</p>}
    </div>
  );
}
