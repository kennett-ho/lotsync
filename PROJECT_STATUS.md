# LotSync — Project Status

Engineering dashboard, kept current after every completed slice or
sprint. This is a snapshot, not a narrative — see `SPRINT_X_REVIEW.md`
files for the story behind each entry, and `IMPLEMENTATION_PLAN.md`
for the full plan this tracks progress against.

**Last updated:** 2026-07-23 (Sprint 1 closed; Slice 2 design decided; Git baseline established)

## Current position

| | |
|---|---|
| **Phase** | Phase 2 — Persistent operational platform |
| **Sprint** | 2 (not yet started) |
| **Slice** | 2 — Full source coverage (not yet started) |
| **Last completed** | Slice 1 — SQLite foundation + Keyper write path (Sprint 1) |

## Completed slices

| Slice | Sprint | Summary | Review |
|---|---|---|---|
| 1 — SQLite foundation, Keyper write path | 1 | `vehicle`/`event` tables live; Keyper's pass persists to both, additively, with zero CSV output change | [`SPRINT_1_REVIEW.md`](SPRINT_1_REVIEW.md) |

## Upcoming slices

| Slice | Sprint | What it needs to decide or prove |
|---|---|---|
| 2 — Full source coverage + `PendingIdentity` capture | 2 | Extend the write path to Tekion, Sold, MDD, RecovR, RapidRecon. Capture Keyper's unresolved-identity records as `PendingIdentity` rows (decided — see `DATA_MODEL.md`'s `PendingIdentity` entry). **Design already decided, not open:** promotion of a `PendingIdentity` to a real `Vehicle` is explicitly out of scope for this slice — that's Slice 3. |
| 3 + 4 — Historical diffing, `PendingIdentity` promotion, SyncRun provenance | 3 | Diff-before-write for Events; `PendingIdentity` → `Vehicle` promotion (the system's first state transition); `SyncRun` table and provenance on every Event. |
| 5 — Task generation | 4 | First slice where the database becomes load-bearing (auto-resolving Tasks). |
| 6 — Recommendation engine | 5 | Convert/dismiss lifecycle. |
| 7 — Dashboard data layer | 6 | Query functions proving the DB can answer dashboard-shaped questions; end of Phase 2. |

## Regression status

- **91 / 91 tests passing** (`tests/`, run via
  `PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"`
  from the repo root).
- Baseline before Phase 2 work began: 81 tests. Growth is expected and
  required every sprint per `IMPLEMENTATION_PLAN.md`'s Success Metrics
  — a shrinking count is a red flag, not a cleanup.
- No CI — the suite must be run manually. Flagged as a standing risk
  in `SPRINT_1_REVIEW.md`.

## Environment

- Python 3.12.10, `pandas` 3.0.5, `openpyxl` 3.1.5, installed locally.
- Sandbox-specific hardcoded paths replaced with
  `LOTSYNC_UPLOADS_DIR` / `LOTSYNC_CONFIG_PATH` / `LOTSYNC_OUT_DIR` /
  `LOTSYNC_DB_PATH` env vars, each defaulting to a repo-relative
  `data/` subfolder.
- Git-tracked as of this update. Tagged `v0.1.0` (Phase 2 Sprint 1
  baseline). Resolves the standing "no version control" risk named in
  `SPRINT_1_REVIEW.md`.

## Governance document status

Per the engineering workflow established after Sprint 1:
`VISION.md`, `PRODUCT.md`, and `ARCHITECTURE.md` are untouched since
`PRODUCT.md`'s creation and remain fully consistent with everything
implemented so far. `DATA_MODEL.md` received two changes, both under
the "genuine architectural flaw" governance trigger, not a design
change: added `Event.event_id` (Sprint 1 — the table had no primary
key) and added the `PendingIdentity` model (Sprint 2 design discussion,
pre-implementation — `Vehicle` had no honest way to represent an
observation with unresolved identity). No open governance questions
at this time.
