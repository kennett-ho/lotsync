-- Sprint 3.7 (v0.7.3) -- Event Fidelity.
--
-- Two additions, landing together because both serve the same goal:
-- the Timeline should represent the operational history of a vehicle,
-- not a log of when LotSync happened to sync. Neither changes what
-- observed_at means or removes it -- see DATA_MODEL.md's Event entry
-- for the full reasoning.

-- event.event_time: the source's own claimed timestamp for when this
-- event actually happened, distinct from observed_at (when LotSync's
-- sync learned about it -- unchanged, still always populated, still
-- the audit trail). Nullable, because most sources don't expose a
-- per-observation timestamp at all today (MDD, RecovR, RapidRecon's
-- raw exports have no date column) -- populated only where a source
-- genuinely provides one with a confirmed meaning: Keyper's Checkout
-- Date for "Out" events (the one place this project already trusted
-- this field, via the existing days-out calculation), and Tekion's
-- Stocked In Date / Sold Date. Deliberately NOT populated by
-- inferring a Keyper "In" (return) timestamp -- Keyper's export has
-- no field confirmed to mean that; see sync/reconciler.py's
-- _persist_keyper_observation docstring for why guessing was rejected.
--
-- ADD COLUMN, not a recreation -- same operation as
-- migrations/0007_vehicle_display_name.sql, same reasoning: a new
-- nullable column with no constraint doesn't require rebuilding the
-- table.
ALTER TABLE event ADD COLUMN event_time TEXT;

-- event_freshness: closes a real, pre-existing audit gap this sprint
-- surfaced -- not a new feature, a missing piece of "don't lose audit
-- capability." Today, once a repeated identical observation is
-- correctly suppressed from creating a new Event (Keyper/Tekion/MDD/
-- RecovR have always done this -- see each persist_* function's
-- diff-before-write), nothing records that the claim was reconfirmed:
-- SyncRun only tracks aggregate per-source execution, not which VINs
-- it touched, so "was this specific vehicle's WHOLESALE status
-- reconfirmed by last night's sync, or is our belief three weeks
-- stale" has never actually been answerable per vehicle. This table
-- is the minimal fix: one row per (vin, event_type), updated on every
-- observation regardless of whether a new Event was written.
--
-- Deliberately mutable (upserted, not append-only) -- this is
-- DECISION_FRAMEWORK.md's "current state is always a derived read"
-- category, the same as Vehicle's own status-cache columns, NOT
-- history. It does not violate "history is immutable": no Event row
-- is ever edited here, because this isn't one -- it's freshness
-- metadata sitting next to history, not inside it.
--
-- Generic across source/event_type by construction (not one column
-- per source on Vehicle, which wouldn't even fit every source --
-- RapidRecon deliberately has no Vehicle status column of its own,
-- per Phase 2 Sprint 2's documented decision) -- so any future
-- source's persist function gets this for free just by using the same
-- shared helper (see sync/reconciler.py's _insert_event_if_changed),
-- not by re-inventing per-source freshness tracking each time.
--
-- No FOREIGN KEY on sync_run_id, same convention and same reasoning
-- as event.sync_run_id (see migrations/0003_sync_run.sql) -- an
-- opaque provenance tag, not a hard-enforced reference.
CREATE TABLE IF NOT EXISTS event_freshness (
    vin              TEXT NOT NULL,
    event_type       TEXT NOT NULL,
    source           TEXT NOT NULL,
    last_observed_at TEXT NOT NULL,
    last_sync_run_id TEXT,
    PRIMARY KEY (vin, event_type),
    FOREIGN KEY (vin) REFERENCES vehicle (vin)
);
