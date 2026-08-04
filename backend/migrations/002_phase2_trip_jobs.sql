-- Phase 2: durable job metadata for operational inspection and recovery.
-- Redis remains the queue/event/idempotency transport; final itineraries stay
-- in trips. This table provides a PostgreSQL home for job snapshots when the
-- deployment's job repository is extended beyond the Redis-first path.

CREATE TABLE IF NOT EXISTS trip_jobs (
    id UUID PRIMARY KEY,
    idempotency_key_hash TEXT NOT NULL UNIQUE,
    request_json JSONB NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'accepted',
            'retrieving_data',
            'resolving_locations',
            'fetching_transport',
            'fetching_places',
            'fetching_weather',
            'optimising',
            'generating_narrative',
            'validating',
            'saving',
            'completed',
            'failed',
            'cancelled'
        )
    ),
    step TEXT NOT NULL,
    message TEXT NOT NULL,
    progress INTEGER NOT NULL CHECK (progress BETWEEN 0 AND 100),
    result_trip_id VARCHAR(12),
    error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS trip_jobs_status_idx
    ON trip_jobs (status, updated_at);

CREATE INDEX IF NOT EXISTS trip_jobs_result_idx
    ON trip_jobs (result_trip_id)
    WHERE result_trip_id IS NOT NULL;
