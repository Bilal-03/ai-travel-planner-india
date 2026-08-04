import type { OfflineTripSnapshot } from "@/lib/offline";

export default function OfflineEssentials({ snapshot }: { snapshot: OfflineTripSnapshot }) {
  return (
    <section className="mb-8 rounded-xl border border-warning/30 bg-warning/5 p-4" aria-label="Offline trip essentials">
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="text-xl">📡</span>
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-foreground">Offline trip essentials</h2>
          <p className="mt-1 text-xs text-foreground-muted">Saved {new Date(snapshot.savedAt).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-4 text-xs sm:grid-cols-2">
        <div>
          <h3 className="font-semibold text-foreground">Addresses</h3>
          <ul className="mt-2 space-y-1 text-foreground-secondary">{snapshot.essentials.addresses.map((address) => <li key={address}>• {address}</li>)}</ul>
        </div>
        <div>
          <h3 className="font-semibold text-foreground">Emergency notes</h3>
          <ul className="mt-2 space-y-1 text-foreground-secondary">{snapshot.essentials.emergencyNotes.map((note) => <li key={note}>• {note}</li>)}</ul>
        </div>
      </div>
    </section>
  );
}
