import { TransportOption } from "./api";

export interface ProviderHandoff {
  url: string;
  label: string;
}
/**
 * Build a transparent search handoff. These links open a provider search or
 * route view; they never imply that YatraAI has held inventory or made a
 * booking.
 */
export function getTransportHandoff(option: TransportOption, travelDate?: string): ProviderHandoff {
  if (option.mode === "flight") {
    const dateSuffix = travelDate ? ` on ${travelDate}` : "";
    return {
      url: `https://www.google.com/travel/flights?q=${encodeURIComponent(`Flights from ${option.departure_city} to ${option.arrival_city}${dateSuffix}`)}`,
      label: "Check current fares",
    };
  }

  if (option.mode === "train") {
    return {
      url: "https://www.irctc.co.in/nget/train-search",
      label: "Search current trains",
    };
  }

  return {
    url: `https://www.google.com/maps/dir/${encodeURIComponent(option.departure_city)}/${encodeURIComponent(option.arrival_city)}`,
    label: "Open route in Maps",
  };
}
