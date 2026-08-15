# SQLite → PostgreSQL Migration Assessment

> **Status update (Infrastructure Sprint 03, 2026-08-15):** the
> migration this document assessed has now been implemented **for the
> DealerDOH development environment only** — dual-engine persistence
> behind `DATABASE_ENGINE`, PostgreSQL migrations, dual-engine CI, and
> the deployed dev API running against Supabase PostgreSQL. Production
> remains on SQLite exactly as this document recommended, until its own
> planned migration sprint. See `DEV_ENVIRONMENT.md` for the
> implemented architecture. The assessment below is preserved unchanged
> as the historical record; its findings held up well — the one item it
> flagged as a real design decision (`event.sync_run_id`) was resolved
> by preserving TEXT semantics with explicit casts/coercion, and the
> one incompatibility it did not list (`IS NOT 'Sold'` in
> `queries/vehicles.py`) was found and fixed during implementation.

**Original status line: assessment only. Nothing has been migrated. No code in this document's scope has been changed.**

Produced ahead of the v0.8.x Render deployment, per the standing decision in `PRE_DEPLOYMENT_REVIEW.md` (R1/D6) and `DEPLOYMENT.md`: SQLite stays the database for this first deployment (backed by a Render persistent disk); Postgres is evaluated here as a scoped follow-up, not a blocker.

