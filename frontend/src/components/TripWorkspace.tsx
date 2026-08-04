"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import ItineraryTimeline from "@/components/ItineraryTimeline";
import TransportCard from "@/components/TransportCard";
import BudgetBreakdown from "@/components/BudgetBreakdown";
import ShareTrip from "@/components/ShareTrip";
import TripConversation from "@/components/TripConversation";
import { DestinationInspiration, PackingAndPrint } from "@/components/TripEnhancements";
import {
  api,
  ApiError,
  Itinerary,
  TransportOption,
  formatDate,
  formatINR,
  getVibeEmoji,
} from "@/lib/api";
import { track } from "@/lib/analytics";

const TripMap = dynamic(() => import("@/components/TripMap"), { ssr: false });

type WorkspaceTab = "plan" | "map" | "budget" | "chat";

interface TripWorkspaceProps {
  itinerary: Itinerary;
  onUpdate: (itinerary: Itinerary) => void;
  onNewTrip: () => void;
  onTransportSelect: (option: TransportOption) => Promise<void>;
}

interface WorkspaceContentProps {
  itinerary: Itinerary;
  onUpdate: (itinerary: Itinerary) => void;
  onTransportSelect: (option: TransportOption) => Promise<void>;
  onActivityEdit: (instruction: string) => Promise<void>;
  isEditing: boolean;
}

function WorkspaceTabs({ activeTab, onChange }: { activeTab: WorkspaceTab; onChange: (tab: WorkspaceTab) => void }) {
  const tabs: { id: WorkspaceTab; label: string; icon: string }[] = [
    { id: "plan", label: "Plan", icon: "📅" },
    { id: "map", label: "Map", icon: "🗺️" },
    { id: "budget", label: "Budget", icon: "💰" },
    { id: "chat", label: "Chat", icon: "✦" },
  ];

  return (
    <nav className="workspace-tabs no-scrollbar flex gap-1 overflow-x-auto rounded-xl border border-glass-border bg-glass-bg p-1 lg:hidden" aria-label="Trip workspace sections">
      {tabs.map((tab) => (
        <button key={tab.id} type="button" onClick={() => onChange(tab.id)} aria-current={activeTab === tab.id ? "page" : undefined} className={`flex min-w-[76px] flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2.5 text-xs font-semibold transition ${activeTab === tab.id ? "bg-primary text-white shadow-md" : "text-foreground-muted hover:bg-glass-highlight hover:text-foreground"}`}>
          <span aria-hidden="true">{tab.icon}</span>{tab.label}
        </button>
      ))}
    </nav>
  );
}

function TravelTips({ itinerary }: { itinerary: Itinerary }) {
  if (!itinerary.generation_notes.length) return null;
  return (
    <section className="workspace-panel rounded-xl border border-glass-border bg-glass-bg p-4">
      <h2 className="text-sm font-semibold text-foreground">💡 What to keep in mind</h2>
      <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-foreground-muted">
        {itinerary.generation_notes.slice(0, 4).map((note, index) => (
          <li key={`${note}-${index}`} className="flex items-start gap-2"><span className="mt-0.5 text-accent">•</span><span>{note}</span></li>
        ))}
      </ul>
    </section>
  );
}

function JourneySummary({ itinerary }: { itinerary: Itinerary }) {
  if (!itinerary.selected_transport) return null;
  return (
    <section className="rounded-xl border border-primary/30 bg-primary/5 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-primary">Recommended journey</p>
          <h2 className="mt-1 text-lg font-bold text-foreground">A route that fits the brief.</h2>
        </div>
        <span className="rounded-full bg-success/15 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-success">Selected</span>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg bg-background/35 p-3">
          <p className="text-[11px] text-foreground-muted">Outbound · {itinerary.start_date}</p>
          <p className="mt-1 text-sm font-semibold text-foreground">{itinerary.origin.name} → {itinerary.destination.name}</p>
          <p className="mt-1 text-xs text-foreground-secondary">{itinerary.selected_transport.provider} · {formatINR(itinerary.selected_transport.price)} per person</p>
        </div>
        <div className="rounded-lg bg-background/35 p-3">
          <p className="text-[11px] text-foreground-muted">Return · {itinerary.end_date}</p>
          <p className="mt-1 text-sm font-semibold text-foreground">{itinerary.destination.name} → {itinerary.origin.name}</p>
          <p className="mt-1 text-xs text-foreground-secondary">Round-trip budget includes the selected option.</p>
        </div>
      </div>
      <div className="mt-3 flex items-start gap-2 rounded-lg border border-glass-border bg-background/30 p-3 text-xs leading-relaxed text-foreground-secondary">
        <span aria-hidden="true">✦</span>
        <p><strong className="text-foreground">Why this option?</strong> It remains within the working budget, keeps the journey aligned with your {itinerary.travel_preference} preference, and is the most balanced available option for these dates. Verify live fares and availability before booking.</p>
      </div>
    </section>
  );
}

