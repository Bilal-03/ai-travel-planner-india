"use client";

import { DataProvenance, UNAVAILABLE_PROVENANCE } from "@/lib/api";
import { effectiveDataStatus } from "./DataStatusBadge";

interface FreshnessTimestampProps {
  provenance?: DataProvenance | null;
}

function formatDate(value: string | null): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export default function FreshnessTimestamp({ provenance }: FreshnessTimestampProps) {
  const value = provenance || UNAVAILABLE_PROVENANCE;
  const checked = formatDate(value.retrieved_at);
  const status = effectiveDataStatus(value);

  if (status === "stale") {
    return <span className="text-[11px] text-orange-300">Stale since {checked || "the last check"}</span>;
  }
  if (!checked) return <span className="text-[11px] text-foreground-muted">Freshness unavailable</span>;
  return <span className="text-[11px] text-foreground-muted">Checked {checked}</span>;
}