**Method:** every `.sql` migration file was read in full; every `conn.execute(...)` call site in the backend (`database/repository.py`, `queries/*.py`, `sync/reconciler.py`, `sync/pipeline.py`, `api/*`) was located and inspected; `tests/README.md`'s stated testing philosophy was checked against actual test code. This codebase has **no ORM** — all persistence is raw SQL via Python's stdlib `sqlite3` module (`models/*.py`'s dataclasses are explicitly documented elsewhere as unused scaffolding) — so "ORM behavior" as a category doesn't apply here; the closest analogue is DB-API driver behavior, covered below.

---

## Findings by category

### 1. Dependencies

| Item | Classification | Notes |
|---|---|---|
| `import sqlite3` (stdlib, zero install cost) everywhere a connection is opened or typed (`sqlite3.Connection` type hints — 15 files, 57 occurrences) | **Trivial** | Swap for `psycopg` (v3) or `psycopg2-binary` — a genuinely new PyPI dependency (`requirements.txt` currently has zero DB-driver dependency at all, since `sqlite3` is stdlib). Type hints are a mechanical rename. |
| No ORM anywhere | N/A | Nothing to migrate in this category; see driver-level items below instead. |

### 2. SQL statements — placeholder syntax

| Item | Classification | Notes |
|---|---|---|
| `?` positional placeholders | **Moderate** | Used at **~56 source call sites** (`database/repository.py`: 36, `sync/reconciler.py`: 4, `sync/pipeline.py`: 2, `queries/*.py`: 13, `api/app.py`: 1) plus **~115 more in tests**. Postgres drivers (`psycopg2`/`psycopg3`) use `%s`, not `?`. Purely mechanical, but touches essentially every SQL string in the codebase — needs a careful pass (not a blind global find/replace, since a few queries are built via f-string column-list interpolation around the placeholders) and full re-test. |
| `ON CONFLICT (...) DO UPDATE SET col = excluded.col` (upsert syntax) | **Trivial** | Used in `upsert_vehicle`, `upsert_event_freshness`, `upsert_pending_identity`. Postgres supports this **exact same syntax** (SQLite's upsert clause was itself modeled on Postgres's) — `EXCLUDED` works identically. Only the `?`→`%s` swap (already counted above) touches these. |
| `INSERT OR IGNORE INTO vehicle (vin) VALUES (?)` | **Trivial** | One occurrence (`upsert_vehicle`'s no-fields branch) — SQLite-only keyword, no Postgres equivalent by that name. Direct rewrite: `INSERT INTO vehicle (vin) VALUES (%s) ON CONFLICT (vin) DO NOTHING`. |
| `cur.lastrowid` | **Moderate** | 6 occurrences in `database/repository.py` (`insert_event`, `start_sync_run`, `insert_task`, `escalate_task`, `insert_task_execution_event`, `insert_recommendation`). Not supported by psycopg2/psycopg3 — Postgres has no universal "last inserted rowid." Each of the 6 `INSERT` statements needs a `RETURNING <pk_column>` clause, and each caller needs `cur.lastrowid` → `cur.fetchone()[0]`. Mechanical, but six distinct call sites to individually verify, not one sweep. |
| `event.sync_run_id` (TEXT) compared against `sync_run.sync_run_id` (INTEGER PK) | **High risk** | See dedicated writeup below — this is the one item that's a real design decision, not a mechanical translation. |

### 3. Migrations (`database/migrations/*.sql`, all 8 files read in full)

| Item | Classification | Notes |
|---|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | **Trivial per column** | 6 tables (`event`, `pending_identity`, `sync_run`, `task`, `task_execution_event`, `recommendation`). Postgres equivalent: `INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY` (or legacy `SERIAL PRIMARY KEY`). Well-understood, mechanical — but touches 5 of the 8 migration files. |
| `TEXT`, `INTEGER`, `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `FOREIGN KEY (...) REFERENCES ...`, composite `PRIMARY KEY (...)`, `UNIQUE (...)`, `ALTER TABLE ... ADD COLUMN ...` | **Trivial / no change** | Standard ANSI SQL, supported identically by Postgres. Every migration file's structure otherwise ports as-is. |
| Migration runner itself (`_pending_migrations`, `apply_migrations` — `glob.glob` + filename-prefix parsing + `schema_migrations` bookkeeping table) | **Trivial / no change** | Pure Python + portable SQL; backend-agnostic. |
| `conn.executescript(fh.read())` (runs each `.sql` file as one multi-statement script) | **Moderate** | Neither psycopg2 nor psycopg3 has a direct `executescript()` equivalent, though both can run a `;`-separated multi-statement string via one `cursor.execute()` call (libpq supports multi-statement query text). Behaviorally close but not identical — `executescript()` has SQLite-specific implicit-commit semantics that need re-verification against `apply_migrations()`'s surrounding commit/rollback logic. |
| **Net migration-file cost** | — | Every one of the 8 files needs a Postgres-dialect copy; in practice only the `AUTOINCREMENT` keyword actually changes — everything else is copy-paste. Whether that becomes a parallel `migrations_postgres/` directory or a one-time rewrite (there's no real production SQLite data to preserve pre-launch) is a decision for whoever does this, not a technical blocker either way. |

### 4. Pragmas

| Item | Classification | Notes |
|---|---|---|
| `PRAGMA foreign_keys = ON` (`database/repository.py:86`) | **Trivial** | SQLite disables FK enforcement by default and needs this pragma per-connection. Postgres enforces FKs unconditionally, always — this line is simply deleted, no replacement needed. |
| `check_same_thread=False` (`sqlite3.connect(..., check_same_thread=False)`) | **Moderate–High** (see below) | SQLite-specific Python API parameter; the concept doesn't exist for network drivers. Removing it is trivial — but see the connection-pooling writeup below for what it's currently masking. |

### 5. Datatypes

| Item | Classification | Notes |
|---|---|---|
| `detail_fields` JSON stored as `TEXT` via `json.dumps`/`json.loads` | **Trivial / no change** | Postgres `TEXT` stores this identically. Adopting native `JSONB` is a nice-to-have future optimization, not something the migration requires. |
| Timestamps (`observed_at`, `created_at`, etc.) stored as ISO-8601 `TEXT` via `datetime.now().isoformat()` | **Trivial / no change** | Lexical sort order equals chronological order for ISO-8601 — works identically in Postgres. Adopting native `TIMESTAMPTZ` is a nice-to-have, not required. |
| `event.sync_run_id` TEXT vs. `sync_run.sync_run_id` INTEGER | **High risk** | See below. |

### 6. Filesystem assumptions

| Item | Classification | Notes |
|---|---|---|
| `LOTSYNC_DB_PATH` as a single filesystem path; `os.makedirs(dirname, exist_ok=True)` before connecting | **Moderate** | Postgres needs a connection string/DSN instead (e.g. Render's `DATABASE_URL`, `postgresql://user:pass@host:5432/dbname`). `connect()`'s signature changes shape entirely (path → DSN), and the directory-creation step becomes meaningless and is deleted. Most callers (`main.py`, `api/dependencies.py`, every test) call `connect()` with no arguments today, so they're insulated from the signature change itself — but every one of them is still affected by *what* `connect()` now requires to be configured (a reachable Postgres server, not just a writable directory). |

---

## The one real design decision: `event.sync_run_id`

`event.sync_run_id` is declared `TEXT` (`migrations/0001_initial.sql`), while `sync_run.sync_run_id` is `INTEGER PRIMARY KEY AUTOINCREMENT` (`migrations/0003_sync_run.sql`) — added three migrations later, deliberately without a matching type or a `FOREIGN KEY`, per `migrations/0003_sync_run.sql`'s own comment: `event.sync_run_id` is "an opaque provenance tag," and tests intentionally write arbitrary non-numeric strings like `"run-1"` into it without a real `SyncRun` row existing at all.

`database/repository.py`'s own docstring (on `start_sync_run`) and a passing test (`tests/test_database_slice4.py`'s orphan-check) both explicitly document and rely on SQLite's loose type-affinity treating `'1' = 1` as true *inside a query* — e.g. `SELECT COUNT(*) FROM event WHERE sync_run_id NOT IN (SELECT sync_run_id FROM sync_run)` silently coerces the TEXT/INTEGER comparison and returns the right answer today. Postgres is strictly typed: `text = integer` either raises `operator does not exist` outright or requires an explicit cast, and will never silently coerce.

This needs an actual decision, not a mechanical translation, before any migration code is written:

- **(a) Make `event.sync_run_id` a real `INTEGER`** matching `sync_run.sync_run_id`, and give up the "opaque string tag" convenience — every test currently writing a fake string sync_run_id would need to either write a real integer or use `NULL`, and the "no FK, deliberately opaque" design note in `migrations/0003_sync_run.sql` would need revisiting.
- **(b) Keep it `TEXT`**, and add explicit `::text` casts everywhere it's compared against `sync_run.sync_run_id` (starting with the orphan-check query) — preserves today's semantics exactly, but requires auditing every comparison site for the same silent-coercion pattern, not just the one test that happens to assert it today.

Either is workable. Neither is mechanical. This should be resolved first, since it shapes what the Postgres version of `migrations/0001_initial.sql`/`0003_sync_run.sql` and several `repository.py` functions actually look like.

---

## Connection architecture: pooling

`api/dependencies.py`'s `get_db()` opens a brand-new connection per request today — cheap for a local SQLite file, and the reason `check_same_thread=False` exists at all (documented in `repository.py` as a Phase 3, Sprint 2 fix for FastAPI's threadpool). For a networked Postgres server, opening a fresh TCP + auth handshake on every single request is slow and will eventually exhaust the server's connection limit under any real concurrent load. This isn't a syntax change — it's a genuine architecture addition: a connection pool (`psycopg_pool.ConnectionPool`, or an external pooler like PgBouncer, which Render's managed Postgres supports) needs to be introduced and wired into `get_db()`. Classified **Moderate–High**: well-trodden, not exotic, but a new moving part with its own configuration and failure modes, not present anywhere in this codebase today.

