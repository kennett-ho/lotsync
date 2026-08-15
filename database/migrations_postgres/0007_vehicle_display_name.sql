-- PostgreSQL dialect of database/migrations/0007_vehicle_display_name.sql
-- (Sprint 03). See that file for the full design reasoning (why
-- display_name exists instead of parsing "Year Make Model"). One
-- dialect difference: PostgreSQL's ADD COLUMN supports IF NOT EXISTS,
-- used here to keep the file re-runnable in the same spirit as the
-- CREATE TABLE IF NOT EXISTS convention (SQLite's ALTER has no such
-- clause; its file relies on schema_migrations bookkeeping alone).

ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS display_name TEXT;
