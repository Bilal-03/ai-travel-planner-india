"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  Itinerary,
  ItineraryItem,
  Place,
  StayOption,
  TransportOption,
  api,
  formatDuration,
  formatINR,
} from "@/lib/api";
import { track } from "@/lib/analytics";
import DataStatusBadge from "./DataStatusBadge";
import EstimateDisclaimer from "./EstimateDisclaimer";
import ProviderAttribution from "./ProviderAttribution";
import TransportCard from "./TransportCard";

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

type DiscoveryTab = "place" | "stay" | "transport";
type TransportSearchMode = "flight" | "train";

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

function StayCard({
  stay,
  isAdded,
  isAdding,
  onAdd,
}: {
  stay: StayOption;
  isAdded: boolean;
  isAdding: boolean;
  onAdd: (stay: StayOption) => void;
}) {
  return (
    <article data-testid={`stay-card-${stay.id}`} className="place-discovery-card">
      <div className="stay-card-illustration" aria-hidden="true">🛏️</div>
      <div className="mt-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-[0.1em] text-marigold">{stay.area}</p>
          <h3 className="mt-1 truncate text-sm font-semibold text-foreground">{stay.name}</h3>
        </div>
        <DataStatusBadge provenance={stay.provenance} compact />
      </div>
      <p className="mt-2 text-xs leading-relaxed text-foreground-secondary">{stay.description}</p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-foreground-muted">
        <span>{formatINR(stay.nightly_price)} / room / night</span>
        <span className="text-right">{stay.nights} night{stay.nights === 1 ? "" : "s"} · {stay.rooms} room{stay.rooms === 1 ? "" : "s"}</span>
        <span className="font-semibold text-foreground">{formatINR(stay.total_price)} trip estimate</span>
        <span className="text-right">{stay.check_in} → {stay.check_out}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {stay.amenities.map((amenity) => <span key={amenity} className="rounded-full bg-glass-highlight px-2 py-1 text-[10px] text-foreground-muted">{amenity}</span>)}
      </div>
      <div className="mt-3 flex items-center gap-2">
        <button type="button" data-testid={`add-stay-${stay.id}`} onClick={() => onAdd(stay)} disabled={isAdding || isAdded} className="warm-button flex-1 rounded-lg px-2.5 py-2 text-[11px] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">
          {isAdding ? "Adding…" : isAdded ? "Added to itinerary" : "Add stay estimate"}
        </button>
        <a href={stay.booking_url} target="_blank" rel="noreferrer" onClick={() => track("provider_link_clicked", { metadata: { provider: "Google Hotels", source: "stay" } })} className="rounded-lg border border-glass-border px-2.5 py-2 text-[11px] font-semibold text-primary hover:border-primary">
          Search live ↗
        </a>
      </div>
      <div className="mt-3 space-y-1">
        <ProviderAttribution provenance={stay.provenance} />
        <EstimateDisclaimer provenance={stay.provenance} />
      </div>
    </article>
  );
}

function stayItemDetails(item: ItineraryItem): { stayId: string; area: string; totalPrice: number; bookingUrl: string | null } {
  const metadata = item.metadata || {};
  return {
    stayId: typeof metadata.stay_id === "string" ? metadata.stay_id : item.id,
    area: typeof metadata.area === "string" ? metadata.area : "Destination stay",
    totalPrice: typeof metadata.total_price === "number" ? metadata.total_price : 0,
    bookingUrl: typeof metadata.booking_url === "string" ? metadata.booking_url : null,
  };
}

