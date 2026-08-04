"use client";

import { DataProvenance, DataStatus, UNAVAILABLE_PROVENANCE } from "@/lib/api";

interface DataStatusBadgeProps {
  provenance?: DataProvenance | null;
  compact?: boolean;
}

const LABELS: Record<DataStatus | "stale", string> = {
  live: "Live",
  recently_verified: "Recently verified",
  schedule_only: "Schedule only",
  estimated: "Estimated",
  static_reference: "Static reference",
  unavailable: "Data unavailable",
  stale: "Stale data",
};

function isStale(provenance: DataProvenance): boolean {
  return Boolean(provenance.expires_at && Date.parse(provenance.expires_at) <= Date.now());
}

export function effectiveDataStatus(provenance?: DataProvenance | null): DataStatus | "stale" {
  const value = provenance || UNAVAILABLE_PROVENANCE;
  if (value.status !== "unavailable" && isStale(value)) return "stale";
  return value.status;
}

export default function DataStatusBadge({ provenance, compact = false }: DataStatusBadgeProps) {
  const value = provenance || UNAVAILABLE_PROVENANCE;
  const status = effectiveDataStatus(value);
  const style = {
    live: "border-success/30 bg-success/10 text-success",
    recently_verified: "border-sky-400/30 bg-sky-400/10 text-sky-300",
    schedule_only: "border-violet-400/30 bg-violet-400/10 text-violet-300",
    estimated: "border-amber-400/30 bg-amber-400/10 text-amber-300",
    static_reference: "border-slate-400/30 bg-slate-400/10 text-slate-300",
    unavailable: "border-error/30 bg-error/10 text-error",
    stale: "border-orange-400/30 bg-orange-400/10 text-orange-300",
  }[status];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border ${
        compact ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs"
      } ${style}`}
      title={value.disclaimer}
    >
      <span aria-hidden="true">{status === "live" ? "●" : status === "stale" ? "!" : "•"}</span>
      {LABELS[status]}
    </span>
  );
}