---

## Test infrastructure: the dominant cost

**High risk / high effort — this is the largest single item in this assessment, bigger than all the application-code items combined.**

Every one of this project's ~360 tests that touches the database opens `connect(":memory:")` — a SQLite-only, zero-setup, automatically-isolated-per-test database requiring no external process. `tests/README.md` states "no external dependencies" as a deliberate project principle (citing `ARCHITECTURE.md`'s "minimal dependencies" stance), and there is currently no CI configuration in this repo (`.github/workflows/` doesn't exist) — the entire test suite runs today with nothing beyond `python -m unittest` and the Python stdlib (FastAPI's `TestClient`/`httpx` being the one already-acknowledged, narrow exception).

Postgres has no `:memory:` equivalent. Migrating means adopting one of:
- **Docker + a real Postgres container**, locally and in any future CI — the first external service dependency this project would ever have.
- **`testcontainers-python` / `pytest-postgresql`** — ephemeral-Postgres test libraries, each with real setup/teardown cost per test run.
- **Transactional rollback per test** against one shared, persistent test database (each test runs inside a transaction that's rolled back instead of getting a fresh DB) — requires re-architecting how `apply_migrations()` and every test's `setUp()` acquire a connection.

Whichever is chosen, this touches all ~20 test files using the `:memory:` pattern and is an infrastructure decision in its own right, not a code-level find-and-replace.

---

## Effort estimate

- **Application code** (`repository.py` + `queries/*.py` + `sync/reconciler.py` + `sync/pipeline.py` + `api/dependencies.py`, plus a Postgres-dialect copy of the 8 migration files): roughly one focused engineering session, **conditional on the `sync_run_id` decision being made first** — the actual SQL is closer to Postgres-compatible than SQLite-specific quirks usually are (the upsert syntax alone being a pleasant surprise), so this is dominated by the mechanical `?`→`%s` sweep and the 6 `lastrowid`→`RETURNING` conversions, not by exotic incompatibilities.
- **Connection pooling**: a half-day to a day, well-understood pattern, new dependency + configuration.
- **Test infrastructure**: the dominant cost — likely 1-2 additional sessions depending on which of the three approaches above is chosen, plus an ongoing tax every future dev/CI run pays (a live Postgres becomes a hard requirement to run `python -m unittest` at all, which is not true today).
- **The `sync_run_id` decision**: not large in implementation once made, but should happen first — it changes the shape of two migration files and several repository functions.

**Net read:** this is a real, bounded, non-trivial follow-up project — not a one-line connection-string swap, but also not a rewrite (no ORM to introduce, no business-logic changes, and most of the raw SQL already reads as Postgres-compatible or trivially portable). The cost center is test infrastructure and one semantic landmine, not sheer SQL volume.

---

## Recommendation

Consistent with the standing decision already reflected in `DEPLOYMENT.md`: **do not migrate before tonight's deployment.** Nothing found here is a deployment blocker — SQLite on a Render persistent disk (already configured) is a reasonable choice for a single-instance, single-dealership deployment at today's scale. Revisit this migration as a scoped follow-up once real usage (concurrent writers, data volume, or a move to multi-instance hosting) actually demands it, starting with the `sync_run_id` type decision above before writing any code.
