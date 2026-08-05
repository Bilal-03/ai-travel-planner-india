"use client";

import { FormEvent, useEffect, useState } from "react";
import { ApiError, Itinerary, Place, api, formatDuration, formatINR } from "@/lib/api";
import { track } from "@/lib/analytics";

interface PlaceDiscoveryProps {
  itinerary: Itinerary;
  isOpen: boolean;
  onClose: () => void;
  onUpdate: (itinerary: Itinerary) => void;
}

interface SavedPlacesPanelProps {
  itinerary: Itinerary;
  onOpenDiscovery: () => void;
  onUpdate: (itinerary: Itinerary) => void;
}

function categoryLabel(category: string): string {
  return category.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function placePhoto(place: Place, itinerary: Itinerary): { url: string; alt: string } | null {
  const photo = place.photos?.[0];
  if (photo) return { url: photo.url, alt: photo.alt || place.name };
  const destinationPhoto = itinerary.destination_photos?.[0];
  if (destinationPhoto) return { url: destinationPhoto.url, alt: place.name };
  return null;
}

function PlaceImage({ place, itinerary, compact = false }: { place: Place; itinerary: Itinerary; compact?: boolean }) {
  const photo = placePhoto(place, itinerary);
  if (!photo) {
    return <div className={`${compact ? "h-16 w-20" : "h-28 w-full"} place-card-placeholder`} aria-hidden="true">✦</div>;
  }
  return (
    // Destination and provider photos are dynamic URLs; the API owns attribution metadata.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={photo.url} alt={photo.alt} className={compact ? "h-16 w-20 rounded-lg object-cover" : "h-28 w-full rounded-lg object-cover"} />
  );
}

function PlaceMeta({ place }: { place: Place }) {
  const visitMinutes = place.estimated_visit_minutes || 60;
  const estimatedCost = place.estimated_cost || 0;
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-foreground-muted">
      <span>{formatDuration(visitMinutes)} visit</span>
      <span>{estimatedCost ? `${formatINR(estimatedCost)} est.` : "No ticket estimate"}</span>
      {place.rating !== null && place.rating !== undefined && <span>★ {place.rating.toFixed(1)}</span>}
    </div>
  );
}

function PlaceCard({
  place,
  itinerary,
  isSaved,
  onSave,
  onSelect,
  actionKey,
}: {
  place: Place;
  itinerary: Itinerary;
  isSaved: boolean;
  onSave: (place: Place) => void;
  onSelect: (place: Place) => void;
  actionKey: string | null;
}) {
  const isSaving = actionKey === `save:${place.id}`;
  return (
    <article data-testid={`place-card-${place.id}`} className="place-discovery-card">
      <PlaceImage place={place} itinerary={itinerary} />
      <div className="mt-3 min-w-0">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold text-foreground">{place.name}</h3>
            <p className="mt-1 text-[11px] uppercase tracking-[0.1em] text-marigold">{categoryLabel(place.category)}</p>
          </div>
          {isSaved && <span className="shrink-0 rounded-full bg-success/15 px-2 py-1 text-[10px] font-semibold text-success">Saved</span>}
        </div>
        <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-foreground-secondary">{place.description || "A place to consider for this India itinerary."}</p>
        <PlaceMeta place={place} />
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            data-testid={`save-place-${place.id}`}
            onClick={() => onSave(place)}
            disabled={isSaving || isSaved}
            className="flex-1 rounded-lg border border-glass-border px-2.5 py-2 text-[11px] font-semibold text-foreground-secondary transition hover:border-primary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSaving ? "Saving…" : isSaved ? "Saved" : "Save place"}
          </button>
          <button
            type="button"
            data-testid={`add-place-${place.id}`}
            onClick={() => onSelect(place)}
            className="warm-button flex-1 rounded-lg px-2.5 py-2 text-[11px] font-semibold text-white"
          >
            Add to day
          </button>
        </div>
      </div>
    </article>
  );
}

