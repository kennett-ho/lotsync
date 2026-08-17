-- Sprint 10 (Rail D, Inventory Ingestion Safety) -- report_baseline:
-- the per-report-type row-count history that pre-sync validation
-- compares an incoming report against ("suspicious count change",
-- V1_1_RELEASE_READINESS 5.D exit 7).
--
-- Why a new table instead of reading sync_run.records_processed:
-- sync_run's "tekion" row deliberately covers BOTH Tekion report
-- types in one number (len(current) + len(sold) -- see
-- sync/pipeline.py), and SyncRun's documented meaning ("one execution
-- of the pipeline against one source") is governed by DATA_MODEL.md
-- and not stretched here. Baselines need to be scoped per
-- (vendor, report_type) -- a Tekion sold count must never judge a
-- Tekion current file -- so they get their own, purpose-named record.
--
-- One row per report accepted by an executed sync (written by
-- POST /inventory-sync/run AFTER the sync succeeds -- never by the
-- validation endpoint, which only reads). valid_rows is the count
-- validation computed (rows carrying usable identity); total_rows is
-- the raw data-row count. dealership_id is nullable and currently
-- always the deployment's serving store, same posture as
-- sync_run.dealership_id; per-row store scoping is the governed
-- Store #2 trigger (V1_1_RELEASE_READINESS section 7), not faked here.
--
-- Data-migration record (per .claude/workflows/data-migration.md):
-- additive CREATE TABLE only -- no existing table touched, no
-- backfill (pre-Sprint-10 syncs have no per-report-type counts to
-- backfill honestly; the first post-upgrade sync simply reports "No
-- prior baseline"), no destructive step. Rollback = DROP TABLE
-- report_baseline. Applied automatically by the existing migration
-- runner on non-production targets (local SQLite, Supabase DEV);
-- production applies it only via the governed release trains, where
-- beta.6-code-over-v10-DB rollback stays safe exactly as proven for
-- 0009 (old runner sees versions 1..10 applied, nothing pending, and
-- never reads this table). tools/migrate_sqlite_to_postgres.py's
-- EXPECTED_SCHEMA_VERSION/TABLE_ORDER/IDENTITY_PKS were updated in
-- the same commit (the standing migration-drift guard), and the
-- RC-freeze rehearsal refresh must include this table.

CREATE TABLE IF NOT EXISTS report_baseline (
    report_baseline_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor             TEXT NOT NULL,
    report_type        TEXT NOT NULL,
    slot               TEXT NOT NULL,
    dealership_id      TEXT REFERENCES dealership (dealership_id),
    total_rows         INTEGER NOT NULL,
    valid_rows         INTEGER NOT NULL,
    sync_started_at    TEXT NOT NULL,
    recorded_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- The one query shape validation uses: newest baseline for a
-- (vendor, report_type) pair.
CREATE INDEX IF NOT EXISTS idx_report_baseline_lookup
    ON report_baseline (vendor, report_type, report_baseline_id);
