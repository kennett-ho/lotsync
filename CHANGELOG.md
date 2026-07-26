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

## Sprint 3 — Slices 3+4: Historical diffing, PendingIdentity promotion, SyncRun provenance (2026-07-25)

See [`SPRINT_3_REVIEW.md`](SPRINT_3_REVIEW.md) for full detail.

**Added**
- `database/migrations/0003_sync_run.sql` — `sync_run` table.
- `database/repository.py` — `get_last_event_detail_fields()`,
  `get_pending_identity()`, `resolve_pending_identity()`,
  `start_sync_run()`, `complete_sync_run()`, `fail_sync_run()`, and a
  `sync_run()` context manager giving each source's persistence pass
  real transactional semantics.
- `sync/reconciler.py` — `_promote_pending_identity_if_resolved()`,
  wired into `reconcile_keyper_tekion`'s two successful-resolution
  branches.
- `tests/test_database_slice3.py` (10 tests) and
  `tests/test_database_slice4.py` (8 tests).

**Changed**
- All four diffed persistence functions (`_persist_keyper_observation`,
  `persist_tekion_observations`, `persist_mdd_observations`,
  `persist_recovr_observations`) now write an `Event` only when the
  relevant claim actually changed since the last matching `Event` —
  not since whatever `vehicle`'s current-state field happens to hold
  (a real diffing bug, found and fixed mid-sprint; see
  `SPRINT_3_REVIEW.md`). Tekion's diff key is `(tekion_status,
  stock_number)`, not `tekion_status` alone.
- `upsert_vehicle()`, `insert_event()`, `upsert_pending_identity()`,
  `resolve_pending_identity()` no longer commit individually — commit
  responsibility moved to `sync_run()`'s transaction boundary.
- `main.py` wraps every source's persistence pass in `sync_run(...)`.
- `DATA_MODEL.md` — added `"in_progress"` to `SyncRun.status`'s
  documented values.

**No change to:** any CSV report's content or format. Verified via
full-suite regression (119 → 137 passing) plus an end-to-end `main.py`
smoke test against all five sources, with direct inspection of the
resulting `sync_run` table.

**Deliberately accepted, documented limitation:** a VIN with two
observations of the same `event_type` in one sync (the K80001/K80002
duplicate-sold-VIN fixture — an internally contradictory Tekion
export) does not achieve full idempotency on rerun. Not fixed; see
`SPRINT_3_REVIEW.md`'s "Problem solving" section for why.
