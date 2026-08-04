-- Phase 4: retain one server-side revision so the workspace can undo its latest edit.
-- The storage service also applies this additively for existing deployments.
ALTER TABLE trips
    ADD COLUMN IF NOT EXISTS previous_itinerary_json JSONB;
