-- Phase 7: immutable itinerary history, collaboration grants, privacy-safe
-- analytics, audit logs, and production operational hardening.
--
-- Tokens are stored only as SHA-256 hashes. Itinerary versions are append-only;
-- a new edit creates a new row instead of mutating an existing snapshot.

CREATE TABLE IF NOT EXISTS itinerary_versions (
    id UUID PRIMARY KEY,
    trip_id VARCHAR(64) NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('single', 'multi_city')),
    version INTEGER NOT NULL CHECK (version > 0),
    action TEXT NOT NULL,
    actor_id VARCHAR(128),
    snapshot_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (trip_id, kind, version)
);

CREATE TABLE IF NOT EXISTS trip_edits (
    id UUID PRIMARY KEY,
    trip_id VARCHAR(64) NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('single', 'multi_city')),
    action TEXT NOT NULL,
    actor_id VARCHAR(128),
    version INTEGER,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS share_links (
    id UUID PRIMARY KEY,
    trip_id VARCHAR(64) NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('single', 'multi_city')),
    role TEXT NOT NULL CHECK (role IN ('editor', 'viewer')),
    token_hash TEXT NOT NULL UNIQUE,
    invite_email TEXT,
    created_by VARCHAR(128),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS collaborators (
    id UUID PRIMARY KEY,
    trip_id VARCHAR(64) NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('single', 'multi_city')),
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('editor', 'viewer')),
    created_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (trip_id, kind, email)
);

CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY,
    event_name TEXT NOT NULL,
    trip_id_hash TEXT,
    kind TEXT,
    duration_ms INTEGER,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY,
    action TEXT NOT NULL,
    trip_id VARCHAR(64),
    actor_hash TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS itinerary_versions_trip_idx
    ON itinerary_versions (trip_id, kind, version DESC);
CREATE INDEX IF NOT EXISTS trip_edits_trip_idx
    ON trip_edits (trip_id, kind, created_at DESC);
CREATE INDEX IF NOT EXISTS share_links_trip_idx
    ON share_links (trip_id, kind, expires_at);
CREATE INDEX IF NOT EXISTS analytics_events_name_idx
    ON analytics_events (event_name, created_at DESC);
