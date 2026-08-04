-- Phase 6: canonical multi-city aggregates and normalized route projections.

CREATE TABLE IF NOT EXISTS multi_city_trips (
    id VARCHAR(12) PRIMARY KEY,
    trip_json JSONB NOT NULL,
    origin TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget INTEGER NOT NULL,
    owner_token_hash TEXT,
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

CREATE INDEX IF NOT EXISTS multi_city_stays_route_idx
    ON multi_city_destination_stays (trip_id, position);
