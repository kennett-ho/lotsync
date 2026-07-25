-- Phase 2, Slice 2 -- PendingIdentity.
--
-- See DATA_MODEL.md's "PendingIdentity" entry for the full reasoning:
-- an observation (today, always from Keyper) that couldn't be resolved
-- to a real VIN at write time. Deliberately a separate table from
-- vehicle, not a vehicle row with vin = NULL or a sentinel VIN string
-- -- see that entry for why both alternatives were rejected.
--
-- Upsert key is (source, raw_identifier), NOT an insert-every-run
-- pattern like event. A PendingIdentity represents one still-open,
-- physically-real item (e.g. one key sitting in a cabinet); the same
-- unresolved key observed again next sync must update the existing
-- row's last_observed_at, not create a second row for the same key --
-- otherwise "how many cycles has this been pending" (this table's
-- entire reason for existing, per DATA_MODEL.md) can never be answered
-- and Slice 2's Definition of Done (PendingIdentity count matches
-- data_quality_exceptions.csv's row count) would break after a second
-- run.
--
-- resolved_vin has no FOREIGN KEY constraint declared -- Slice 3 is
-- what actually sets it (promotion), and by the time it does, the
-- referenced vehicle row already exists (promotion upserts Vehicle
-- first). Left unconstrained here rather than added and immediately
-- relied on by code that doesn't exist yet.

CREATE TABLE IF NOT EXISTS pending_identity (
    pending_identity_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    source                TEXT NOT NULL,
    raw_identifier        TEXT NOT NULL,
    identifier_type       TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'pending',
    first_observed_at     TEXT NOT NULL,
    last_observed_at      TEXT NOT NULL,
    resolved_vin          TEXT,
    resolved_at           TEXT,
    UNIQUE (source, raw_identifier)
);

CREATE INDEX IF NOT EXISTS idx_pending_identity_status ON pending_identity (status);
