import { commitmentsForTrip, isOfflineSnapshotStale, type OfflineTripSnapshot } from "@/lib/offline";

export default function OfflineEssentials({ snapshot }: { snapshot: OfflineTripSnapshot }) {
  const commitments = snapshot.essentials.commitments || commitmentsForTrip(snapshot.trip);
  const stale = isOfflineSnapshotStale(snapshot.savedAt);
  return (
    <section data-testid="offline-essentials" className="mb-8 rounded-xl border border-warning/30 bg-warning/5 p-4" aria-label="Offline trip essentials">
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="text-xl">📡</span>
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-foreground">Offline trip essentials</h2>
          <p className="mt-1 text-xs text-foreground-muted">Saved {new Date(snapshot.savedAt).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}{stale ? " · older than 24 hours" : ""}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-4 text-xs sm:grid-cols-3">
        <div>
          <h3 className="font-semibold text-foreground">Addresses</h3>
          <ul className="mt-2 space-y-1 text-foreground-secondary">{snapshot.essentials.addresses.map((address) => <li key={address}>• {address}</li>)}</ul>
        </div>
        <div>
          <h3 className="font-semibold text-foreground">Trip commitments</h3>
          {!commitments.transport && commitments.stays.length === 0 ? (
            <p className="mt-2 text-foreground-muted">No transport or stay choices saved.</p>
          ) : (
            <ul className="mt-2 space-y-1 text-foreground-secondary">
              {commitments.transport && <li>• {commitments.transport}</li>}
              {commitments.stays.map((stay) => <li key={stay}>• {stay}</li>)}
            </ul>
          )}
        </div>
        <div>
          <h3 className="font-semibold text-foreground">Emergency notes</h3>
          <ul className="mt-2 space-y-1 text-foreground-secondary">{snapshot.essentials.emergencyNotes.map((note) => <li key={note}>• {note}</li>)}</ul>
        </div>
      </div>
    </section>
  );
}
