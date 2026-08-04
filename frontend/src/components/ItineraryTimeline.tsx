"use client";

import { DragEvent, FormEvent, ReactNode, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, DayPlan, formatINR, formatDate } from "@/lib/api";
import DataStatusBadge from "./DataStatusBadge";
import EstimateDisclaimer from "./EstimateDisclaimer";
import FreshnessTimestamp from "./FreshnessTimestamp";
import ProviderAttribution from "./ProviderAttribution";
import WeatherBadge from "./WeatherBadge";

interface ItineraryTimelineProps {
  dayPlans: DayPlan[];
  action?: ReactNode;
  headingId?: string;
  editingEnabled?: boolean;
  isEditing?: boolean;
  onActivityEdit?: (instruction: string) => Promise<void>;
}

interface DraggedActivity {
  name: string;
  dayNumber: number;
}

function activityDuration(activity: Activity): number {
  if (!activity.start_time || !activity.end_time) return activity.poi.estimated_visit_minutes || 60;
  const [startHour, startMinute] = activity.start_time.split(":").map(Number);
  const [endHour, endMinute] = activity.end_time.split(":").map(Number);
  return Math.max(15, (endHour * 60 + endMinute) - (startHour * 60 + startMinute));
}

function ActivityEditor({
  activity,
  dayNumber,
  dayNumbers,
  onSubmit,
  isEditing,
}: {
  activity: Activity;
  dayNumber: number;
  dayNumbers: number[];
  onSubmit: (instruction: string) => void;
  isEditing: boolean;
}) {
  const [replacement, setReplacement] = useState("");
  const [duration, setDuration] = useState(activityDuration(activity));
  const [targetDay, setTargetDay] = useState(dayNumber);

  const submit = (instruction: string) => {
    onSubmit(instruction);
  };

  return (
    <details className="relative shrink-0 print:hidden">
      <summary className="cursor-pointer list-none rounded-md border border-glass-border px-2 py-1 text-[11px] font-medium text-foreground-muted transition hover:border-primary hover:text-foreground" aria-label={`Edit ${activity.poi.name}`}>
        ⋯ Edit
      </summary>
      <div className="absolute right-0 top-8 z-30 w-[min(19rem,calc(100vw-2rem))] space-y-3 rounded-xl border border-glass-border bg-background p-3 text-left shadow-xl" role="menu">
        <div>
          <label htmlFor={`move-${dayNumber}-${activity.poi.id}`} className="block text-[11px] text-foreground-muted">Move to another day</label>
          <div className="mt-1 flex gap-2">
            <select id={`move-${dayNumber}-${activity.poi.id}`} value={targetDay} onChange={(event) => setTargetDay(Number(event.target.value))} className="min-w-0 flex-1 rounded-md border border-glass-border bg-glass-bg px-2 py-1.5 text-xs text-foreground" disabled={isEditing || Boolean(activity.is_locked)}>
              {dayNumbers.map((day) => <option key={day} value={day}>Day {day}{day === dayNumber ? " · current" : ""}</option>)}
            </select>
            <button type="button" onClick={() => submit(`Move activity "${activity.poi.name}" from day ${dayNumber} to day ${targetDay}.`)} disabled={isEditing || targetDay === dayNumber || Boolean(activity.is_locked)} className="rounded-md border border-primary/50 px-2 py-1 text-[11px] font-semibold text-primary disabled:opacity-40">Move</button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button type="button" onClick={() => submit(`Delete activity "${activity.poi.name}" from day ${dayNumber}.`)} disabled={isEditing || Boolean(activity.is_locked)} className="rounded-md border border-error/40 px-2 py-1.5 text-[11px] font-semibold text-error disabled:opacity-40">Delete</button>
          <button type="button" onClick={() => submit(`${activity.is_locked ? "Unlock" : "Lock"} activity "${activity.poi.name}" on day ${dayNumber}.`)} disabled={isEditing} className="rounded-md border border-glass-border px-2 py-1.5 text-[11px] font-semibold text-foreground-secondary disabled:opacity-40">{activity.is_locked ? "Unlock" : "Lock"}</button>
        </div>
        <div>
          <label htmlFor={`replace-${dayNumber}-${activity.poi.id}`} className="block text-[11px] text-foreground-muted">Replace this stop</label>
          <div className="mt-1 flex gap-2">
            <input id={`replace-${dayNumber}-${activity.poi.id}`} value={replacement} onChange={(event) => setReplacement(event.target.value)} placeholder="e.g. a nature activity" className="min-w-0 flex-1 rounded-md border border-glass-border bg-glass-bg px-2 py-1.5 text-xs text-foreground" disabled={isEditing || Boolean(activity.is_locked)} />
            <button type="button" onClick={() => submit(`Replace activity "${activity.poi.name}" on day ${dayNumber} with "${replacement.trim()}".`)} disabled={isEditing || replacement.trim().length < 3 || Boolean(activity.is_locked)} className="rounded-md border border-primary/50 px-2 py-1 text-[11px] font-semibold text-primary disabled:opacity-40">Replace</button>
          </div>
        </div>
        <div>
          <label htmlFor={`duration-${dayNumber}-${activity.poi.id}`} className="block text-[11px] text-foreground-muted">Edit duration</label>
          <div className="mt-1 flex gap-2">
            <input id={`duration-${dayNumber}-${activity.poi.id}`} type="number" min={15} max={720} step={15} value={duration} onChange={(event) => setDuration(Number(event.target.value) || 15)} className="min-w-0 flex-1 rounded-md border border-glass-border bg-glass-bg px-2 py-1.5 text-xs text-foreground" disabled={isEditing || Boolean(activity.is_locked)} />
            <button type="button" onClick={() => submit(`Set duration for activity "${activity.poi.name}" on day ${dayNumber} to ${duration} minutes.`)} disabled={isEditing || Boolean(activity.is_locked)} className="rounded-md border border-primary/50 px-2 py-1 text-[11px] font-semibold text-primary disabled:opacity-40">Save</button>
          </div>
        </div>
        {activity.is_locked && <p className="text-[10px] leading-relaxed text-warning">Locked stops are protected from drag, delete, move, and replacement until you unlock them.</p>}
      </div>
    </details>
  );
}

