# LotSync — Project Status

Engineering dashboard, kept current after every completed slice or
sprint. This is a snapshot, not a narrative — see `SPRINT_X_REVIEW.md`
files for the story behind each entry, and `IMPLEMENTATION_PLAN.md`
for the full plan this tracks progress against.

**Last updated:** 2026-07-23 (Sprint 2 / Slice 2 closed)

## Current position

| | |
|---|---|
| **Phase** | Phase 2 — Persistent operational platform |
| **Sprint** | 3 (not yet started) |
| **Slice** | 3 + 4 — Historical diffing, `PendingIdentity` promotion, SyncRun provenance (not yet started) |
| **Last completed** | Slice 2 — Full source coverage + `PendingIdentity` capture (Sprint 2) |

## Completed slices

| Slice | Sprint | Summary | Review |
|---|---|---|---|
| 1 — SQLite foundation, Keyper write path | 1 | `vehicle`/`event` tables live; Keyper's pass persists to both, additively, with zero CSV output change | [`SPRINT_1_REVIEW.md`](SPRINT_1_REVIEW.md) |
| 2 — Full source coverage + `PendingIdentity` capture | 2 | All 5 sources (Tekion, Sold, MDD, RecovR, RapidRecon) persist their contribution; Keyper's unresolved-identity population captured via the new `PendingIdentity` model instead of being dropped; zero CSV output change | [`SPRINT_2_REVIEW.md`](SPRINT_2_REVIEW.md) |

## Upcoming slices

| Slice | Sprint | What it needs to decide or prove |
|---|---|---|
| 3 + 4 — Historical diffing, `PendingIdentity` promotion, SyncRun provenance | 3 | Diff-before-write for Events (idempotency); `PendingIdentity` → `Vehicle` promotion (the system's first state transition — decided in Sprint 2's design discussion, not yet built); `SyncRun` table and provenance on every Event. One open question carried from Sprint 2: does `PendingIdentity.last_observed_at` advancing count as "a change worth an Event," or is it exempt the same way `days_out` is exempt? Not yet answered. |
| 5 — Task generation | 4 | First slice where the database becomes load-bearing (auto-resolving Tasks). |
| 6 — Recommendation engine | 5 | Convert/dismiss lifecycle. |
| 7 — Dashboard data layer | 6 | Query functions proving the DB can answer dashboard-shaped questions; end of Phase 2. |

## Regression status

- **119 / 119 tests passing** (`tests/`, run via
  `PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"`
  from the repo root).
- Growth this sprint: 91 → 119 (+28, `tests/test_database_slice2.py`).
  One pre-existing Slice 1 test was also fixed in place (a hardcoded
  migration count that Slice 2's new migration file exposed as fragile
  — see `SPRINT_2_REVIEW.md`, "Unexpected discoveries").
- No CI — the suite must be run manually. Standing risk, unchanged
  since Sprint 1.

## Environment

- Python 3.12.10, `pandas` 3.0.5, `openpyxl` 3.1.5, installed locally.
- Sandbox-specific hardcoded paths replaced with
  `LOTSYNC_UPLOADS_DIR` / `LOTSYNC_CONFIG_PATH` / `LOTSYNC_OUT_DIR` /
  `LOTSYNC_DB_PATH` env vars, each defaulting to a repo-relative
  `data/` subfolder.
- Git-tracked, tagged `v0.1.0` (Phase 2 Sprint 1 baseline, pushed to
  `origin` on GitHub — private repository). Sprint 2's work is
  committed on top of that tag; no new tag has been cut yet.

## Governance document status

Per the engineering workflow established after Sprint 1:
`VISION.md`, `PRODUCT.md`, and `ARCHITECTURE.md` remain untouched and
fully consistent with everything implemented through Sprint 2.
`DATA_MODEL.md` has received two changes total, both under the
"genuine architectural flaw" governance trigger, not a design change:
added `Event.event_id` (Sprint 1 — the table had no primary key) and
added the `PendingIdentity` model (decided during Sprint 2's
pre-implementation design discussion — `Vehicle` had no honest way to
represent an observation with unresolved identity). No governance
document was touched *during* Sprint 2's actual implementation —
everything built matched what was already decided going in. No open
governance questions at this time.
