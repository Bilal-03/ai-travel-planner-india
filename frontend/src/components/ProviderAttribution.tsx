"use client";

import { DataProvenance, UNAVAILABLE_PROVENANCE } from "@/lib/api";

interface ProviderAttributionProps {
  provenance?: DataProvenance | null;
}

export default function ProviderAttribution({ provenance }: ProviderAttributionProps) {
  const value = provenance || UNAVAILABLE_PROVENANCE;
  const source = value.source_reference;
  const sourceLink = source && /^https?:\/\//i.test(source) ? source : null;

  return (
    <span className="text-[11px] text-foreground-muted">
      Source: {value.provider}
      {sourceLink && (
        <>
          {" "}
          <a
            href={sourceLink}
            target="_blank"
            rel="noreferrer"
            className="text-primary hover:text-primary-light underline-offset-2 hover:underline"
            onClick={(event) => event.stopPropagation()}
          >
            verify ↗
          </a>
        </>
      )}
    </span>
  );
}
