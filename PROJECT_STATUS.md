# LotSync — Project Status

Engineering dashboard, kept current after every completed slice or
sprint. This is a snapshot, not a narrative — see `SPRINT_X_REVIEW.md`
files for the story behind each entry, and `IMPLEMENTATION_PLAN.md`
for the full plan this tracks progress against.

**Last updated:** 2026-07-26 (Sprint 4 closed — Phase 2 complete)

## Current position

| | |
|---|---|
| **Phase** | Phase 2 — Persistent operational platform — **COMPLETE** |
| **Sprint** | 4 (done — Slices 5, 6, 7) |
| **Slice** | None open. Phase 3 (web application) awaits an explicit product-owner decision to begin — see `IMPLEMENTATION_PLAN.md`'s "Scope boundary" |
| **Last completed** | Slice 7 — Dashboard data layer (Sprint 4) |

## Completed slices

| Slice | Sprint | Summary | Review |
|---|---|---|---|
| 1 — SQLite foundation, Keyper write path | 1 | `vehicle`/`event` tables live; Keyper's pass persists to both, additively, with zero CSV output change | [`SPRINT_1_REVIEW.md`](SPRINT_1_REVIEW.md) |
| 2 — Full source coverage + `PendingIdentity` capture | 2 | All 5 sources (Tekion, Sold, MDD, RecovR, RapidRecon) persist their contribution; Keyper's unresolved-identity population captured via the new `PendingIdentity` model instead of being dropped; zero CSV output change | [`SPRINT_2_REVIEW.md`](SPRINT_2_REVIEW.md) |
| 3 + 4 — Historical diffing, `PendingIdentity` promotion, SyncRun provenance | 3 | Diff-before-write across all four diffed sources, compared against Event history rather than the Vehicle cache (a real bug was found and fixed mid-sprint); `PendingIdentity` → `Vehicle` promotion, the system's first state transition; `SyncRun` table with real per-source transactional semantics (stronger than originally scoped); one documented, accepted idempotency gap for an internally-contradictory upstream Tekion input | [`SPRINT_3_REVIEW.md`](SPRINT_3_REVIEW.md) |
| 5 — Task generation | 4 | Pre-Sprint 4 design review reshaped `Task` into `commitment_standing`/`execution_status` (independent axes), a `TaskExecutionEvent` append-only log, and `escalated_from_task_id`. Backend: `generate_install_tasks` (reusing `build_tracker_install_tasks`), Reality-discharge wired into RecovR/Tekion-sold diffs, Intent-discharge (`cancel_task`/`escalate_task`), manual completion assertions coexisting with automatic discharge. Known, documented asymmetry: `install_mdd_beacon` Tasks have no automatic Honored path (MDD never positively confirms). | (no dedicated review file — folded into this dashboard + commit history) |
| 6 — Recommendation engine | 4 | `Recommendation` lifecycle (open/converted_to_task/dismissed), first rule (`key_out_aging`'s most-severe bucket, config-driven not hardcoded), conversion-to-Task as a ratified act, dismissed-reopening logic reusing Slice 3's Event history rather than new tracking fields. | (same as above) |
| 7 — Dashboard data layer | 4 | `queries/dashboard.py`: `connected_systems_status`, `recent_activity_feed`, `task_counts_by_department`, `inventory_health_percentage` — all read-only, no new stored state. Two terms neither `IMPLEMENTATION_PLAN.md` nor `DATA_MODEL.md` precisely defined ("health," "department" grouping) resolved as documented implementation decisions. Performance validated at 3,000 vehicles / 12,000 events — sub-second, no optimization needed yet. | (same as above) |

## Upcoming slices

None. **Phase 2 is complete.** Phase 3 (the web application — API,
authentication, UI) is the next phase per `PRODUCT.md`/
`IMPLEMENTATION_PLAN.md`, but starting it is an explicit product-owner
decision to make now that the boundary is actually reached, not an
automatic continuation — see this file's closing note below.

## Regression status

- **211 / 211 tests passing** (`tests/`, run via
  `PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"`
  from the repo root).
- Growth this sprint: 137 → 211 (+74 across Slices 5–7: 34 in
  `test_database_slice5.py`, 21 in `test_database_slice6.py`, 19 in
  `test_queries_dashboard.py`).
- No CI — the suite must be run manually. Standing risk, unchanged
  since Sprint 1.

## Environment

- Python 3.12.10, `pandas` 3.0.5, `openpyxl` 3.1.5, installed locally.
- Sandbox-specific hardcoded paths replaced with
  `LOTSYNC_UPLOADS_DIR` / `LOTSYNC_CONFIG_PATH` / `LOTSYNC_OUT_DIR` /
  `LOTSYNC_DB_PATH` env vars, each defaulting to a repo-relative
  `data/` subfolder.
- Git-tracked, tagged `v0.1.0`, `v0.2.0`, and `v0.3.0` (Sprint 3),
  pushed to `origin` on GitHub (private repository). Sprint 4's
  Slice 5/6/7 work is committed on top of `v0.3.0`; a `v0.4.0` tag
  (closing Sprint 4 and Phase 2) is this closeout's tagging step.

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
own. No governance document was touched during Slice 7 — `queries/
dashboard.py` is new, ungoverned application code, not a schema or
architecture change. No open governance questions at this time.

## Phase 2 complete — what the backend now provides

Every source (Tekion, Sold, MDD, RecovR, RapidRecon, Keyper) persists
its contribution to `Vehicle`/`Event`, diffed against history rather
than rewritten every sync (Slices 1–3). `PendingIdentity` captures and,
when a later sync resolves it, promotes unresolved Keyper identities
into real Vehicles (Slices 2–3). Every Event traces back to the
`SyncRun` that produced it, with real per-source transactional
semantics (Slice 4). `Task` models operational commitments with
independent commitment/execution axes, four terminal dispositions
split cleanly into Reality- and Intent-discharge, ratification/
authority tracking, and escalation (Slice 5). `Recommendation` models
interpretations distinct from commitments, with a working convert/
dismiss lifecycle (Slice 6). `queries/dashboard.py` proves all of the
above can actually answer dashboard-shaped questions without
introducing a second, driftable copy of any answer (Slice 7). Every
CSV report a dealership already depends on has produced byte-identical
output, unchanged, through all seven slices.

**Next decision, not yet made:** whether and when to begin Phase 3
(the web application — API, authentication, UI), per
`IMPLEMENTATION_PLAN.md`'s "Scope boundary." That's an explicit
product-owner call to make now that Phase 2 is actually done, not a
default continuation of this sprint.