function PlanContent({ itinerary, onUpdate, onTransportSelect, onActivityEdit, isEditing }: WorkspaceContentProps) {
  const alternatives = itinerary.transport_options.filter((option) => option.provider !== itinerary.selected_transport?.provider || option.code !== itinerary.selected_transport?.code);

  return (
    <div className="space-y-5">
      <JourneySummary itinerary={itinerary} />
      <TravelTips itinerary={itinerary} />
      <DestinationInspiration itinerary={itinerary} />
      <section aria-labelledby="workspace-itinerary-heading">
        <ItineraryTimeline
          dayPlans={itinerary.day_plans}
          headingId="workspace-itinerary-heading"
          editingEnabled
          onActivityEdit={onActivityEdit}
          isEditing={isEditing}
          action={<span className="hidden text-xs text-foreground-muted sm:inline">Drag a stop or open Edit</span>}
        />
      </section>
      {alternatives.length > 0 && (
        <section aria-labelledby="workspace-transport-heading">
          <div className="mb-3 flex items-end justify-between gap-3">
            <div><p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-marigold">Compare before you commit</p><h2 id="workspace-transport-heading" className="mt-1 text-xl font-bold text-foreground">Other ways to get there</h2></div>
            <span className="text-xs text-foreground-muted">{alternatives.length} alternative{alternatives.length === 1 ? "" : "s"}</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {alternatives.map((option, index) => <TransportCard key={`${option.provider}-${option.code || index}`} option={option} travelDate={itinerary.start_date} onClick={() => void onTransportSelect(option)} />)}
          </div>
        </section>
      )}
      <section className="grid gap-3 print:hidden sm:grid-cols-2">
        <PackingAndPrint itinerary={itinerary} onUpdate={onUpdate} />
      </section>
    </div>
  );
}

function OverviewRail({ itinerary }: { itinerary: Itinerary }) {
  return (
    <aside className="space-y-4" aria-label="Trip overview">
      <div className="workspace-panel overflow-hidden rounded-xl border border-glass-border bg-glass-bg">
        <div className="border-b border-glass-border px-4 py-3"><h2 className="text-sm font-semibold text-foreground">🗺️ Route at a glance</h2><p className="mt-1 text-xs text-foreground-muted">Filter stops by day on the map.</p></div>
        <TripMap center={itinerary.destination.coordinates} dayPlans={itinerary.day_plans} routeSegments={itinerary.route_segments} destination={itinerary.destination.name} />
      </div>
      <BudgetBreakdown budget={itinerary.budget} totalBudget={itinerary.budget.total_estimated + itinerary.budget.remaining} />
      {itinerary.selected_transport && (
        <div className="workspace-panel rounded-xl border border-glass-border bg-glass-bg p-4">
          <div className="flex items-center justify-between gap-2"><h2 className="text-sm font-semibold text-foreground">🚆 Selected transport</h2><span className="text-xs text-success">In plan</span></div>
          <p className="mt-2 text-sm font-medium text-foreground">{itinerary.selected_transport.provider}</p>
          <p className="mt-1 text-xs text-foreground-secondary">{itinerary.selected_transport.mode} · {formatINR(itinerary.selected_transport.price)} per person</p>
          <p className="mt-3 text-xs leading-relaxed text-foreground-muted">Transport choices are re-budgeted and rechecked on the server when you select another option.</p>
        </div>
      )}
      <div className="workspace-panel rounded-xl border border-glass-border bg-glass-bg p-4">
        <h2 className="text-sm font-semibold text-foreground">Trip snapshot</h2>
        <dl className="mt-3 space-y-2 text-xs">
          <div className="flex justify-between gap-3"><dt className="text-foreground-muted">Travellers</dt><dd className="font-medium text-foreground">{itinerary.adults + itinerary.children}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-foreground-muted">Vibe</dt><dd className="text-foreground">{itinerary.vibes.map((vibe) => getVibeEmoji(vibe)).join(" ") || "—"}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-foreground-muted">Data note</dt><dd className="text-right text-foreground-secondary">Live where available; estimates are labelled</dd></div>
        </dl>
      </div>
    </aside>
  );
}

