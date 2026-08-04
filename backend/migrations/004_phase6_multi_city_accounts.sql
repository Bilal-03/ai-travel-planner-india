-- Phase 6: canonical multi-city aggregates, normalized route projections,
-- optional accounts, and explicit preference memory.

ALTER TABLE trips
    ADD COLUMN IF NOT EXISTS owner_user_id VARCHAR(36);

CREATE TABLE IF NOT EXISTS multi_city_trips (
    id VARCHAR(12) PRIMARY KEY,
    trip_json JSONB NOT NULL,
    origin TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget INTEGER NOT NULL,
    owner_token_hash TEXT,
    owner_user_id VARCHAR(36),
    previous_trip_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS multi_city_destination_stays (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    stay_id VARCHAR(64) NOT NULL,
    position INTEGER NOT NULL,
    city_json JSONB NOT NULL,
    arrival_date DATE NOT NULL,
    departure_date DATE NOT NULL,
    nights INTEGER NOT NULL,
    notes TEXT,
    provenance_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, stay_id)
);

CREATE TABLE IF NOT EXISTS multi_city_travel_legs (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    leg_id VARCHAR(64) NOT NULL,
    leg_position INTEGER NOT NULL,
    origin_json JSONB NOT NULL,
    destination_json JSONB NOT NULL,
    travel_date DATE NOT NULL,
    mode TEXT NOT NULL,
    selected_offer_json JSONB,
    alternatives_json JSONB NOT NULL,
    duration_minutes INTEGER NOT NULL,
    fare INTEGER NOT NULL,
    provenance_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, leg_id)
);

CREATE TABLE IF NOT EXISTS multi_city_visits (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    visit_id VARCHAR(64) NOT NULL,
    stay_id VARCHAR(64) NOT NULL,
    visit_date DATE NOT NULL,
    visit_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, visit_id)
);

CREATE TABLE IF NOT EXISTS multi_city_itinerary_days (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,
    day_date DATE NOT NULL,
    day_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, day_number)
);

CREATE TABLE IF NOT EXISTS multi_city_accommodation_selections (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    selection_id VARCHAR(64) NOT NULL,
    stay_id VARCHAR(64) NOT NULL,
    selection_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, selection_id)
);

CREATE TABLE IF NOT EXISTS multi_city_transport_selections (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    leg_id VARCHAR(64) NOT NULL,
    selection_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, leg_id)
);

CREATE TABLE IF NOT EXISTS yatra_accounts (
    id VARCHAR(36) PRIMARY KEY,
    email TEXT UNIQUE,
    display_name TEXT,
    is_anonymous BOOLEAN NOT NULL DEFAULT TRUE,
    memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS yatra_account_sessions (
    token_hash TEXT PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL REFERENCES yatra_accounts(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS yatra_account_preferences (
    account_id VARCHAR(36) PRIMARY KEY REFERENCES yatra_accounts(id) ON DELETE CASCADE,
    memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    preferred_transport TEXT,
    hotel_category TEXT,
    typical_budget_min INTEGER,
    typical_budget_max INTEGER,
    dietary_preference TEXT,
    travel_pace TEXT,
    accessibility_requirements TEXT,
    preferred_departure_times JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS multi_city_trips_owner_idx
    ON multi_city_trips (owner_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS multi_city_stays_route_idx
    ON multi_city_destination_stays (trip_id, position);

