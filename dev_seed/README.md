# dev_seed — the standing QA dealership

Sprint 04. This package turns DealerDOH DEV from "populated with fake
data" into a deliberate QA environment: every synthetic vehicle
exercises a specific implemented operational rule, and the expected
outcomes are enforced automatically on SQLite and PostgreSQL.

| File | Role |
|---|---|
| `scenarios.py` | The scenario roster and the six deterministic source exports it generates for each of the seed's two sync days. Every row carries its `QA-*` scenario ID in a comment. |
| `seeder.py` | Replays the scenarios through `sync/pipeline.run_inventory_sync()` — the real Inventory Sync API path. Nothing writes to the database directly. |
| `expected.py` | Machine-readable expected outcomes, per scenario. Imported by `tests/test_qa_dataset.py`. |

**Human-readable source of truth:** `SYNTHETIC_QA_MATRIX.md` (repo
root). If the matrix and this package disagree, the matrix wins.
**Operator guide:** `DEV_QA_GUIDE.md` (repo root) — what to click,
what to expect, how to reseed.

## How it works

Two consecutive sync days, replayed through the real pipeline:

- **Day 1** (sync date `2026-07-20`) establishes the baseline: 17 of
  the 18 tasks, the first recommendation, all pending identities.
- **Day 2** (sync date `2026-07-21`, the **QA reference date**)
  exercises the transitions: a sale moots an install task, a RecovR
  pairing honors one, the 3-day and 25-day thresholds are crossed, an
  ambiguous identity resolves, and every unchanged vehicle re-observes
  without adding Timeline noise.

All aging math runs against the pinned sync dates, so expected
outcomes are stable forever regardless of when the seed runs. Source
CSVs are generated into a temp directory at seed time from
`scenarios.py` — the scenario definitions are the single source of
truth, with no checked-in CSV copies to drift.

## Seeding / resetting a development database

Always via `seed_dev.py` (repo root), which carries the production
guardrails (refuses `ENVIRONMENT=production` and the production DB
path):

```bash
# local SQLite (default: data/dealerdoh-dev-seed.db)
PYTHONPATH=.. python seed_dev.py --reset

# deployed dev (Supabase PostgreSQL) -- run with the dev database's env
DATABASE_ENGINE=postgres DATABASE_URL=<dev-only DSN> PYTHONPATH=.. python seed_dev.py --reset
```

`--reset` drops and re-migrates first; the standing totals in
`SYNTHETIC_QA_MATRIX.md` are exact only after a reset+seed (replaying
Day 2 onto an already-seeded database is idempotent everywhere except
QA-CONFLICT-002's documented re-fire).

## Never

- Never run against production (`master`, `lotsync-api`,
  `/var/data/lotsync.db`). The guardrails refuse, and the rule stands
  regardless.
- Never edit standing dev data by hand to "fix" a count — reseed, or
  fix the scenario definition and matrix together.
