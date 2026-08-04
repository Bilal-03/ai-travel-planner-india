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

Before applying in production, run the migration against a staging database and
verify the status check constraint and expiry index. Do not hand-edit the live
schema or replace this file with a runtime `ALTER TABLE` call.