function DayPicker({
  itinerary,
  place,
  selectedDay,
  onDayChange,
  onAdd,
  isAdding,
}: {
  itinerary: Itinerary;
  place: Place;
  selectedDay: number;
  onDayChange: (day: number) => void;
  onAdd: () => void;
  isAdding: boolean;
}) {
  return (
    <section className="place-selected-panel" aria-label={`Choose a day for ${place.name}`}>
      <div className="flex min-w-0 items-center gap-3">
        <div className="h-12 w-16 shrink-0 overflow-hidden rounded-lg"><PlaceImage place={place} itinerary={itinerary} compact /></div>
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.12em] text-marigold">Ready to add</p>
          <h3 className="truncate text-sm font-semibold text-foreground">{place.name}</h3>
        </div>
      </div>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="min-w-0 flex-1 text-xs text-foreground-muted">
          Add to day
          <select value={selectedDay} onChange={(event) => onDayChange(Number(event.target.value))} className="mt-1 block w-full rounded-lg border border-glass-border bg-background/50 px-3 py-2 text-sm text-foreground outline-none focus:border-primary" aria-label={`Day for ${place.name}`}>
            {itinerary.day_plans.map((day) => <option key={day.day_number} value={day.day_number}>Day {day.day_number} · {day.date}</option>)}
          </select>
        </label>
        <button type="button" onClick={onAdd} disabled={isAdding || !itinerary.day_plans.length} className="warm-button rounded-lg px-4 py-2.5 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">
          {isAdding ? "Adding…" : "Add to itinerary"}
        </button>
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-foreground-muted">The planner will place it after the current stops on that day and update the working budget.</p>
    </section>
  );
}

