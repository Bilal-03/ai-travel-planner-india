"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  Account,
  api,
  AccommodationPreference,
  ApiError,
  DietaryPreference,
  PreferenceMemory,
  SavedTripSummary,
  TransportMode,
  TripPace,
} from "@/lib/api";

const inputClass = "mt-1 w-full rounded border border-glass-border bg-black/20 px-3 py-2 text-xs text-foreground outline-none focus:border-marigold";

export default function AccountPanel() {
  const [account, setAccount] = useState<Account | null>(null);
  const [preferences, setPreferences] = useState<PreferenceMemory | null>(null);
  const [history, setHistory] = useState<SavedTripSummary[]>([]);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [claimId, setClaimId] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadAccount = async () => {
    try {
      const current = await api.ensureAnonymousSession();
      setAccount(current);
      const [savedPreferences, savedTrips] = await Promise.all([api.getPreferences(), api.getSavedTrips()]);
      setPreferences(savedPreferences);
      setHistory(savedTrips);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Account memory is unavailable until the backend is running.");
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => void loadAccount(), 0);
    return () => window.clearTimeout(timer);
  }, []);

  const register = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const current = await api.registerAccount({ email, display_name: displayName || undefined });
      setAccount(current);
      setStatus("Your optional account is active; saved trips will follow this account.");
      setEmail("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The account could not be created.");
    } finally {
      setSaving(false);
    }
  };

  const updatePreferences = async (update: Parameters<typeof api.updatePreferences>[0]) => {
    setSaving(true);
    setError(null);
    try {
      setPreferences(await api.updatePreferences(update));
      setStatus("Preference memory updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Preferences could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const disableMemory = async () => {
    setSaving(true);
    try {
      setPreferences(await api.disablePreferenceMemory());
      setStatus("Preference memory is disabled and saved fields were cleared.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Preference memory could not be disabled.");
    } finally {
      setSaving(false);
    }
  };

  const enableMemory = async () => {
    await updatePreferences({ memory_enabled: true });
  };

  const deleteMemory = async () => {
    setSaving(true);
    try {
      setPreferences(await api.deletePreferences());
      setStatus("Remembered preferences deleted.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Remembered preferences could not be deleted.");
    } finally {
      setSaving(false);
    }
  };

  const deleteAccount = async () => {
    setSaving(true);
    try {
      await api.deleteAccount();
      setAccount(null);
      setPreferences(null);
      setHistory([]);
      setStatus("Account, saved trips, and preference memory deleted.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The account could not be deleted.");
    } finally {
      setSaving(false);
    }
  };

  const claimTrip = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!claimId.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.claimTrip(claimId.trim());
      setHistory(await api.getSavedTrips());
      setStatus("The anonymous trip is now attached to this account.");
      setClaimId("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That trip could not be claimed from this browser.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="mx-auto mt-8 max-w-[1180px] rounded-[6px] border border-glass-border bg-background/25 p-5 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.18em] text-foreground-muted">Optional account & memory</p>
          <h2 className="mt-2 text-xl font-semibold text-foreground">Keep control of what YatraAI remembers</h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-foreground-secondary">Anonymous sessions keep the planner usable. Save only explicit transport, hotel, budget, food, pace, accessibility, or departure-time preferences.</p>
        </div>
        {account && <span className="rounded-full border border-glass-border px-3 py-1 text-[10px] uppercase tracking-wide text-foreground-muted">{account.is_anonymous ? "Anonymous session" : account.email || "Account"}</span>}
      </div>

      {(status || error) && <p role={error ? "alert" : "status"} className={`mt-4 rounded border px-3 py-2 text-xs ${error ? "border-error/30 bg-error/10 text-error" : "border-success/30 bg-success/10 text-success"}`}>{error || status}</p>}

      {!account ? <p className="mt-5 text-sm text-foreground-muted">Start the backend to enable account continuity and preference memory.</p> : (
        <div className="mt-6 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          {account.is_anonymous && <form onSubmit={register} className="rounded border border-glass-border bg-black/10 p-4">
            <h3 className="font-semibold text-foreground">Create an optional account</h3>
            <p className="mt-1 text-xs text-foreground-muted">This upgrades the current anonymous session; it does not block trip planning.</p>
            <label className="mt-4 block text-xs text-foreground-secondary">Email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} className={inputClass} placeholder="you@example.com" /></label>
            <label className="mt-3 block text-xs text-foreground-secondary">Display name<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} className={inputClass} placeholder="Optional" /></label>
            <button type="submit" disabled={saving} className="mt-4 rounded bg-marigold px-4 py-2 text-xs font-bold uppercase tracking-wide text-[#24160a] disabled:opacity-50">{saving ? "Saving…" : "Create account"}</button>
          </form>}

          {preferences && <div className="rounded border border-glass-border bg-black/10 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold text-foreground">Explicit preference memory</h3><p className="mt-1 text-xs text-foreground-muted">{preferences.memory_enabled ? "Enabled — only the fields below are saved." : "Disabled — no preference fields are being used."}</p></div><div className="flex gap-2"><button type="button" onClick={preferences.memory_enabled ? disableMemory : enableMemory} disabled={saving} className="rounded border border-glass-border px-3 py-1.5 text-[10px] uppercase tracking-wide text-foreground-muted disabled:opacity-40">{preferences.memory_enabled ? "Disable" : "Enable"}</button><button type="button" onClick={deleteMemory} disabled={saving} className="rounded border border-error/40 px-3 py-1.5 text-[10px] uppercase tracking-wide text-error disabled:opacity-40">Delete memory</button></div></div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-foreground-secondary">Preferred transport<select value={preferences.preferred_transport || ""} disabled={!preferences.memory_enabled} onChange={(event) => void updatePreferences({ memory_enabled: true, preferred_transport: (event.target.value || null) as TransportMode | null })} className={inputClass}><option value="">No preference</option><option value="train">Train</option><option value="flight">Flight</option><option value="road">Road</option></select></label>
              <label className="text-xs text-foreground-secondary">Hotel category<select value={preferences.hotel_category || ""} disabled={!preferences.memory_enabled} onChange={(event) => void updatePreferences({ memory_enabled: true, hotel_category: (event.target.value || null) as AccommodationPreference | null })} className={inputClass}><option value="">No preference</option><option value="budget">Budget</option><option value="standard">Standard</option><option value="comfort">Comfort</option></select></label>
              <label className="text-xs text-foreground-secondary">Travel pace<select value={preferences.travel_pace || ""} disabled={!preferences.memory_enabled} onChange={(event) => void updatePreferences({ memory_enabled: true, travel_pace: (event.target.value || null) as TripPace | null })} className={inputClass}><option value="">No preference</option><option value="relaxed">Relaxed</option><option value="balanced">Balanced</option><option value="packed">Packed</option></select></label>
              <label className="text-xs text-foreground-secondary">Dietary preference<select value={preferences.dietary_preference || ""} disabled={!preferences.memory_enabled} onChange={(event) => void updatePreferences({ memory_enabled: true, dietary_preference: (event.target.value || null) as DietaryPreference | null })} className={inputClass}><option value="">No preference</option><option value="vegetarian">Vegetarian</option><option value="non_vegetarian">Non-vegetarian</option></select></label>
              <label className="text-xs text-foreground-secondary">Typical budget minimum<input type="number" min={0} value={preferences.typical_budget_min ?? ""} disabled={!preferences.memory_enabled} onChange={(event) => void updatePreferences({ memory_enabled: true, typical_budget_min: event.target.value ? Number(event.target.value) : null })} className={inputClass} /></label>
              <label className="text-xs text-foreground-secondary">Typical budget maximum<input type="number" min={0} value={preferences.typical_budget_max ?? ""} disabled={!preferences.memory_enabled} onChange={(event) => void updatePreferences({ memory_enabled: true, typical_budget_max: event.target.value ? Number(event.target.value) : null })} className={inputClass} /></label>
            </div>
            <label className="mt-3 block text-xs text-foreground-secondary">Accessibility requirements<textarea rows={2} value={preferences.accessibility_requirements || ""} disabled={!preferences.memory_enabled} onChange={(event) => setPreferences({ ...preferences, accessibility_requirements: event.target.value })} onBlur={() => void updatePreferences({ memory_enabled: true, accessibility_requirements: preferences.accessibility_requirements || null })} className={inputClass} placeholder="Only if you explicitly want this remembered" /></label>
            <label className="mt-3 block text-xs text-foreground-secondary">Preferred departure times<input value={preferences.preferred_departure_times.join(", ")} disabled={!preferences.memory_enabled} onChange={(event) => setPreferences({ ...preferences, preferred_departure_times: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} onBlur={() => void updatePreferences({ memory_enabled: true, preferred_departure_times: preferences.preferred_departure_times })} className={inputClass} placeholder="07:00, 10:00" /><span className="mt-1 block text-[11px] text-foreground-muted">Separate times with commas; this is saved only when you choose to keep it.</span></label>
          </div>}
        </div>
      )}

      {history.length > 0 && <div className="mt-6 rounded border border-glass-border bg-black/10 p-4"><h3 className="font-semibold text-foreground">Saved trip history</h3><ul className="mt-3 grid gap-2 sm:grid-cols-2">{history.map((trip) => <li key={`${trip.kind}-${trip.id}`} className="rounded border border-glass-border px-3 py-2 text-xs text-foreground-secondary"><span className="font-semibold text-foreground">{trip.origin} → {trip.destination}</span><span className="ml-2 text-foreground-muted">{trip.start_date}</span></li>)}</ul></div>}

      {account && <form onSubmit={claimTrip} className="mt-5 flex flex-wrap items-end gap-3 rounded border border-glass-border bg-black/10 p-4"><label className="min-w-[220px] flex-1 text-xs text-foreground-secondary">Claim a trip created in this browser<input value={claimId} onChange={(event) => setClaimId(event.target.value)} className={inputClass} placeholder="Trip ID" /></label><button type="submit" disabled={saving || !claimId.trim()} className="rounded border border-marigold/50 px-4 py-2 text-xs text-marigold disabled:opacity-40">Claim trip</button><p className="basis-full text-[11px] text-foreground-muted">The browser must still hold that trip&apos;s creator edit token.</p></form>}

      {account && <div className="mt-5 border-t border-glass-border pt-4"><button type="button" onClick={deleteAccount} disabled={saving} className="text-xs text-error underline decoration-error/40 underline-offset-4 disabled:opacity-40">Delete my account and saved trips</button></div>}
    </section>
  );
}
