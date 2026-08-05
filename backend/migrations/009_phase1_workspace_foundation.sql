-- Phase 1 workspace foundation
--
-- These tables are projections for the normalized place/item/source/research
-- contracts. The itinerary JSON remains the compatibility read model while
-- the application adopts these tables incrementally.

CREATE TABLE IF NOT EXISTS places (
    id VARCHAR(64) PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    category TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    address TEXT,
    city TEXT,
    state TEXT,
    country_code CHAR(2) NOT NULL DEFAULT 'IN',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS places_city_idx ON places (city);
CREATE INDEX IF NOT EXISTS places_category_idx ON places (category);

CREATE TABLE IF NOT EXISTS place_provider_links (
    place_id VARCHAR(64) NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_place_id TEXT NOT NULL,
    source_url TEXT,
    provenance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    PRIMARY KEY (place_id, provider)
);

CREATE INDEX IF NOT EXISTS place_provider_links_lookup_idx
    ON place_provider_links (provider, provider_place_id);
CREATE INDEX IF NOT EXISTS place_provider_links_expiry_idx
    ON place_provider_links (expires_at)
    WHERE expires_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS trip_intents (
    trip_id VARCHAR(12) PRIMARY KEY REFERENCES trips(id) ON DELETE CASCADE,
    intent_version INTEGER NOT NULL DEFAULT 1,
    intent_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trip_sources (
    id VARCHAR(64) PRIMARY KEY,
    trip_id VARCHAR(12) NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL CHECK (source_type IN (
        'official', 'provider', 'map', 'editorial', 'image', 'user'
    )),
    publisher TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    attribution_text TEXT,
    provenance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS trip_sources_trip_idx ON trip_sources (trip_id, captured_at);

CREATE TABLE IF NOT EXISTS trip_research_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id VARCHAR(12) NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'understanding_request', 'asking_question', 'searching',
        'found_places', 'found_transport', 'found_stays', 'validating',
        'updated_plan', 'completed', 'failed'
    )),
    status TEXT NOT NULL CHECK (status IN ('pending', 'complete', 'warning', 'error')),
    message TEXT NOT NULL,
    query_text TEXT,
    result_count INTEGER CHECK (result_count IS NULL OR result_count >= 0),
    source_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS trip_research_events_trip_idx
    ON trip_research_events (trip_id, created_at);

CREATE TABLE IF NOT EXISTS trip_itinerary_items (
    id VARCHAR(64) PRIMARY KEY,
    trip_id VARCHAR(12) NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    day_number INTEGER CHECK (day_number IS NULL OR day_number BETWEEN 1 AND 31),
    position INTEGER NOT NULL DEFAULT 0 CHECK (position >= 0),
    item_type TEXT NOT NULL CHECK (item_type IN (
        'place_visit', 'stay', 'flight', 'train', 'road_transfer',
        'restaurant', 'event', 'note'
    )),
    place_id VARCHAR(64) REFERENCES places(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    item_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS trip_itinerary_items_day_idx
    ON trip_itinerary_items (trip_id, day_number, position);
CREATE INDEX IF NOT EXISTS trip_itinerary_items_place_idx
    ON trip_itinerary_items (place_id)
    WHERE place_id IS NOT NULL;
