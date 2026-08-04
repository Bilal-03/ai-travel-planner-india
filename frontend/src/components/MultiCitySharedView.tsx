"use client";

import { formatDate, formatINR, type MultiCityTrip } from "@/lib/api";
import ShareTrip from "@/components/ShareTrip";

export default function MultiCitySharedView({ trip }: { trip: MultiCityTrip }) {
  const route = [trip.origin.name, ...trip.destination_stays.map((stay) => stay.city.name), trip.origin.name].join(" → ");
  return (
    <main className="min-h-screen bg-background">
      <div className="gradient-hero px-4 py-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div><p className="text-xs uppercase tracking-[0.14em] text-foreground-muted">Shared multi-city trip</p><h1 className="mt-2 text-3xl font-bold text-foreground">{route}</h1><p className="mt-2 text-sm text-foreground-secondary">{formatDate(trip.start_date)} – {formatDate(trip.end_date)} · {trip.total_days} days · {formatINR(trip.budget.total_estimated)}</p></div>
          <ShareTrip tripId={trip.id} kind="multi_city" />
        </div>
      </div>
      <div className="mx-auto max-w-6xl px-4 py-8">
        <section className="grid gap-4 md:grid-cols-2">
          {trip.destination_stays.map((stay) => <article key={stay.id} className="glass rounded-xl p-4"><p className="text-xs uppercase tracking-wide text-marigold">{stay.nights} nights</p><h2 className="mt-1 text-lg font-semibold text-foreground">{stay.city.name}</h2><p className="mt-1 text-xs text-foreground-muted">{formatDate(stay.arrival_date)} – {formatDate(stay.departure_date)}</p>{stay.notes && <p className="mt-3 text-sm text-foreground-secondary">{stay.notes}</p>}</article>)}
        </section>
        <section className="mt-8"><h2 className="text-xl font-bold text-foreground">Itinerary days</h2><div className="mt-4 grid gap-4 md:grid-cols-2">{trip.itinerary_days.map((day) => <article key={`${day.day_number}-${day.date}`} className="glass rounded-xl p-4"><p className="text-xs uppercase tracking-wide text-marigold">Day {day.day_number} · {formatDate(day.date)}</p><h3 className="mt-1 font-semibold text-foreground">{day.destination?.name || "Return journey"}</h3>{day.visits.length ? <ul className="mt-3 space-y-2 text-sm text-foreground-secondary">{day.visits.map((visit) => <li key={visit.id}>• {visit.poi.name}</li>)}</ul> : <p className="mt-3 text-xs text-foreground-muted">Keep this day flexible for the travel leg.</p>}</article>)}</div></section>
      </div>
    </main>
  );
}
