-- Phase 2, Slice 4 -- SyncRun provenance.
--
-- See DATA_MODEL.md's SyncRun entry: one execution of the reconciliation
-- pipeline against one source. Every Event traces back to the SyncRun
-- that detected it; the "Connected Systems" dashboard panel is a
-- derived view over this table grouped by source, NOT a separate
-- SystemStatus model (deliberately rejected -- see ARCHITECTURE.md).
--
-- status: DATA_MODEL.md's original text lists "complete" / "delayed" /
-- "failed" -- none of which describes a row between INSERT and
-- completion. "in_progress" is added here as a fourth, necessary value
-- under the same "genuine architectural flaw" governance trigger
-- Sprint 1 used to add Event.event_id: a table can't be built and used
-- correctly without a row having *some* valid status while its source
-- is still being processed. DATA_MODEL.md is updated alongside this
-- migration to reflect it.
--
-- Real transactional semantics (Sprint 3 kickoff decision, not the
-- original Slice 4 default): a SyncRun only reaches 'complete' after
-- ALL of its source's writes commit successfully in one transaction; a
-- SyncRun marked 'failed' means NONE of that source's writes persisted
-- -- see database/repository.py's sync_run() context manager and the
-- removed per-statement commits in upsert_vehicle/insert_event/
-- upsert_pending_identity/resolve_pending_identity (Slices 1-3 had each
-- of those commit individually; that's no longer true as of this
-- migration's accompanying code change).
--
-- No FOREIGN KEY declared from event.sync_run_id to this table, even
-- though it now exists. Slices 1-3's tests populate event.sync_run_id
-- with arbitrary caller-supplied strings (e.g. "run-1") that were never
-- real SyncRun rows -- always a valid, intentionally opaque calling
-- convention (sync_run_id tags an Event for provenance; nothing in this
-- codebase has ever validated it against a real row). Enforcing a hard
-- FK now would break that convention across dozens of already-passing
-- tests, for a guarantee IMPLEMENTATION_PLAN.md's own Slice 4 success
-- criteria already satisfies a different way: "No orphaned Events, an
-- explicit assertion in tests" -- proven at the application level (see
-- tests/test_database_slice4.py) against the real pipeline's actual
-- sync_run_id values, not enforced via schema.

CREATE TABLE IF NOT EXISTS sync_run (
    sync_run_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source              TEXT NOT NULL,
    -- No Dealership table exists yet -- stays an unconstrained,
    -- unpopulated column until that's built, same as
    -- vehicle.current_dealership_id (see migrations/0001_initial.sql).
    dealership_id       TEXT,
    started_at          TEXT NOT NULL,
    completed_at        TEXT,
    records_processed   INTEGER,
    -- issues_found / tasks_generated are populated by Slice 5/6's Task
    -- and Recommendation logic, which doesn't exist yet -- left NULL
    -- here, not computed speculatively (no speculative schema/data,
    -- per IMPLEMENTATION_PLAN.md's Development Philosophy).
    issues_found        INTEGER,
    tasks_generated     INTEGER,
    status              TEXT NOT NULL DEFAULT 'in_progress'
);

CREATE INDEX IF NOT EXISTS idx_sync_run_source ON sync_run (source);
