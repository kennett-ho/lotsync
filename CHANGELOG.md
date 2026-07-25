# Changelog

Established at the start of Phase 2's ongoing sprint workflow. Entries
before this point (the Phase 1 module split) predate this file and are
described in `ARCHITECTURE.md` instead, not backfilled here.

Each entry links to its sprint review for full detail — this file is
a scannable log, not the record itself.

## Sprint 1 — Slice 1: SQLite foundation + Keyper write path (2026-07-23)

See [`SPRINT_1_REVIEW.md`](SPRINT_1_REVIEW.md) for full detail.

**Added**
- `database/migrations/0001_initial.sql` — `vehicle` and `event` tables.
- `database/repository.py` — `connect()`, `upsert_vehicle()`, `insert_event()`.
- `reconcile_keyper_tekion()` gained optional `db_conn`/`sync_run_id`
  parameters; when supplied, VIN-resolvable Keyper records additionally
  persist to `vehicle`/`event`. Default behavior (no params) unchanged.
- `PROJECT_STATUS.md`, this file, and the standing sprint-review
  workflow itself.

**Changed**
- `event_id` added to `Event` (`DATA_MODEL.md`, `models/event.py`) —
  the table had no primary key.
- Hardcoded `/mnt/user-data/...` paths replaced with
  `LOTSYNC_UPLOADS_DIR` / `LOTSYNC_CONFIG_PATH` / `LOTSYNC_OUT_DIR`
  env-var overrides, defaulting to a repo-relative `data/` folder.

**No change to:** any CSV report's content or format. See Sprint 1's
Definition of Done verification for how this was confirmed.

## Sprint 2 — Slice 2: Full source coverage + PendingIdentity capture (2026-07-23)

See [`SPRINT_2_REVIEW.md`](SPRINT_2_REVIEW.md) for full detail.

**Added**
- `database/migrations/0002_pending_identity.sql` — `pending_identity` table.
- `database/repository.py` — `upsert_pending_identity()`, keyed by
  `(source, raw_identifier)` (upsert, not insert-every-run).
- `sync/reconciler.py` — four new persistence functions:
  `persist_tekion_observations()`, `persist_mdd_observations()`,
  `persist_recovr_observations()`, `persist_rapidrecon_observations()`,
  plus `_persist_pending_identity()` wired into
  `reconcile_keyper_tekion()`'s three unresolved-identity exception
  branches. All are no-ops when `db_conn` is omitted.
- `main.py` wires all four new functions into the pipeline.
- `tests/test_database_slice2.py` (28 tests) and
  `tests/fixtures/synthetic/rapidrecon.csv` (no RapidRecon fixture
  existed before this sprint).

**Changed**
- `DATA_MODEL.md` — added the `PendingIdentity` model (decided during
  this sprint's pre-implementation design discussion).
- `tests/test_database_slice1.py` — fixed a hardcoded migration-count
  assertion that this sprint's new migration file exposed as fragile;
  also fixed a connection-leak-on-assertion-failure that caused a
  confusing Windows `PermissionError` instead of a clear test failure.

**No change to:** any CSV report's content or format. Verified via
full-suite regression (91 → 119 passing) plus an end-to-end `main.py`
smoke test against all five sources.

**Deliberately deferred to Slice 3:** `PendingIdentity` → `Vehicle`
promotion (detecting a previously-unresolved identifier resolving).
Capture-only in this sprint, as scoped from the outset.
