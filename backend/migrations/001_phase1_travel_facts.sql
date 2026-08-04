-- Phase 1: provider provenance and freshness facts.
-- Apply this migration with the project's database migration runner before
-- enabling durable fact-level refreshes. The current itinerary JSON remains
-- backwards compatible and carries the same metadata immediately.

CREATE TABLE IF NOT EXISTS travel_facts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    value_json JSONB NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'live',
            'recently_verified',
            'schedule_only',
            'estimated',
            'static_reference',
            'unavailable'
        )
    ),
    retrieved_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    confidence DOUBLE PRECISION CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    source_reference TEXT,
    disclaimer TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (entity_type, entity_id, field_name, provider, retrieved_at)
);

CREATE INDEX IF NOT EXISTS travel_facts_lookup_idx
    ON travel_facts (entity_type, entity_id, field_name);

CREATE INDEX IF NOT EXISTS travel_facts_expiry_idx
    ON travel_facts (expires_at)
    WHERE expires_at IS NOT NULL;
