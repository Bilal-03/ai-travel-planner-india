-- Remove account/session/preference tables and account ownership columns from
-- databases that were initialized before the account-free planner decision.

DROP TABLE IF EXISTS yatra_account_preferences;
DROP TABLE IF EXISTS yatra_account_sessions;
DROP TABLE IF EXISTS yatra_accounts;

ALTER TABLE trips
    DROP COLUMN IF EXISTS owner_user_id;

ALTER TABLE multi_city_trips
    DROP COLUMN IF EXISTS owner_user_id;