export default function TripWorkspace({ itinerary, onUpdate, onNewTrip, onTransportSelect }: TripWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("plan");
  const [isEditing, setIsEditing] = useState(false);
  const [refinementError, setRefinementError] = useState<string | null>(null);
  const [previousItinerary, setPreviousItinerary] = useState<Itinerary | null>(null);

  const refine = async (instruction: string) => {
    setIsEditing(true);
    setRefinementError(null);
    const before = itinerary;
    try {
      const updated = await api.refineTrip(itinerary.id, instruction);
      setPreviousItinerary(before);
      onUpdate(updated);
      const lower = instruction.toLowerCase();
      if (lower.includes("replace")) track("activity_replaced", { tripId: itinerary.id, kind: "single", metadata: { accepted: true } });
      if (lower.includes("regenerate day")) track("day_regenerated", { tripId: itinerary.id, kind: "single", metadata: { accepted: true } });
    } catch (error) {
      setRefinementError(error instanceof ApiError ? error.message : "Couldn’t apply that change. Please try again.");
    } finally {
      setIsEditing(false);
    }
  };

  const undo = async () => {
    if (!previousItinerary || isEditing) return;
    setIsEditing(true);
    setRefinementError(null);
    try {
      const restored = await api.undoTrip(itinerary.id);
      onUpdate(restored);
      setPreviousItinerary(null);
    } catch (error) {
      setRefinementError(error instanceof ApiError ? error.message : "Couldn’t undo the latest change.");
    } finally {
      setIsEditing(false);
    }
  };

  const conversation = (
    <TripConversation
      itinerary={itinerary}
      onRefine={refine}
      onUndo={undo}
      isRefining={isEditing}
      refinementError={refinementError}
      canUndo={Boolean(previousItinerary)}
    />
  );

  return (
    <section id="trip-workspace" className="gradient-hero min-h-[calc(100vh-73px)] px-3 py-5 sm:px-5 sm:py-8 lg:px-7">
      <div className="mx-auto max-w-[1440px]">
        <motion.header initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="mb-5 flex flex-col gap-4 sm:mb-7 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0">
            <button type="button" onClick={onNewTrip} className="mb-2 text-sm text-foreground-muted transition hover:text-foreground">← New trip</button>
            <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.16em] text-marigold">Trip workspace · {itinerary.total_days} days</p>
            <h1 className="mt-1 truncate font-[family-name:var(--font-teko)] text-[clamp(2.5rem,5vw,4.4rem)] font-semibold uppercase leading-none text-foreground"><span className="gradient-text">{itinerary.origin.name} → {itinerary.destination.name}</span></h1>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-foreground-secondary sm:text-sm"><span>📅 {formatDate(itinerary.start_date)} – {formatDate(itinerary.end_date)}</span><span className="hidden sm:inline">•</span><span>💰 {formatINR(itinerary.budget.total_estimated)} planned</span></div>
          </div>
          <div className="flex items-center gap-2 print:hidden"><span className="hidden rounded-full border border-glass-border bg-glass-bg px-3 py-2 text-xs text-foreground-muted sm:inline">No sign-up · private edits</span><ShareTrip tripId={itinerary.id} /></div>
        </motion.header>

        <WorkspaceTabs activeTab={activeTab} onChange={setActiveTab} />

        <div className="mt-5 hidden items-start gap-5 lg:grid lg:grid-cols-[250px_minmax(0,1fr)_330px] xl:grid-cols-[270px_minmax(0,1fr)_360px]">
          {conversation}
          <main className="min-w-0"><PlanContent itinerary={itinerary} onUpdate={onUpdate} onTransportSelect={onTransportSelect} onActivityEdit={refine} isEditing={isEditing} /></main>
          <OverviewRail itinerary={itinerary} />
        </div>

        <div className="mt-5 lg:hidden">
          {activeTab === "plan" && <PlanContent itinerary={itinerary} onUpdate={onUpdate} onTransportSelect={onTransportSelect} onActivityEdit={refine} isEditing={isEditing} />}
          {activeTab === "map" && <div className="rounded-xl border border-glass-border bg-glass-bg p-1"><TripMap center={itinerary.destination.coordinates} dayPlans={itinerary.day_plans} routeSegments={itinerary.route_segments} destination={itinerary.destination.name} /></div>}
          {activeTab === "budget" && <div className="space-y-4"><BudgetBreakdown budget={itinerary.budget} totalBudget={itinerary.budget.total_estimated + itinerary.budget.remaining} />{itinerary.selected_transport && <TransportCard option={itinerary.selected_transport} travelDate={itinerary.start_date} isSelected />}</div>}
          {activeTab === "chat" && conversation}
        </div>
      </div>
    </section>
  );
}
