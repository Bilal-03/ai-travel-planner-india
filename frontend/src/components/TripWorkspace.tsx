"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import ItineraryTimeline from "@/components/ItineraryTimeline";
import TransportCard from "@/components/TransportCard";
import TripCommitments from "@/components/TripCommitments";
import BudgetBreakdown from "@/components/BudgetBreakdown";
import ShareTrip from "@/components/ShareTrip";
import TripConversation from "@/components/TripConversation";
import PlaceDiscovery, { SavedPlacesPanel } from "@/components/PlaceDiscovery";
import { DestinationInspiration, PackingAndPrint } from "@/components/TripEnhancements";
import {
  api,
  ApiError,
  Itinerary,
  TransportOption,
  formatDate,
  formatINR,
} from "@/lib/api";
import { track } from "@/lib/analytics";

const TripMap = dynamic(() => import("@/components/TripMap"), { ssr: false });

type WorkspaceTab = "plan" | "overview" | "map" | "saved" | "budget" | "chat";
type WorkspaceRightTab = "plan" | "overview" | "saved";

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
  onPlanSelect: (planId: string) => Promise<void>;
  isPlanSelecting: boolean;
  onActivityEdit: (instruction: string) => Promise<void>;
  isEditing: boolean;
}

function WorkspaceTabs({ activeTab, onChange }: { activeTab: WorkspaceTab; onChange: (tab: WorkspaceTab) => void }) {
  const tabs: { id: WorkspaceTab; label: string; icon: string }[] = [
    { id: "plan", label: "Plan", icon: "📅" },
    { id: "overview", label: "Overview", icon: "✦" },
    { id: "map", label: "Map", icon: "🗺️" },
    { id: "saved", label: "Saved", icon: "🔖" },
    { id: "budget", label: "Budget", icon: "💰" },
    { id: "chat", label: "Chat", icon: "✦" },
  ];

  return (
    <nav className="workspace-tabs print-hidden no-scrollbar flex gap-1 overflow-x-auto rounded-xl border border-glass-border bg-glass-bg p-1 lg:hidden" aria-label="Trip workspace sections">
      {tabs.map((tab) => (
        <button data-testid={`workspace-mobile-tab-${tab.id}`} key={tab.id} type="button" onClick={() => onChange(tab.id)} aria-current={activeTab === tab.id ? "page" : undefined} className={`flex min-w-[78px] flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2.5 text-xs font-semibold transition ${activeTab === tab.id ? "bg-primary text-white shadow-md" : "text-foreground-muted hover:bg-glass-highlight hover:text-foreground"}`}>
          <span aria-hidden="true">{tab.icon}</span>{tab.label}
        </button>
      ))}
    </nav>
  );
}

function WorkspaceRightTabs({ activeTab, onChange, onAddPlace }: { activeTab: WorkspaceRightTab; onChange: (tab: WorkspaceRightTab) => void; onAddPlace: () => void }) {
  const tabs: { id: WorkspaceRightTab; label: string }[] = [
    { id: "overview", label: "Trip overview" },
    { id: "plan", label: "Plan" },
    { id: "saved", label: "Saved" },
  ];

  return (
    <nav className="workspace-right-tabs print-hidden" aria-label="Itinerary workspace view">
      <div className="flex items-center gap-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            aria-current={activeTab === tab.id ? "page" : undefined}
            className={activeTab === tab.id ? "workspace-right-tab workspace-right-tab-active" : "workspace-right-tab"}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2">
        <span className="hidden text-[10px] font-[family-name:var(--font-space-mono)] uppercase tracking-[0.14em] text-foreground-muted sm:inline">Live workspace</span>
        <button type="button" onClick={onAddPlace} aria-label="Add a place to itinerary" className="workspace-add-button rounded-lg px-3 py-2 text-xs font-semibold text-white">+ Add</button>
      </div>
    </nav>
  );
}

