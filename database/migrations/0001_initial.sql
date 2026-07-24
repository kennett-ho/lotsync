-- Phase 2, Slice 1 -- SQLite foundation.
--
-- Scope per IMPLEMENTATION_PLAN.md Slice 1: Vehicle and Event only, no
-- other tables yet. Column shapes match DATA_MODEL.md's full,
-- already-decided Vehicle/Event definitions -- but only Keyper's
-- import path (sync/reconciler.py, reconcile_keyper_tekion) populates
-- any of it in this slice. tekion_status/mdd_status/recovr_status/
-- current_dealership_id/stock_number/year/make/model/new_or_used all
-- stay NULL until the sources that own them are wired in during
-- Slice 2 -- see ARCHITECTURE.md, "Where business rules belong," for
-- why Keyper's own pass must not guess at fields it doesn't own.
--
-- sync_run_id / actor_employee_id / dealership_id on event are present
-- now (matching DATA_MODEL.md's decided Event shape) but intentionally
-- left as plain, unconstrained columns -- SyncRun, Employee, and
-- Dealership tables don't exist until later slices (4, and not yet
-- scheduled, respectively). No FOREIGN KEY is declared against a table
-- that doesn't exist yet; add the constraint in the migration that
-- introduces each referenced table.
--
-- Per IMPLEMENTATION_PLAN.md's Migration Strategy risk note: numbered,
-- ordered migration files from day one, even though this first schema
-- is small. Treat it as intentionally provisional (see Slice 1's Risk
-- entry) -- it may need revision once Slice 2 brings in the other four
-- sources.

-- schema_migrations itself is bootstrap infrastructure created by
-- database/repository.py before any numbered migration runs, not a
-- versioned migration -- not repeated here to avoid two places
-- claiming ownership of that table.

CREATE TABLE IF NOT EXISTS vehicle (
    vin                     TEXT PRIMARY KEY,
    stock_number            TEXT,
    year                    INTEGER,
    make                    TEXT,
    model                   TEXT,
    new_or_used             TEXT,
    -- Mutable current attribute, NOT identity -- see DATA_MODEL.md,
    -- "Tenant vs Dealership." No Dealership table exists yet; this
    -- stays an unconstrained, unpopulated column until that's built.
    current_dealership_id   TEXT,
    tekion_status           TEXT,
    keyper_status           TEXT,
    mdd_status              TEXT,
    recovr_status           TEXT,
    inventory_state         TEXT
    -- pending_tasks and history are NOT columns here -- per
    -- DATA_MODEL.md's Relationships section, both are derived by
    -- querying task/event WHERE vin = ?, not stored redundantly.
);

CREATE TABLE IF NOT EXISTS event (
    event_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    vin                 TEXT NOT NULL,
    event_type          TEXT NOT NULL,
    source              TEXT NOT NULL,
    sync_run_id         TEXT,
    actor_employee_id   TEXT,
    -- Captured at write time, NOT derived from vehicle.current_dealership_id
    -- -- see DATA_MODEL.md, keeps history accurate across a later transfer.
    dealership_id       TEXT,
    observed_at         TEXT NOT NULL,
    summary             TEXT,
    detail_fields       TEXT,  -- JSON-encoded dict; see DATA_MODEL.md ("unvalidated dict for now")
    FOREIGN KEY (vin) REFERENCES vehicle (vin)
);

-- Per IMPLEMENTATION_PLAN.md Technical Risks: index vin, sync_run_id,
-- and event_type from Sprint 1 onward, not added reactively later.
CREATE INDEX IF NOT EXISTS idx_event_vin ON event (vin);
CREATE INDEX IF NOT EXISTS idx_event_sync_run_id ON event (sync_run_id);
CREATE INDEX IF NOT EXISTS idx_event_event_type ON event (event_type);
