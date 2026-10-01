-- Runs once, on an empty PostgreSQL data directory, before the API connects.
-- Mounted into the postgres container at /docker-entrypoint-initdb.d/.
--
-- The application does not require any extension: primary keys are UUIDs
-- generated in Python, so `uuid-ossp` / `pgcrypto` are not needed for
-- correctness. These are enabled because they are broadly useful and cost
-- nothing, and because having the hook in place means adding one later is a
-- one-line change rather than a migration.

-- Trigram indexes, for when the current LIKE-based search outgrows itself.
-- See docs/scalability.md.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Accent- and case-insensitive comparison for names and institutions.
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Query statistics, so slow queries can be found in production.
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- NOTE: PostGIS is NOT used. SkillBridge stores locations as city and state
-- strings and matches them textually; there is no geometry, no spatial index
-- and no distance query anywhere in the codebase. If geographic matching is
-- added later, enable it here and switch the postgres image to postgis/postgis.
