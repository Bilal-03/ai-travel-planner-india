"use client";

import { DataProvenance, UNAVAILABLE_PROVENANCE } from "@/lib/api";
import { effectiveDataStatus } from "./DataStatusBadge";

interface EstimateDisclaimerProps {
  provenance?: DataProvenance | null;
  className?: string;
}

export default function EstimateDisclaimer({ provenance, className = "" }: EstimateDisclaimerProps) {
  const value = provenance || UNAVAILABLE_PROVENANCE;
  const status = effectiveDataStatus(value);
  const shouldShow = status !== "live";

  if (!shouldShow) return null;
  return (
    <div className={`text-[11px] leading-relaxed text-amber-200/80 ${className}`}>
      ⚠️ {value.disclaimer || "Verify this information before booking."}
    </div>
  );
}
