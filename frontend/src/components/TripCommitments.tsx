"use client";

import { Itinerary, ItineraryItem, TransportOption, formatDate, formatINR } from "@/lib/api";
import { getTransportHandoff } from "@/lib/providerLinks";
import { track } from "@/lib/analytics";
import DataStatusBadge from "./DataStatusBadge";
import EstimateDisclaimer from "./EstimateDisclaimer";
import FreshnessTimestamp from "./FreshnessTimestamp";
import ProviderAttribution from "./ProviderAttribution";

interface TripCommitmentsProps {
  itinerary: Itinerary;
  compact?: boolean;
}
function metadataString(item: ItineraryItem, key: string): string | null {
  const value = item.metadata?.[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function metadataNumber(item: ItineraryItem, key: string): number | null {
  const value = item.metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function transportIcon(option: TransportOption): string {
  if (option.mode === "flight") return "✈️";
  if (option.mode === "train") return "🚂";
  return "🚗";
}

function transportLabel(option: TransportOption): string {
  if (option.mode === "flight") return "Flight";
  if (option.mode === "train") return "Train";
  return "Road transfer";
}

function TransportCommitment({ itinerary, option }: { itinerary: Itinerary; option: TransportOption }) {
  const handoff = getTransportHandoff(option, itinerary.start_date);
  const roundTripEstimate = option.price * (itinerary.members || 2) * 2;
  return (
    <article data-testid="transport-commitment" className="rounded-xl border border-primary/25 bg-primary/5 p-3.5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-lg" aria-hidden="true">{transportIcon(option)}</div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-foreground">Selected {transportLabel(option)}</h3>
            <span className="rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-success">In plan</span>
            <DataStatusBadge provenance={option.provenance} compact />
          </div>
          <p className="mt-1 text-xs text-foreground-secondary">{option.provider}{option.code ? ` · ${option.code}` : ""}</p>
          <p className="mt-2 text-sm font-medium text-foreground">{itinerary.origin.name} → {itinerary.destination.name}</p>
          <p className="mt-1 text-xs text-foreground-muted">Outbound {formatDate(itinerary.start_date)} · return {formatDate(itinerary.end_date)}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-sm font-bold text-foreground">{formatINR(roundTripEstimate)}</p>
          <p className="text-[10px] text-foreground-muted">round trip estimate</p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
        <ProviderAttribution provenance={option.provenance} />
        <FreshnessTimestamp provenance={option.provenance} />
      </div>
      <EstimateDisclaimer provenance={option.field_data_provenance?.fare || option.provenance} className="mt-2" />
      <a
        href={handoff.url}
        target="_blank"
        rel="noreferrer"
        onClick={() => track("provider_link_clicked", { tripId: itinerary.id, kind: "single", metadata: { provider: option.provider, source: "transport_commitment", estimated_data: option.is_fallback } })}
        className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary-light"
      >
        {handoff.label} ↗
      </a>
    </article>
  );
}

function StayCommitment({ itinerary, item }: { itinerary: Itinerary; item: ItineraryItem }) {
  const area = metadataString(item, "area") || "Destination stay";
  const checkIn = metadataString(item, "check_in");
  const checkOut = metadataString(item, "check_out");
  const nights = metadataNumber(item, "nights");
  const rooms = metadataNumber(item, "rooms");
  const totalPrice = metadataNumber(item, "total_price") || 0;
  const bookingUrl = metadataString(item, "booking_url");

  return (
    <article data-testid="stay-commitment" className="rounded-xl border border-teal-400/25 bg-teal-400/5 p-3.5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-teal-400/15 text-lg" aria-hidden="true">🛏️</div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-foreground">{item.title}</h3>
            <span className="rounded-full bg-amber-400/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-200">Estimate saved</span>
          </div>
          <p className="mt-1 text-xs text-foreground-secondary">{area}{nights ? ` · ${nights} night${nights === 1 ? "" : "s"}` : ""}{rooms ? ` · ${rooms} room${rooms === 1 ? "" : "s"}` : ""}</p>
          {checkIn && checkOut && <p className="mt-1 text-xs text-foreground-muted">{formatDate(checkIn)} → {formatDate(checkOut)}</p>}
        </div>
        <div className="shrink-0 text-right">
          <p className="text-sm font-bold text-foreground">{formatINR(totalPrice)}</p>
          <p className="text-[10px] text-foreground-muted">trip estimate</p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
        <ProviderAttribution provenance={item.provenance} />
        <FreshnessTimestamp provenance={item.provenance} />
      </div>
      <EstimateDisclaimer provenance={item.provenance} className="mt-2" />
      {bookingUrl && (
        <a
          href={bookingUrl}
          target="_blank"
          rel="noreferrer"
          onClick={() => track("provider_link_clicked", { tripId: itinerary.id, kind: "single", metadata: { provider: "Google Hotels", source: "stay_commitment", estimated_data: true } })}
          className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary-light"
        >
          Search live stays ↗
        </a>
      )}
    </article>
  );
}

export default function TripCommitments({ itinerary, compact = false }: TripCommitmentsProps) {
  const stayItems = (itinerary.items || []).filter((item) => item.item_type === "stay");
  const commitmentCount = stayItems.length + (itinerary.selected_transport ? 1 : 0);
  if (commitmentCount === 0) return null;

  return (
    <section data-testid="trip-commitments" aria-labelledby="trip-commitments-heading" className={`rounded-xl border border-glass-border bg-glass-bg p-4 ${compact ? "" : "sm:p-5"}`}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-marigold">Decision log</p>
          <h2 id="trip-commitments-heading" className="mt-1 text-xl font-bold text-foreground">Trip commitments</h2>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed text-foreground-secondary">These choices stay attached while the planner reshapes your days. They are planning records, not reservations.</p>
        </div>
        <span className="rounded-full border border-glass-border bg-background/35 px-2.5 py-1 text-[10px] font-semibold text-foreground-muted">{commitmentCount} saved</span>
      </div>
      <div className={`mt-4 grid gap-3 ${compact ? "grid-cols-1" : "xl:grid-cols-2"}`}>
        {itinerary.selected_transport && <TransportCommitment itinerary={itinerary} option={itinerary.selected_transport} />}
        {stayItems.map((item) => <StayCommitment key={item.id} itinerary={itinerary} item={item} />)}
      </div>
      <p className="mt-3 text-[11px] leading-relaxed text-foreground-muted">Before paying, confirm live price, schedule, availability, taxes, cancellation terms, and the provider’s booking conditions.</p>
    </section>
  );
}
