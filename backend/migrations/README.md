# Database migrations

Migrations in this directory are ordered SQL files intended for the production
database migration runner. They are not executed by the application at runtime.

`001_phase1_travel_facts.sql` adds the durable fact-level storage needed for
provider, status, freshness, confidence, source, and disclaimer metadata. Phase
1 writes the same provenance into the itinerary JSON so existing Neon and
in-memory storage paths remain compatible; later phases can backfill and refresh
`travel_facts` without changing the API contract.

`002_phase2_trip_jobs.sql` adds the PostgreSQL job-snapshot schema. Phase 2 uses
Redis as the active queue, event replay, idempotency, and cancellation transport;
the migration provides the durable operational record needed when the job
repository is connected to PostgreSQL in the deployment.

`003_phase4_trip_revisions.sql` adds the previous-itinerary JSONB column used by
the trip workspace's one-step undo action. The application also applies this
column additively when it initializes an existing trips table.

`004_phase6_multi_city.sql` adds the canonical multi-city aggregate and its
stay/leg/visit/day/transport-selection projections. Apply it after the preceding
migrations.

`005_phase7_collaboration_analytics.sql` adds append-only single-itinerary versions,
structured trip edits, hashed share grants, collaborator roles, privacy-safe
analytics events, and sensitive-action audit logs. Apply it before enabling
`REQUIRE_DURABLE_STORAGE=true` in production. The application creates the same
tables only as a local-development convenience; the migration remains the
source of truth for hosted databases.

`006_remove_legacy_account_schema.sql` removes the account/session/preference
tables and account ownership columns created by the earlier account-based
implementation. Apply it to any database that has already run that retired
schema.

`007_remove_legacy_accommodation_projection.sql` removes a retired projection
from databases that applied the earlier itinerary shape.

`008_remove_retired_route_schema.sql` removes the retired multi-stop route
tables and any associated collaboration rows from databases that applied the
earlier route-planner implementation. The earlier route migration remains in
the ordered history so existing migration runners stay consistent; the active
application no longer creates or exposes those tables.

Before applying in production, run the migration against a staging database and
verify the status check constraint and expiry index. Do not hand-edit the live
schema or replace this file with a runtime `ALTER TABLE` call.