function AddActivityControl({ dayNumber, onSubmit, isEditing }: { dayNumber: number; onSubmit: (instruction: string) => void; isEditing: boolean }) {
  const [activityName, setActivityName] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const value = activityName.trim();
    if (value.length < 3 || isEditing) return;
    onSubmit(`Add custom activity "${value}" to day ${dayNumber}.`);
    setActivityName("");
    setIsOpen(false);
  };

  return (
    <div className="mt-3 print:hidden">
      {!isOpen ? (
        <button type="button" onClick={() => setIsOpen(true)} className="rounded-md border border-dashed border-glass-border px-3 py-2 text-[11px] font-medium text-foreground-muted transition hover:border-primary hover:text-foreground">＋ Add custom activity</button>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-2 rounded-lg border border-dashed border-glass-border bg-background/25 p-2 sm:flex-row">
          <label htmlFor={`add-activity-${dayNumber}`} className="sr-only">Custom activity for day {dayNumber}</label>
          <input id={`add-activity-${dayNumber}`} autoFocus value={activityName} onChange={(event) => setActivityName(event.target.value)} placeholder="What would you like to add?" className="min-w-0 flex-1 rounded-md border border-glass-border bg-glass-bg px-2.5 py-2 text-xs text-foreground" disabled={isEditing} />
          <div className="flex gap-2"><button type="submit" disabled={isEditing || activityName.trim().length < 3} className="rounded-md bg-primary px-3 py-2 text-[11px] font-semibold text-white disabled:opacity-40">Add</button><button type="button" onClick={() => setIsOpen(false)} className="rounded-md border border-glass-border px-3 py-2 text-[11px] text-foreground-muted">Cancel</button></div>
        </form>
      )}
    </div>
  );
}