export function SavedPlacesPanel({ itinerary, onOpenDiscovery, onUpdate }: SavedPlacesPanelProps) {
  const places = itinerary.places || [];
  const [dayByPlace, setDayByPlace] = useState<Record<string, number>>({});
  const [actionKey, setActionKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const changePlace = async (place: Place, action: "add" | "remove") => {
    const key = `${action}:${place.id}`;
    setActionKey(key);
    setError(null);
    try {
      if (action === "remove") {
        onUpdate(await api.removeSavedPlace(itinerary.id, place.id));
        track("place_removed", { tripId: itinerary.id, kind: "single", metadata: { category: place.category } });
      } else {
        const dayNumber = dayByPlace[place.id] || itinerary.day_plans[0]?.day_number;
        if (!dayNumber) throw new ApiError("This trip has no planned day to add the place to.", 400);
        onUpdate(await api.addPlaceToItinerary(itinerary.id, place.id, dayNumber));
        track("place_added", { tripId: itinerary.id, kind: "single", metadata: { category: place.category, day_number: dayNumber } });
      }
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Couldn’t update Saved Places.");
    } finally {
      setActionKey(null);
    }
  };

  return (
    <section className="space-y-4" aria-label="Saved Places">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-marigold">Trip collection</p>
          <h2 className="mt-1 text-xl font-bold text-foreground">Saved Places <span className="text-sm font-normal text-foreground-muted">{places.length}</span></h2>
          <p className="mt-1 text-xs leading-relaxed text-foreground-secondary">Keep ideas here, then place them on a day when the route feels right.</p>
        </div>
        <button type="button" onClick={onOpenDiscovery} className="workspace-add-button rounded-lg px-3 py-2 text-xs font-semibold text-white">+ Discover places</button>
      </div>
      {error && <p className="rounded-lg border border-error/30 bg-error/10 p-3 text-xs leading-relaxed text-error" role="alert">{error}</p>}
      {places.length === 0 ? (
        <div className="workspace-empty-state rounded-xl border border-dashed border-glass-border p-6 text-center">
          <span className="text-2xl text-marigold" aria-hidden="true">✦</span>
          <h3 className="mt-2 text-sm font-semibold text-foreground">Your place shelf is empty.</h3>
          <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-foreground-muted">Search reviewed landmarks and map places around {itinerary.destination.name}, save the ones that fit, and add them to any day.</p>
          <button type="button" onClick={onOpenDiscovery} className="mt-4 rounded-lg border border-primary/50 px-3 py-2 text-xs font-semibold text-primary hover:bg-primary/10">Open place search</button>
        </div>
      ) : (
        <div className="space-y-3">
          {places.map((place) => {
            const isAdding = actionKey === `add:${place.id}`;
            const isRemoving = actionKey === `remove:${place.id}`;
            return (
              <article key={place.id} className="saved-place-row">
                <PlaceImage place={place} itinerary={itinerary} compact />
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0"><h3 className="truncate text-sm font-semibold text-foreground">{place.name}</h3><p className="mt-1 text-[11px] uppercase tracking-[0.1em] text-marigold">{categoryLabel(place.category)}</p></div>
                    <button type="button" onClick={() => void changePlace(place, "remove")} disabled={isRemoving} className="shrink-0 text-[11px] text-foreground-muted hover:text-error disabled:opacity-60">{isRemoving ? "Removing…" : "Remove"}</button>
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-foreground-secondary">{place.description || "Saved for this trip."}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <select value={dayByPlace[place.id] || itinerary.day_plans[0]?.day_number || ""} onChange={(event) => setDayByPlace((current) => ({ ...current, [place.id]: Number(event.target.value) }))} className="rounded-md border border-glass-border bg-background/50 px-2 py-1.5 text-[11px] text-foreground" aria-label={`Choose day for ${place.name}`}>
                      {itinerary.day_plans.map((day) => <option key={day.day_number} value={day.day_number}>Day {day.day_number}</option>)}
                    </select>
                    <button type="button" onClick={() => void changePlace(place, "add")} disabled={isAdding || !itinerary.day_plans.length} className="rounded-md bg-primary/15 px-2.5 py-1.5 text-[11px] font-semibold text-primary hover:bg-primary/25 disabled:opacity-60">{isAdding ? "Adding…" : "Add to itinerary"}</button>
                    <span className="text-[11px] text-foreground-muted">{formatDuration(place.estimated_visit_minutes || 60)}</span>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default function PlaceDiscovery({ itinerary, isOpen, onClose, onUpdate }: PlaceDiscoveryProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Place[]>([]);
  const [isSearching, setIsSearching] = useState(true);
  const [actionKey, setActionKey] = useState<string | null>(null);
  const [selectedPlace, setSelectedPlace] = useState<Place | null>(null);
  const [selectedDay, setSelectedDay] = useState(itinerary.day_plans[0]?.day_number || 1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const controller = new AbortController();
    void api.searchPlaces({
      coordinates: itinerary.destination.coordinates,
      city: itinerary.destination.name,
      focus: itinerary.preferences?.experiences?.join(","),
      signal: controller.signal,
    }).then(setResults).catch((requestError: unknown) => {
      if (!controller.signal.aborted) setError(requestError instanceof ApiError ? requestError.message : "Couldn’t load places around this destination.");
    }).finally(() => {
      if (!controller.signal.aborted) setIsSearching(false);
    });
    return () => controller.abort();
  }, [isOpen, itinerary.destination.coordinates, itinerary.destination.name, itinerary.day_plans, itinerary.preferences?.experiences]);

  if (!isOpen) return null;

  const runSearch = async (event?: FormEvent) => {
    event?.preventDefault();
    setIsSearching(true);
    setError(null);
    try {
      setResults(await api.searchPlaces({
        coordinates: itinerary.destination.coordinates,
        city: itinerary.destination.name,
        query: query.trim() || undefined,
        focus: itinerary.preferences?.experiences?.join(","),
      }));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Couldn’t search places right now.");
    } finally {
      setIsSearching(false);
    }
  };

  const savedIds = new Set((itinerary.places || []).map((place) => place.id));

  const save = async (place: Place) => {
    setActionKey(`save:${place.id}`);
    setError(null);
    try {
      onUpdate(await api.savePlace(itinerary.id, place));
      track("place_saved", { tripId: itinerary.id, kind: "single", metadata: { category: place.category } });
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Couldn’t save this place.");
    } finally {
      setActionKey(null);
    }
  };

  const add = async () => {
    if (!selectedPlace || !selectedDay) return;
    setActionKey(`add:${selectedPlace.id}`);
    setError(null);
    try {
      onUpdate(await api.addPlaceToItinerary(itinerary.id, selectedPlace.id, selectedDay, selectedPlace));
      track("place_added", { tripId: itinerary.id, kind: "single", metadata: { category: selectedPlace.category, day_number: selectedDay } });
      setSelectedPlace(null);
      onClose();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Couldn’t add this place to the itinerary.");
    } finally {
      setActionKey(null);
    }
  };

  return (
    <div className="place-discovery-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="place-discovery-modal" role="dialog" aria-modal="true" aria-labelledby="place-discovery-title" data-testid="add-to-itinerary-dialog">
        <header className="flex items-start justify-between gap-4">
          <div><p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.15em] text-marigold">{itinerary.destination.name} · India</p><h2 id="place-discovery-title" className="mt-1 text-2xl font-bold tracking-tight text-foreground">Add to itinerary</h2><p className="mt-1 text-xs text-foreground-muted">Search places near your route, save ideas, and place them on a day.</p></div>
          <button type="button" onClick={onClose} aria-label="Close place search" className="rounded-full border border-glass-border px-2.5 py-1 text-lg leading-none text-foreground-muted hover:text-foreground">×</button>
        </header>
        <div className="place-discovery-tabs mt-5" role="tablist" aria-label="Add item type">
          <button type="button" role="tab" aria-selected="true" className="place-discovery-tab place-discovery-tab-active">Place</button>
          {(["Stay", "Flight", "Event"] as const).map((tab) => <button key={tab} type="button" role="tab" aria-selected="false" disabled className="place-discovery-tab">{tab}<span className="ml-1 text-[9px]">Soon</span></button>)}
        </div>
        <form onSubmit={(event) => void runSearch(event)} className="mt-4 flex gap-2">
          <label htmlFor="place-search-input" className="sr-only">Search place</label>
          <input id="place-search-input" data-testid="place-search-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`Search ${itinerary.destination.name} places`} className="min-w-0 flex-1 rounded-xl border border-primary/50 bg-background/45 px-4 py-3 text-sm text-foreground outline-none placeholder:text-foreground-muted focus:ring-2 focus:ring-primary/20" />
          <button type="submit" disabled={isSearching} className="warm-button rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">{isSearching ? "…" : "Search"}</button>
        </form>
        {error && <p className="mt-3 rounded-lg border border-error/30 bg-error/10 p-3 text-xs leading-relaxed text-error" role="alert">{error}</p>}
        {selectedPlace && <DayPicker itinerary={itinerary} place={selectedPlace} selectedDay={selectedDay} onDayChange={setSelectedDay} onAdd={() => void add()} isAdding={actionKey === `add:${selectedPlace.id}`} />}
        <div className="mt-5 flex items-center justify-between gap-3"><h3 className="text-sm font-semibold text-foreground">Places to consider</h3><span className="text-[11px] text-foreground-muted">{results.length} result{results.length === 1 ? "" : "s"}</span></div>
        {isSearching && !results.length ? <div className="place-discovery-loading" aria-live="polite"><span className="text-marigold">✦</span> Looking around {itinerary.destination.name}…</div> : results.length ? <div className="place-discovery-grid mt-3">{results.map((place) => <PlaceCard key={place.id} place={place} itinerary={itinerary} isSaved={savedIds.has(place.id)} onSave={(value) => void save(value)} onSelect={(value) => { setSelectedPlace(value); setSelectedDay(itinerary.day_plans[0]?.day_number || 1); }} actionKey={actionKey} />)}</div> : <div className="workspace-empty-state mt-3 rounded-xl border border-dashed border-glass-border p-6 text-center"><p className="text-sm font-semibold text-foreground">No matching places yet.</p><p className="mt-1 text-xs text-foreground-muted">Try a landmark, market, fort, garden, food, or a broader search.</p></div>}
        <p className="mt-5 text-[10px] leading-relaxed text-foreground-muted">Place details and costs are planning estimates from map or reviewed tourism sources. Confirm current hours, access, closures, and ticket prices before visiting.</p>
      </section>
    </div>
  );
}
