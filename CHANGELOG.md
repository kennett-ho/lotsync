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
