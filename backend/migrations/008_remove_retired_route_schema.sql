-- Remove the retired multi-stop route planner from existing installations.
-- Child projections are dropped before their aggregate parent.

DO $$
BEGIN
    IF to_regclass('public.itinerary_versions') IS NOT NULL THEN
        DELETE FROM itinerary_versions WHERE kind = 'multi_city';
        ALTER TABLE itinerary_versions
            DROP CONSTRAINT IF EXISTS itinerary_versions_kind_check;
        ALTER TABLE itinerary_versions
            ADD CONSTRAINT itinerary_versions_kind_check CHECK (kind = 'single');
    END IF;

    IF to_regclass('public.trip_edits') IS NOT NULL THEN
        DELETE FROM trip_edits WHERE kind = 'multi_city';
        ALTER TABLE trip_edits
            DROP CONSTRAINT IF EXISTS trip_edits_kind_check;
        ALTER TABLE trip_edits
            ADD CONSTRAINT trip_edits_kind_check CHECK (kind = 'single');
    END IF;

    IF to_regclass('public.share_links') IS NOT NULL THEN
        DELETE FROM share_links WHERE kind = 'multi_city';
        ALTER TABLE share_links
            DROP CONSTRAINT IF EXISTS share_links_kind_check;
        ALTER TABLE share_links
            ADD CONSTRAINT share_links_kind_check CHECK (kind = 'single');
    END IF;

    IF to_regclass('public.collaborators') IS NOT NULL THEN
        DELETE FROM collaborators WHERE kind = 'multi_city';
        ALTER TABLE collaborators
            DROP CONSTRAINT IF EXISTS collaborators_kind_check;
        ALTER TABLE collaborators
            ADD CONSTRAINT collaborators_kind_check CHECK (kind = 'single');
    END IF;

    IF to_regclass('public.analytics_events') IS NOT NULL THEN
        DELETE FROM analytics_events WHERE kind = 'multi_city';
    END IF;
END
$$;

DROP TABLE IF EXISTS multi_city_transport_selections;
DROP TABLE IF EXISTS multi_city_itinerary_days;
DROP TABLE IF EXISTS multi_city_visits;
DROP TABLE IF EXISTS multi_city_travel_legs;
DROP TABLE IF EXISTS multi_city_destination_stays;
DROP TABLE IF EXISTS multi_city_accommodation_selections;
DROP TABLE IF EXISTS multi_city_trips;
