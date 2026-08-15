-- PostgreSQL dialect of database/migrations/0008_event_fidelity.sql
-- (Sprint 03). See that file for the full design reasoning
-- (event_time vs observed_at; why event_freshness is mutable current-
-- state metadata, not history; why last_sync_run_id has no FK).
-- Dialect difference: ADD COLUMN IF NOT EXISTS (same note as 0007).

ALTER TABLE event ADD COLUMN IF NOT EXISTS event_time TEXT;

CREATE TABLE IF NOT EXISTS event_freshness (
    vin              TEXT NOT NULL,
    event_type       TEXT NOT NULL,
    source           TEXT NOT NULL,
    last_observed_at TEXT NOT NULL,
    last_sync_run_id TEXT,
    PRIMARY KEY (vin, event_type),
    FOREIGN KEY (vin) REFERENCES vehicle (vin)
);