function WorkspaceTopbar({ itinerary, onNewTrip }: { itinerary: Itinerary; onNewTrip: () => void }) {
  return (
    <motion.header initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="workspace-topbar">
      <div className="flex min-w-0 items-center gap-3">
        <button type="button" onClick={onNewTrip} aria-label="Start a new trip" className="workspace-brand-mark">
          <span aria-hidden="true">✦</span>
        </button>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.16em] text-marigold">Trip workspace</p>
            <span className="hidden text-[10px] text-foreground-muted sm:inline">·</span>
            <span className="hidden text-[10px] text-foreground-muted sm:inline">Private planning board</span>
          </div>
          <h1 className="mt-0.5 truncate text-xl font-bold tracking-tight text-foreground sm:text-2xl">{itinerary.origin.name} → {itinerary.destination.name}</h1>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-foreground-secondary">
            <span>{formatDate(itinerary.start_date)} – {formatDate(itinerary.end_date)}</span>
            <span aria-hidden="true">·</span>
            <span>{itinerary.total_days} days</span>
            <span aria-hidden="true">·</span>
            <span>{formatINR(itinerary.budget.total_estimated)} planned</span>
          </div>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2 print:hidden">
        <span className="hidden rounded-full border border-glass-border bg-glass-bg px-3 py-2 text-xs text-foreground-muted xl:inline">No sign-up · private edits</span>
        <ShareTrip tripId={itinerary.id} />
      </div>
    </motion.header>
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

function PlanOptions({ itinerary, onPlanSelect, isPlanSelecting }: Pick<WorkspaceContentProps, "itinerary" | "onPlanSelect" | "isPlanSelecting">) {
  const options = itinerary.plan_options || [];
  if (options.length <= 1) return null;
  return (
    <section aria-labelledby="plan-options-heading" className="rounded-xl border border-marigold/30 bg-marigold/5 p-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-marigold">Choose your day shape</p><h2 id="plan-options-heading" className="mt-1 text-xl font-bold text-foreground">Three ways to experience the trip</h2></div>
        <span className="text-xs text-foreground-muted">Members: {itinerary.members || 2}</span>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {options.map((option) => {
          const selected = itinerary.selected_plan_id === option.id;
          return (
            <button key={option.id} type="button" onClick={() => void onPlanSelect(option.id)} disabled={isPlanSelecting || selected} className={`rounded-lg border p-3 text-left transition ${selected ? "border-marigold bg-marigold/15" : "border-glass-border bg-background/25 hover:border-marigold/70"} disabled:cursor-not-allowed disabled:opacity-80`}>
              <div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold text-foreground">{option.title}</span>{selected && <span className="text-[10px] font-bold uppercase tracking-wide text-marigold">Selected</span>}</div>
              <p className="mt-2 text-xs leading-relaxed text-foreground-secondary">{option.description}</p>
              <p className="mt-3 text-xs font-semibold text-foreground">{formatINR(option.budget.total_estimated)} estimated</p>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function PlanContent({ itinerary, onUpdate, onTransportSelect, onPlanSelect, isPlanSelecting, onActivityEdit, isEditing }: WorkspaceContentProps) {
  const alternatives = itinerary.transport_options.filter((option) => option.provider !== itinerary.selected_transport?.provider || option.code !== itinerary.selected_transport?.code);

  return (
    <div className="space-y-5">
      <PlanOptions itinerary={itinerary} onPlanSelect={onPlanSelect} isPlanSelecting={isPlanSelecting} />
      <TripCommitments itinerary={itinerary} />
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
            {alternatives.map((option, index) => <TransportCard key={`${option.provider}-${option.code || index}`} option={option} travelDate={itinerary.start_date} tripId={itinerary.id} onClick={() => void onTransportSelect(option)} />)}
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
    <aside className="workspace-overview space-y-4" aria-label="Trip overview">
      <section className="workspace-panel rounded-xl border border-glass-border bg-glass-bg p-4">
        <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-marigold">Trip overview</p>
        <h2 className="mt-1 text-xl font-bold text-foreground">A clear route, one place to adjust it.</h2>
        <p className="mt-2 text-sm leading-relaxed text-foreground-secondary">The map above follows your stops. Use Plan to inspect each day, or ask the planner to reshape the route in plain language.</p>
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
          <div className="rounded-lg bg-background/45 p-3"><span className="block text-foreground-muted">Destination</span><strong className="mt-1 block text-foreground">{itinerary.destination.name}</strong></div>
          <div className="rounded-lg bg-background/45 p-3"><span className="block text-foreground-muted">Stops</span><strong className="mt-1 block text-foreground">{itinerary.day_plans.reduce((count, day) => count + day.activities.length, 0)} planned</strong></div>
        </div>
      </section>
      <BudgetBreakdown budget={itinerary.budget} totalBudget={itinerary.budget.total_estimated + itinerary.budget.remaining} />
      <TripCommitments itinerary={itinerary} compact />
      <div className="workspace-panel rounded-xl border border-glass-border bg-glass-bg p-4">
        <h2 className="text-sm font-semibold text-foreground">Trip snapshot</h2>
        <dl className="mt-3 space-y-2 text-xs">
          <div className="flex justify-between gap-3"><dt className="text-foreground-muted">Members</dt><dd className="font-medium text-foreground">{itinerary.members || 2}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-foreground-muted">Plan</dt><dd className="text-right text-foreground">{(itinerary.plan_options || []).find((option) => option.id === itinerary.selected_plan_id)?.title || "Selected route"}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-foreground-muted">Data note</dt><dd className="text-right text-foreground-secondary">Live where available; estimates are labelled</dd></div>
        </dl>
      </div>
    </aside>
  );
}

function WorkspaceMapPane({ itinerary }: { itinerary: Itinerary }) {
  return (
    <div className="workspace-map-frame print-hidden">
      <div className="workspace-map-toolbar">
        <div className="min-w-0">
          <p className="font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-foreground-muted">Route at a glance</p>
          <p className="truncate text-sm font-semibold text-foreground">{itinerary.origin.name} → {itinerary.destination.name}</p>
        </div>
        <span className="rounded-full border border-success/25 bg-success/10 px-2.5 py-1 text-[10px] font-semibold text-success">{itinerary.day_plans.length} days mapped</span>
      </div>
      <TripMap compact center={itinerary.destination.coordinates} dayPlans={itinerary.day_plans} routeSegments={itinerary.route_segments} destination={itinerary.destination.name} />
    </div>
  );
}

export default function TripWorkspace({ itinerary, onUpdate, onNewTrip, onTransportSelect }: TripWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("plan");
  const [rightTab, setRightTab] = useState<WorkspaceRightTab>("plan");
  const [isEditing, setIsEditing] = useState(false);
  const [refinementError, setRefinementError] = useState<string | null>(null);
  const [previousItinerary, setPreviousItinerary] = useState<Itinerary | null>(null);
  const [isPlanSelecting, setIsPlanSelecting] = useState(false);
  const [isPlaceDiscoveryOpen, setIsPlaceDiscoveryOpen] = useState(false);

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

  const selectPlan = async (planId: string) => {
    if (planId === itinerary.selected_plan_id) return;
    setIsPlanSelecting(true);
    setRefinementError(null);
    try {
      onUpdate(await api.selectPlan(itinerary.id, planId));
      track("plan_selected", { tripId: itinerary.id, kind: "single", metadata: { plan_id: planId } });
    } catch (error) {
      setRefinementError(error instanceof ApiError ? error.message : "Couldn’t switch plans. Please try again.");
    } finally {
      setIsPlanSelecting(false);
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
    <section id="trip-workspace" className="workspace-page gradient-hero min-h-[calc(100vh-73px)] px-3 py-4 sm:px-5 sm:py-6 lg:px-7">
      <div className="mx-auto max-w-[1600px]">
        <WorkspaceTopbar itinerary={itinerary} onNewTrip={onNewTrip} />

        <WorkspaceTabs activeTab={activeTab} onChange={setActiveTab} />

        <div data-testid="workspace-shell" className="workspace-shell mt-4 hidden lg:grid">
          <div className="workspace-conversation-column print-hidden min-h-0">{conversation}</div>
          <section className="workspace-right-pane" aria-label="Trip map and itinerary">
            <WorkspaceMapPane itinerary={itinerary} />
            <WorkspaceRightTabs activeTab={rightTab} onChange={setRightTab} onAddPlace={() => setIsPlaceDiscoveryOpen(true)} />
            <div className="workspace-right-scroll">
              {rightTab === "plan" ? (
                <PlanContent itinerary={itinerary} onUpdate={onUpdate} onTransportSelect={onTransportSelect} onPlanSelect={selectPlan} isPlanSelecting={isPlanSelecting} onActivityEdit={refine} isEditing={isEditing} />
              ) : rightTab === "overview" ? (
                <OverviewRail itinerary={itinerary} />
              ) : (
                <SavedPlacesPanel itinerary={itinerary} onOpenDiscovery={() => setIsPlaceDiscoveryOpen(true)} onUpdate={onUpdate} />
              )}
            </div>
          </section>
        </div>

        <div className="workspace-mobile-surface print-hidden mt-4 lg:hidden">
          {activeTab === "plan" && <PlanContent itinerary={itinerary} onUpdate={onUpdate} onTransportSelect={onTransportSelect} onPlanSelect={selectPlan} isPlanSelecting={isPlanSelecting} onActivityEdit={refine} isEditing={isEditing} />}
          {activeTab === "overview" && <OverviewRail itinerary={itinerary} />}
          {activeTab === "map" && <div className="workspace-mobile-map rounded-xl border border-glass-border bg-glass-bg p-1"><TripMap center={itinerary.destination.coordinates} dayPlans={itinerary.day_plans} routeSegments={itinerary.route_segments} destination={itinerary.destination.name} /></div>}
          {activeTab === "saved" && <SavedPlacesPanel itinerary={itinerary} onOpenDiscovery={() => setIsPlaceDiscoveryOpen(true)} onUpdate={onUpdate} />}
          {activeTab === "budget" && <div className="space-y-4"><BudgetBreakdown budget={itinerary.budget} totalBudget={itinerary.budget.total_estimated + itinerary.budget.remaining} /><TripCommitments itinerary={itinerary} compact /></div>}
          {activeTab === "chat" && conversation}
        </div>
        {isPlaceDiscoveryOpen && <PlaceDiscovery itinerary={itinerary} isOpen onClose={() => setIsPlaceDiscoveryOpen(false)} onUpdate={onUpdate} />}
      </div>
    </section>
  );
}