export function SavedPlacesPanel({ itinerary, onOpenDiscovery, onUpdate }: SavedPlacesPanelProps) {
  const places = itinerary.places || [];
  const stayItems = (itinerary.items || []).filter((item) => item.item_type === "stay");
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

  const removeStay = async (item: ItineraryItem) => {
    const details = stayItemDetails(item);
    setActionKey(`remove-stay:${details.stayId}`);
    setError(null);
    try {
      onUpdate(await api.removeStayFromItinerary(itinerary.id, details.stayId));
      track("stay_removed", { tripId: itinerary.id, kind: "single" });
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Couldn’t remove this stay estimate.");
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
        <button type="button" onClick={onOpenDiscovery} className="workspace-add-button rounded-lg px-3 py-2 text-xs font-semibold text-white">+ Discover places & travel</button>
      </div>
      {error && <p className="rounded-lg border border-error/30 bg-error/10 p-3 text-xs leading-relaxed text-error" role="alert">{error}</p>}

      {stayItems.length > 0 && (
        <section aria-labelledby="planned-stays-heading" className="rounded-xl border border-teal-400/25 bg-teal-400/5 p-4">
          <div className="flex items-end justify-between gap-3">
            <div><p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-teal-300">Trip-level items</p><h3 id="planned-stays-heading" className="mt-1 text-sm font-semibold text-foreground">Stays in this plan</h3></div>
            <button type="button" onClick={onOpenDiscovery} className="text-[11px] font-semibold text-primary hover:text-primary-light">Compare areas</button>
          </div>
          <div className="mt-3 space-y-2">
            {stayItems.map((item) => {
              const details = stayItemDetails(item);
              return <article key={item.id} className="saved-stay-row"><div className="min-w-0 flex-1"><h4 className="truncate text-sm font-semibold text-foreground">{item.title}</h4><p className="mt-1 text-xs text-foreground-secondary">{details.area} · {formatINR(details.totalPrice)} estimate</p></div>{details.bookingUrl && <a href={details.bookingUrl} target="_blank" rel="noreferrer" onClick={() => track("provider_link_clicked", { metadata: { provider: "Google Hotels", source: "saved_stay" } })} className="text-[11px] font-semibold text-primary">Search live ↗</a>}<button type="button" onClick={() => void removeStay(item)} disabled={actionKey === `remove-stay:${details.stayId}`} className="text-[11px] text-foreground-muted hover:text-error disabled:opacity-60">{actionKey === `remove-stay:${details.stayId}` ? "Removing…" : "Remove"}</button></article>;
            })}
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-foreground-muted">These are planning estimates, not reservations. Confirm room type, taxes, cancellation terms, and availability with a live provider.</p>
        </section>
      )}

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

function defaultCheckout(startDate: string, endDate: string): string {
  if (endDate > startDate) return endDate;
  const date = new Date(`${startDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString().slice(0, 10);
}

export default function PlaceDiscovery({ itinerary, isOpen, onClose, onUpdate }: PlaceDiscoveryProps) {
  const [activeTab, setActiveTab] = useState<DiscoveryTab>("place");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Place[]>([]);
  const [isSearching, setIsSearching] = useState(true);
  const [actionKey, setActionKey] = useState<string | null>(null);
  const [selectedPlace, setSelectedPlace] = useState<Place | null>(null);
  const [selectedDay, setSelectedDay] = useState(itinerary.day_plans[0]?.day_number || 1);
  const [error, setError] = useState<string | null>(null);
  const [transportMode, setTransportMode] = useState<TransportSearchMode>("flight");
  const [transportDate, setTransportDate] = useState(itinerary.start_date);
  const [transportResults, setTransportResults] = useState<TransportOption[]>([]);
  const [isTransportSearching, setIsTransportSearching] = useState(false);
  const [transportSearchNonce, setTransportSearchNonce] = useState(0);
  const [stayCheckIn, setStayCheckIn] = useState(itinerary.start_date);
  const [stayCheckOut, setStayCheckOut] = useState(defaultCheckout(itinerary.start_date, itinerary.end_date));
  const [stayResults, setStayResults] = useState<StayOption[]>([]);
  const [isStaySearching, setIsStaySearching] = useState(false);
  const [staySearchNonce, setStaySearchNonce] = useState(0);

  const savedIds = useMemo(() => new Set((itinerary.places || []).map((place) => place.id)), [itinerary.places]);
  const addedStayIds = useMemo(() => new Set((itinerary.items || []).filter((item) => item.item_type === "stay").map((item) => stayItemDetails(item).stayId)), [itinerary.items]);

  useEffect(() => {
    if (!isOpen || activeTab !== "place") return undefined;
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
  }, [isOpen, activeTab, itinerary.destination.coordinates, itinerary.destination.name, itinerary.preferences?.experiences]);

  useEffect(() => {
    if (!isOpen || activeTab !== "transport") return undefined;
    const controller = new AbortController();
    const request = transportMode === "flight"
      ? api.searchFlights(itinerary.origin.name, itinerary.destination.name, transportDate)
      : api.searchTrains(itinerary.origin.name, itinerary.destination.name, transportDate);
    void request.then((options) => {
      if (!controller.signal.aborted) setTransportResults(options);
    }).catch((requestError: unknown) => {
      if (!controller.signal.aborted) setError(requestError instanceof ApiError ? requestError.message : "Couldn’t search transport right now.");
    }).finally(() => {
      if (!controller.signal.aborted) setIsTransportSearching(false);
    });
    return () => controller.abort();
  }, [isOpen, activeTab, itinerary.origin.name, itinerary.destination.name, transportDate, transportMode, transportSearchNonce]);

  useEffect(() => {
    if (!isOpen || activeTab !== "stay") return undefined;
    const controller = new AbortController();
    void api.searchStays(
      itinerary.destination.name,
      stayCheckIn,
      stayCheckOut,
      itinerary.members || 2,
      itinerary.preferences?.hotel_style || undefined,
    ).then((options) => {
      if (!controller.signal.aborted) setStayResults(options);
    }).catch((requestError: unknown) => {
      if (!controller.signal.aborted) setError(requestError instanceof ApiError ? requestError.message : "Couldn’t search stay areas right now.");
    }).finally(() => {
      if (!controller.signal.aborted) setIsStaySearching(false);
    });
    return () => controller.abort();
  }, [isOpen, activeTab, itinerary.destination.name, itinerary.members, itinerary.preferences?.hotel_style, stayCheckIn, stayCheckOut, staySearchNonce]);

  if (!isOpen) return null;

  const runPlaceSearch = async (event?: FormEvent) => {
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
      closeDiscovery();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Couldn’t add this place to the itinerary.");
    } finally {
      setActionKey(null);
    }
  };

  const selectTransport = async (option: TransportOption) => {
    const key = `transport:${option.mode}:${option.provider}:${option.code || ""}`;
    setActionKey(key);
    setError(null);
    try {
      onUpdate(await api.selectTransport(itinerary.id, option, transportDate));
      track("transport_selected", { tripId: itinerary.id, kind: "single", metadata: { provider: option.provider, source: "add_modal" } });
      closeDiscovery();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Couldn’t select this transport option.");
    } finally {
      setActionKey(null);
    }
  };

  const addStay = async (stay: StayOption) => {
    setActionKey(`stay:${stay.id}`);
    setError(null);
    try {
      onUpdate(await api.addStayToItinerary(itinerary.id, stay));
      track("stay_added", { tripId: itinerary.id, kind: "single", metadata: { source: "add_modal", estimated_data: true } });
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Couldn’t add this stay estimate.");
    } finally {
      setActionKey(null);
    }
  };

  const changeTab = (tab: DiscoveryTab) => {
    setActiveTab(tab);
    setSelectedPlace(null);
    setError(null);
    if (tab === "place") setIsSearching(true);
    if (tab === "stay") setIsStaySearching(true);
    if (tab === "transport") setIsTransportSearching(true);
  };

  const closeDiscovery = () => {
    setActiveTab("place");
    setSelectedPlace(null);
    setError(null);
    onClose();
  };

  const tabButton = (tab: DiscoveryTab, label: string) => (
    <button type="button" role="tab" aria-selected={activeTab === tab} onClick={() => changeTab(tab)} className={`place-discovery-tab ${activeTab === tab ? "place-discovery-tab-active" : ""}`}>
      {label}
    </button>
  );

  return (
    <div className="place-discovery-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) closeDiscovery(); }}>
      <section className="place-discovery-modal" role="dialog" aria-modal="true" aria-labelledby="place-discovery-title" data-testid="add-to-itinerary-dialog">
        <header className="flex items-start justify-between gap-4">
          <div><p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.15em] text-marigold">{itinerary.destination.name} · India</p><h2 id="place-discovery-title" className="mt-1 text-2xl font-bold tracking-tight text-foreground">Add to itinerary</h2><p className="mt-1 text-xs text-foreground-muted">Search places, compare transport, or add a clearly-labelled stay estimate.</p></div>
          <button type="button" onClick={closeDiscovery} aria-label="Close place search" className="rounded-full border border-glass-border px-2.5 py-1 text-lg leading-none text-foreground-muted hover:text-foreground">×</button>
        </header>
        <div className="place-discovery-tabs mt-5" role="tablist" aria-label="Add item type">
          {tabButton("place", "Place")}
          {tabButton("stay", "Stay")}
          {tabButton("transport", "Flight")}
          <button type="button" role="tab" aria-selected="false" disabled className="place-discovery-tab">Event<span className="ml-1 text-[9px]">Soon</span></button>
        </div>

        {activeTab === "place" && <>
          <form onSubmit={(event) => void runPlaceSearch(event)} className="mt-4 flex gap-2">
            <label htmlFor="place-search-input" className="sr-only">Search place</label>
            <input id="place-search-input" data-testid="place-search-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`Search ${itinerary.destination.name} places`} className="min-w-0 flex-1 rounded-xl border border-primary/50 bg-background/45 px-4 py-3 text-sm text-foreground outline-none placeholder:text-foreground-muted focus:ring-2 focus:ring-primary/20" />
            <button type="submit" disabled={isSearching} className="warm-button rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">{isSearching ? "…" : "Search"}</button>
          </form>
          {selectedPlace && <DayPicker itinerary={itinerary} place={selectedPlace} selectedDay={selectedDay} onDayChange={setSelectedDay} onAdd={() => void add()} isAdding={actionKey === `add:${selectedPlace.id}`} />}
          <div className="mt-5 flex items-center justify-between gap-3"><h3 className="text-sm font-semibold text-foreground">Places to consider</h3><span className="text-[11px] text-foreground-muted">{results.length} result{results.length === 1 ? "" : "s"}</span></div>
          {isSearching && !results.length ? <div className="place-discovery-loading" aria-live="polite"><span className="text-marigold">✦</span> Looking around {itinerary.destination.name}…</div> : results.length ? <div className="place-discovery-grid mt-3">{results.map((place) => <PlaceCard key={place.id} place={place} itinerary={itinerary} isSaved={savedIds.has(place.id)} onSave={(value) => void save(value)} onSelect={(value) => { setSelectedPlace(value); setSelectedDay(itinerary.day_plans[0]?.day_number || 1); }} actionKey={actionKey} />)}</div> : <div className="workspace-empty-state mt-3 rounded-xl border border-dashed border-glass-border p-6 text-center"><p className="text-sm font-semibold text-foreground">No matching places yet.</p><p className="mt-1 text-xs text-foreground-muted">Try a landmark, market, fort, garden, food, or a broader search.</p></div>}
        </>}

        {activeTab === "transport" && <>
          <form onSubmit={(event) => { event.preventDefault(); setTransportSearchNonce((value) => value + 1); }} className="mt-4 rounded-xl border border-glass-border bg-background/25 p-3">
            <div className="flex flex-wrap items-center gap-2"><button type="button" onClick={() => setTransportMode("flight")} className={`rounded-lg px-3 py-2 text-xs font-semibold ${transportMode === "flight" ? "bg-primary text-white" : "border border-glass-border text-foreground-muted"}`}>✈️ Flights</button><button type="button" onClick={() => setTransportMode("train")} className={`rounded-lg px-3 py-2 text-xs font-semibold ${transportMode === "train" ? "bg-primary text-white" : "border border-glass-border text-foreground-muted"}`}>🚂 Trains</button><span className="text-xs text-foreground-muted">{itinerary.origin.name} → {itinerary.destination.name}</span></div>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end"><label className="flex-1 text-xs text-foreground-muted">Travel date<input type="date" value={transportDate} min={itinerary.start_date} onChange={(event) => setTransportDate(event.target.value)} className="mt-1 block w-full rounded-lg border border-glass-border bg-background/50 px-3 py-2 text-sm text-foreground" /></label><button type="submit" className="warm-button rounded-lg px-4 py-2.5 text-xs font-semibold text-white">Search {transportMode === "flight" ? "flights" : "trains"}</button></div>
          </form>
          {isTransportSearching ? <div className="place-discovery-loading" aria-live="polite"><span className="text-marigold">✦</span> Checking {transportMode === "flight" ? "flight" : "train"} options…</div> : transportResults.length ? <div className="mt-4 grid gap-3">{transportResults.map((option, index) => <div key={`${option.mode}-${option.provider}-${option.code || index}`}><TransportCard option={option} travelDate={transportDate} onClick={() => void selectTransport(option)} /><p className="mt-1 text-[10px] text-foreground-muted">Selecting updates the plan estimate. Booking remains with the linked provider.</p></div>)}</div> : <div className="workspace-empty-state mt-4 rounded-xl border border-dashed border-glass-border p-6 text-center"><p className="text-sm font-semibold text-foreground">No transport options returned.</p><p className="mt-1 text-xs text-foreground-muted">Try another date or check the provider links in the trip plan.</p></div>}
        </>}

        {activeTab === "stay" && <>
          <form onSubmit={(event) => { event.preventDefault(); setStaySearchNonce((value) => value + 1); }} className="mt-4 rounded-xl border border-glass-border bg-background/25 p-3">
            <div className="flex flex-col gap-2 sm:flex-row"><label className="flex-1 text-xs text-foreground-muted">Check in<input type="date" value={stayCheckIn} min={itinerary.start_date} onChange={(event) => setStayCheckIn(event.target.value)} className="mt-1 block w-full rounded-lg border border-glass-border bg-background/50 px-3 py-2 text-sm text-foreground" /></label><label className="flex-1 text-xs text-foreground-muted">Check out<input type="date" value={stayCheckOut} min={stayCheckIn} onChange={(event) => setStayCheckOut(event.target.value)} className="mt-1 block w-full rounded-lg border border-glass-border bg-background/50 px-3 py-2 text-sm text-foreground" /></label><button type="submit" className="warm-button self-end rounded-lg px-4 py-2.5 text-xs font-semibold text-white">Compare areas</button></div>
          </form>
          <div className="mt-4 rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-xs leading-relaxed text-foreground-secondary">Stay results are area-level planning estimates until a live hotel inventory provider is configured. Use <strong className="text-foreground">Search live</strong> to verify properties, current prices, taxes, and cancellation terms.</div>
          {isStaySearching ? <div className="place-discovery-loading" aria-live="polite"><span className="text-marigold">✦</span> Estimating stay areas in {itinerary.destination.name}…</div> : stayResults.length ? <div className="place-discovery-grid mt-4">{stayResults.map((stay) => <StayCard key={stay.id} stay={stay} isAdded={addedStayIds.has(stay.id)} isAdding={actionKey === `stay:${stay.id}`} onAdd={(value) => void addStay(value)} />)}</div> : <div className="workspace-empty-state mt-4 rounded-xl border border-dashed border-glass-border p-6 text-center"><p className="text-sm font-semibold text-foreground">No stay estimates yet.</p><p className="mt-1 text-xs text-foreground-muted">Choose a valid check-in and check-out window to compare areas.</p></div>}
        </>}

        {error && <p className="mt-3 rounded-lg border border-error/30 bg-error/10 p-3 text-xs leading-relaxed text-error" role="alert">{error}</p>}
        <p className="mt-5 text-[10px] leading-relaxed text-foreground-muted">Live availability and booking are always completed with the relevant provider. The planner stores choices and estimates so you can reshape the route safely.</p>
      </section>
    </div>
  );
}
