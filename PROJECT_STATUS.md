# LotSync — Project Status

Engineering dashboard, kept current after every completed slice or
sprint. This is a snapshot, not a narrative — see `SPRINT_X_REVIEW.md`
files for the story behind each entry, and `IMPLEMENTATION_PLAN.md`
for the full plan this tracks progress against.

**Last updated:** 2026-07-26 (Sprint 4 in progress — Slices 5+6 backend complete)

## Current position

| | |
|---|---|
| **Phase** | Phase 2 — Persistent operational platform |
| **Sprint** | 4 (in progress) |
| **Slice** | 7 — Dashboard data layer (not yet started) |
| **Last completed** | Slice 6 — Recommendation engine (Sprint 4) |

## Completed slices

| Slice | Sprint | Summary | Review |
|---|---|---|---|
| 1 — SQLite foundation, Keyper write path | 1 | `vehicle`/`event` tables live; Keyper's pass persists to both, additively, with zero CSV output change | [`SPRINT_1_REVIEW.md`](SPRINT_1_REVIEW.md) |
| 2 — Full source coverage + `PendingIdentity` capture | 2 | All 5 sources (Tekion, Sold, MDD, RecovR, RapidRecon) persist their contribution; Keyper's unresolved-identity population captured via the new `PendingIdentity` model instead of being dropped; zero CSV output change | [`SPRINT_2_REVIEW.md`](SPRINT_2_REVIEW.md) |
| 3 + 4 — Historical diffing, `PendingIdentity` promotion, SyncRun provenance | 3 | Diff-before-write across all four diffed sources, compared against Event history rather than the Vehicle cache (a real bug was found and fixed mid-sprint); `PendingIdentity` → `Vehicle` promotion, the system's first state transition; `SyncRun` table with real per-source transactional semantics (stronger than originally scoped); one documented, accepted idempotency gap for an internally-contradictory upstream Tekion input | [`SPRINT_3_REVIEW.md`](SPRINT_3_REVIEW.md) |
| 5 — Task generation | 4 | Pre-Sprint 4 design review reshaped `Task` into `commitment_standing`/`execution_status` (independent axes), a `TaskExecutionEvent` append-only log, and `escalated_from_task_id`. Backend: `generate_install_tasks` (reusing `build_tracker_install_tasks`), Reality-discharge wired into RecovR/Tekion-sold diffs, Intent-discharge (`cancel_task`/`escalate_task`), manual completion assertions coexisting with automatic discharge. Known, documented asymmetry: `install_mdd_beacon` Tasks have no automatic Honored path (MDD never positively confirms). | (no dedicated review file — folded into this dashboard + commit history) |
| 6 — Recommendation engine | 4 | `Recommendation` lifecycle (open/converted_to_task/dismissed), first rule (`key_out_aging`'s most-severe bucket, config-driven not hardcoded), conversion-to-Task as a ratified act, dismissed-reopening logic reusing Slice 3's Event history rather than new tracking fields. | (same as above) |

## Upcoming slices

| Slice | Sprint | What it needs to decide or prove |
|---|---|---|
| 7 — Dashboard data layer | 4 | Query functions proving the DB can answer dashboard-shaped questions (task health, rule health, recent activity); end of Phase 2. Only after this does Phase 3 (web application, per `PRODUCT.md`) begin, per `IMPLEMENTATION_PLAN.md`'s existing scope boundary. |

## Regression status

- **192 / 192 tests passing** (`tests/`, run via
  `PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"`
  from the repo root).
- Growth this sprint so far: 137 → 192 (+55: 34 in `test_database_slice5.py`,
  21 in `test_database_slice6.py`).
- No CI — the suite must be run manually. Standing risk, unchanged
  since Sprint 1.

## Environment

- Python 3.12.10, `pandas` 3.0.5, `openpyxl` 3.1.5, installed locally.
- Sandbox-specific hardcoded paths replaced with
  `LOTSYNC_UPLOADS_DIR` / `LOTSYNC_CONFIG_PATH` / `LOTSYNC_OUT_DIR` /
  `LOTSYNC_DB_PATH` env vars, each defaulting to a repo-relative
  `data/` subfolder.
- Git-tracked, tagged `v0.1.0`, `v0.2.0`, and `v0.3.0` (Sprint 3),
  pushed to `origin` on GitHub (private repository). Sprint 4's Slice
  5/6 work is committed on top of `v0.3.0`; no new tag has been cut yet
  -- Sprint 4 isn't closed out (Slice 7 remains).

## Governance document status

Per the engineering workflow established after Sprint 1:
`VISION.md` and `PRODUCT.md` remain untouched and fully consistent with
everything implemented through Sprint 4 so far.
`DATA_MODEL.md` has received five changes total, all under the
"genuine architectural flaw" governance trigger, not a design change:
added `Event.event_id` (Sprint 1 — the table had no primary key), added
the `PendingIdentity` model (Sprint 2 — `Vehicle` had no honest way to
represent an observation with unresolved identity), added
`"in_progress"` to `SyncRun.status`'s documented values (Sprint 3 — the
original three values had no way to describe a row between INSERT and
completion), replaced `Task.status`'s three values with
`commitment_standing`/`execution_status` plus a new `TaskExecutionEvent`
entity (Pre-Sprint 4 design review — the original status couldn't
honestly represent a commitment discharged as moot, cancelled, or
superseded), and added `created_at`/`resolved_at` to `Recommendation`
(Slice 6 — implementing "a dismissed Recommendation does not reappear
unless state changed" requires knowing *when* it was dismissed, which
the table had no way to represent). `ARCHITECTURE.md` was touched for
the first time in Phase 2 during Slice 5 — a wording tightening
(Reality-discharge vs Intent-discharge) and a pointer to
`DECISION_FRAMEWORK.md`'s four-layer reasoning structure, both required
by `SPRINT_4_CHECKLIST.md`, not a new decision made outside review.
`PRODUCT.md`'s identical "closes itself" wording gap was deliberately
left alone — not in the checklist, and the design review explicitly
judged it not urgent enough to justify reopening that document on its
own. No open governance questions at this time.
