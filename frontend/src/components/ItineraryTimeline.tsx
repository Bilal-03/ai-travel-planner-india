"use client";

import { ReactNode, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { DayPlan, formatINR, formatDate } from "@/lib/api";
import DataStatusBadge from "./DataStatusBadge";
import EstimateDisclaimer from "./EstimateDisclaimer";
import FreshnessTimestamp from "./FreshnessTimestamp";
import ProviderAttribution from "./ProviderAttribution";
import WeatherBadge from "./WeatherBadge";

interface ItineraryTimelineProps {
  dayPlans: DayPlan[];
  action?: ReactNode;
}

export default function ItineraryTimeline({ dayPlans, action }: ItineraryTimelineProps) {
  const [expandedDay, setExpandedDay] = useState<number | null>(0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-xl font-bold font-[family-name:var(--font-outfit)] text-foreground flex items-center gap-2">
          📅 Day-by-Day Itinerary
        </h3>
        {action}
      </div>

      <div className="relative">
        {/* Vertical timeline line */}
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-glass-border hidden md:block" />

        {dayPlans.map((day, idx) => {
          const isExpanded = expandedDay === idx;

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
                className={`glass rounded-xl overflow-hidden transition-all duration-300 ${
                  isExpanded ? "animate-pulse-glow" : ""
                }`}
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
                            <div className="space-y-2">
                              {day.activities.map((act, aIdx) => {
                                const costProvenance = act.poi.field_provenance?.estimated_cost || act.poi.provenance;
                                return (
                                  <div
                                    key={aIdx}
                                    className="flex items-start gap-3 p-3 rounded-lg bg-glass-bg hover:bg-glass-highlight transition-colors"
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
                                      </div>
                                      <div className="text-xs text-foreground-muted">
                                        {act.poi.category}
                                        {act.notes && ` • ${act.notes}`}
                                      </div>
                                      <EstimateDisclaimer provenance={costProvenance} className="mt-1" />
                                    </div>
                                    {act.estimated_cost > 0 && (
                                      <div className="text-right text-sm font-medium text-accent">
                                        <div>{formatINR(act.estimated_cost)}</div>
                                        <DataStatusBadge provenance={costProvenance} compact />
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

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
