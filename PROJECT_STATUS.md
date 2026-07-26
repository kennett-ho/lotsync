# LotSync — Project Status

Engineering dashboard, kept current after every completed slice or
sprint. This is a snapshot, not a narrative — see `SPRINT_X_REVIEW.md`
files for the story behind each entry, and `IMPLEMENTATION_PLAN.md`
for the full plan this tracks progress against.

**Last updated:** 2026-07-25 (Sprint 3 / Slices 3+4 closed)

## Current position

| | |
|---|---|
| **Phase** | Phase 2 — Persistent operational platform |
| **Sprint** | 4 (not yet started) |
| **Slice** | 5 — Task generation (design review complete, implementation not yet started — see [`SPRINT_4_DESIGN_REVIEW_SUMMARY.md`](SPRINT_4_DESIGN_REVIEW_SUMMARY.md) / [`SPRINT_4_CHECKLIST.md`](SPRINT_4_CHECKLIST.md)) |
| **Last completed** | Slices 3 + 4 — Historical diffing, `PendingIdentity` promotion, SyncRun provenance (Sprint 3) |

## Completed slices

| Slice | Sprint | Summary | Review |
|---|---|---|---|
| 1 — SQLite foundation, Keyper write path | 1 | `vehicle`/`event` tables live; Keyper's pass persists to both, additively, with zero CSV output change | [`SPRINT_1_REVIEW.md`](SPRINT_1_REVIEW.md) |
| 2 — Full source coverage + `PendingIdentity` capture | 2 | All 5 sources (Tekion, Sold, MDD, RecovR, RapidRecon) persist their contribution; Keyper's unresolved-identity population captured via the new `PendingIdentity` model instead of being dropped; zero CSV output change | [`SPRINT_2_REVIEW.md`](SPRINT_2_REVIEW.md) |
| 3 + 4 — Historical diffing, `PendingIdentity` promotion, SyncRun provenance | 3 | Diff-before-write across all four diffed sources, compared against Event history rather than the Vehicle cache (a real bug was found and fixed mid-sprint); `PendingIdentity` → `Vehicle` promotion, the system's first state transition; `SyncRun` table with real per-source transactional semantics (stronger than originally scoped); one documented, accepted idempotency gap for an internally-contradictory upstream Tekion input | [`SPRINT_3_REVIEW.md`](SPRINT_3_REVIEW.md) |

## Upcoming slices

| Slice | Sprint | What it needs to decide or prove |
|---|---|---|
| 5 — Task generation | 4 | First slice where the database becomes load-bearing (auto-resolving Tasks). Must call the same `rules/aging.py`/`rules/inventory.py` functions the CSV reports already use, not reimplement them. Pre-implementation design review complete — concrete work items in [`SPRINT_4_CHECKLIST.md`](SPRINT_4_CHECKLIST.md), including required `DATA_MODEL.md`/`ARCHITECTURE.md` updates not yet made. |
| 6 — Recommendation engine | 5 | Convert/dismiss lifecycle. |
| 7 — Dashboard data layer | 6 | Query functions proving the DB can answer dashboard-shaped questions; end of Phase 2. |

## Regression status

- **137 / 137 tests passing** (`tests/`, run via
  `PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"`
  from the repo root).
- Growth this sprint: 119 → 137 (+18: 10 in `test_database_slice3.py`,
  8 in `test_database_slice4.py`). One pre-existing Slice 1 test was
  also updated in place — it was written at Sprint 1 specifically as
  the canary for this sprint's diffing change (see `SPRINT_3_REVIEW.md`).
- No CI — the suite must be run manually. Standing risk, unchanged
  since Sprint 1.

## Environment

- Python 3.12.10, `pandas` 3.0.5, `openpyxl` 3.1.5, installed locally.
- Sandbox-specific hardcoded paths replaced with
  `LOTSYNC_UPLOADS_DIR` / `LOTSYNC_CONFIG_PATH` / `LOTSYNC_OUT_DIR` /
  `LOTSYNC_DB_PATH` env vars, each defaulting to a repo-relative
  `data/` subfolder.
- Git-tracked, tagged `v0.1.0` and `v0.2.0`, both pushed to `origin` on
  GitHub (private repository). Sprint 3's work is committed on top of
  `v0.2.0`; a `v0.3.0` tag is this sprint's closeout step.

## Governance document status

Per the engineering workflow established after Sprint 1:
`VISION.md`, `PRODUCT.md`, and `ARCHITECTURE.md` remain untouched and
fully consistent with everything implemented through Sprint 3.
`DATA_MODEL.md` has received three changes total, all under the
"genuine architectural flaw" governance trigger, not a design change:
added `Event.event_id` (Sprint 1 — the table had no primary key), added
the `PendingIdentity` model (Sprint 2 — `Vehicle` had no honest way to
represent an observation with unresolved identity), and added
`"in_progress"` to `SyncRun.status`'s documented values (Sprint 3 — the
original three values had no way to describe a row between INSERT and
completion, the same class of gap `Event.event_id` closed). No
governance document was touched for any other reason during Sprint 3 —
everything else built matched what was already decided going in
(`DECISION_FRAMEWORK.md`, `IMPLEMENTATION_PLAN.md`'s existing Slice 3/4
scope). No open governance questions at this time.