export default function ItineraryTimeline({ dayPlans, action, headingId, editingEnabled = false, isEditing = false, onActivityEdit }: ItineraryTimelineProps) {
  const [expandedDay, setExpandedDay] = useState<number | null>(0);
  const [draggedActivity, setDraggedActivity] = useState<DraggedActivity | null>(null);
  const dayNumbers = dayPlans.map((day) => day.day_number);

  const submitEdit = (instruction: string) => {
    if (!onActivityEdit || isEditing) return;
    void onActivityEdit(instruction);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 id={headingId} className="text-xl font-bold font-[family-name:var(--font-outfit)] text-foreground flex items-center gap-2">
          📅 Day-by-Day Itinerary
        </h3>
        {action}
      </div>

      <div className="relative">
        {/* Vertical timeline line */}
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-glass-border hidden md:block" />

        {dayPlans.map((day, idx) => {
          const isExpanded = expandedDay === idx;
          const dropOnDay = (event: DragEvent<HTMLDivElement>) => {
            event.preventDefault();
            if (!draggedActivity || draggedActivity.dayNumber === day.day_number) return;
            submitEdit(`Move activity "${draggedActivity.name}" from day ${draggedActivity.dayNumber} to day ${day.day_number}.`);
            setDraggedActivity(null);
          };

          return (
            <motion.div
              key={day.day_number}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="relative md:pl-14 mb-4"
            >
              {/* Timeline dot */}
              <div className="absolute left-4 top-5 w-5 h-5 rounded-full border-2 border-primary bg-background z-10 hidden md:flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-primary" />
              </div>

              {/* Day Card */}
              <div
                className={`glass relative rounded-xl overflow-hidden transition-all duration-300 ${
                  isExpanded ? "animate-pulse-glow" : ""
                }`}
                onDragOver={(event) => {
                  if (editingEnabled && draggedActivity) event.preventDefault();
                }}
                onDrop={dropOnDay}
              >
                {/* Day Header — always visible */}
                <button
                  onClick={() => setExpandedDay(isExpanded ? null : idx)}
                  className="w-full p-4 flex items-center justify-between hover:bg-glass-highlight transition-colors"
                  id={`day-${day.day_number}-toggle`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary/15 flex items-center justify-center font-bold text-primary">
                      D{day.day_number}
                    </div>
                    <div className="text-left">
                      <div className="font-medium text-foreground">
                        Day {day.day_number}
                        <span className="text-foreground-muted font-normal ml-2 text-sm">
                          {formatDate(day.date)}
                        </span>
                      </div>
                      {day.notes && (
                        <div className="text-foreground-muted text-xs mt-0.5">
                          {day.notes}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {day.weather && <WeatherBadge weather={day.weather} compact />}
                    <span className="text-sm font-medium text-foreground-secondary">
                      {formatINR(day.day_spent)}
                    </span>
                    <motion.span
                      animate={{ rotate: isExpanded ? 180 : 0 }}
                      className="text-foreground-muted"
                    >
                      ▼
                    </motion.span>
                  </div>
                </button>
                {editingEnabled && (
                  <button
                    type="button"
                    onClick={() => submitEdit(`Regenerate day ${day.day_number}.`)}
                    disabled={isEditing}
                    aria-label={`Regenerate day ${day.day_number}`}
                    className="absolute right-12 top-3 rounded-md border border-glass-border bg-background/60 px-2 py-1 text-[11px] font-medium text-foreground-muted transition hover:border-primary hover:text-foreground disabled:opacity-40"
                  >
                    ↻
                  </button>
                )}

                {/* Expanded Content */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <div className="px-4 pb-4 space-y-4 border-t border-glass-border pt-4">
                        {/* Weather (full) */}
                        {day.weather && (
                          <WeatherBadge weather={day.weather} />
                        )}

                        {/* Transport (if travel day) */}
                        {day.transport && (
                          <div className="p-3 rounded-lg border border-glass-border bg-glass-bg">
                            <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-1">
                              {day.transport.mode === "flight" ? "✈️" : day.transport.mode === "train" ? "🚂" : "🚗"}
                              Travel: {day.transport.provider}
                              <DataStatusBadge provenance={day.transport.provenance} compact />
                            </div>
                            <div className="text-xs text-foreground-muted">
                              {day.transport.departure_city} → {day.transport.arrival_city}
                              {day.transport.departure_time && (
                                <span className="ml-2">
                                  at {day.transport.departure_time.slice(11, 16) || day.transport.departure_time}
                                </span>
                              )}
                            </div>
                            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                              <ProviderAttribution provenance={day.transport.provenance} />
                              <FreshnessTimestamp provenance={day.transport.provenance} />
                            </div>
                            <EstimateDisclaimer provenance={day.transport.provenance} className="mt-1" />
                          </div>
                        )}

                        {/* Activities */}
                        {day.activities.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold text-foreground-secondary mb-2">
                              🎯 Activities
                            </h4>
                            <div
                              className="space-y-2"
                            >
                              {day.activities.map((act, aIdx) => {
                                const costProvenance = act.poi.field_provenance?.estimated_cost || act.poi.provenance;
                                return (
                                  <div
                                    key={aIdx}
                                    draggable={editingEnabled && !isEditing && !act.is_locked}
                                    onDragStart={() => setDraggedActivity({ name: act.poi.name, dayNumber: day.day_number })}
                                    onDragEnd={() => setDraggedActivity(null)}
                                    aria-grabbed={draggedActivity?.name === act.poi.name && draggedActivity.dayNumber === day.day_number}
                                    className={`flex items-start gap-3 rounded-lg bg-glass-bg p-3 transition-colors hover:bg-glass-highlight ${editingEnabled && !act.is_locked ? "cursor-grab active:cursor-grabbing" : ""}`}
                                  >
                                    <div className="w-12 text-center">
                                      <div className="text-xs text-primary font-mono">
                                        {act.start_time || "--:--"}
                                      </div>
                                      {act.end_time && (
                                        <div className="text-xs text-foreground-muted font-mono">
                                          {act.end_time}
                                        </div>
                                      )}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                      <div className="flex flex-wrap items-center gap-2 font-medium text-foreground text-sm">
                                        <span>{act.poi.name}</span>
                                        <DataStatusBadge provenance={act.poi.provenance} compact />
                                        {act.is_locked && <span className="rounded-full bg-warning/15 px-1.5 py-0.5 text-[10px] text-warning" title="Locked activity">🔒 Locked</span>}
                                      </div>
                                      <div className="text-xs text-foreground-muted">
                                        {act.poi.category}
                                        {act.notes && ` • ${act.notes}`}
                                      </div>
                                      <EstimateDisclaimer provenance={costProvenance} className="mt-1" />
                                    </div>
                                    <div className="flex items-start gap-2">
                                      {act.estimated_cost > 0 && (
                                      <div className="text-right text-sm font-medium text-accent">
                                        <div>{formatINR(act.estimated_cost)}</div>
                                        <DataStatusBadge provenance={costProvenance} compact />
                                      </div>
                                      )}
                                      {editingEnabled && <ActivityEditor activity={act} dayNumber={day.day_number} dayNumbers={dayNumbers} onSubmit={submitEdit} isEditing={isEditing} />}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                            {editingEnabled && <AddActivityControl dayNumber={day.day_number} onSubmit={submitEdit} isEditing={isEditing} />}
                          </div>
                        )}

                        {editingEnabled && day.activities.length === 0 && <AddActivityControl dayNumber={day.day_number} onSubmit={submitEdit} isEditing={isEditing} />}

                        {day.local_transport_minutes > 0 && (
                          <div className="flex items-center justify-between rounded-lg bg-glass-bg px-3 py-2 text-xs text-foreground-muted">
                            <span>🚕 Local travel between stops · {day.local_transport_minutes} min</span>
                            <span className="font-medium text-foreground-secondary">{formatINR(day.local_transport_cost)}</span>
                          </div>
                        )}

                        {/* Meals */}
                        {day.meals.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold text-foreground-secondary mb-2">
                              🍽️ Meals
                            </h4>
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                              {day.meals.map((meal, mIdx) => (
                                <div
                                  key={mIdx}
                                  className="p-3 rounded-lg bg-glass-bg text-center"
                                >
                                  <div className="text-xs text-foreground-muted uppercase tracking-wider mb-1">
                                    {meal.meal_type}
                                  </div>
                                  <div className="text-sm font-medium text-foreground truncate">
                                    {meal.name}
                                  </div>
                                  <DataStatusBadge provenance={meal.provenance} compact />
                                  {meal.cuisine && (
                                    <div className="text-xs text-foreground-muted">{meal.cuisine}</div>
                                  )}
                                  <div className="text-xs font-medium text-accent mt-1">
                                    {formatINR(meal.estimated_cost)}
                                  </div>
                                  <EstimateDisclaimer provenance={meal.field_provenance?.estimated_cost || meal.provenance} className="mt-1 text-left" />
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Backup Activities */}
                        {day.backup_activities.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold text-foreground-muted mb-2">
                              ☔ Backup Activities (for bad weather)
                            </h4>
                            <div className="space-y-2">
                              {day.backup_activities.map((act, bIdx) => (
                                <div
                                  key={bIdx}
                                  className="flex items-center gap-3 p-2 rounded-lg bg-glass-bg border border-dashed border-glass-border"
                                >
                                  <span className="text-foreground-muted text-sm">
                                    {act.poi.name}
                                  </span>
                                  {act.estimated_cost > 0 && (
                                    <span className="ml-auto text-xs text-foreground-muted">
                                      {formatINR(act.estimated_cost)}
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
