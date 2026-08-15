# DealerDOH Development Environment

**Established:** 2026-08-15 (Infrastructure Sprint 02 — Development Environment Foundation)

The first fully isolated DealerDOH development environment: somewhere
safe to build and break DealerDOH without affecting the dealership
currently using LotSync. Everything here is disposable; nothing here
can reach production.

```
PRODUCTION (locked)                    DEVELOPMENT (this doc)
master                                 dev (branch)
LotSync v1.0.0-beta.6                  DealerDOH Development
Real dealership data                   Synthetic/disposable data only
lotsync-nu.vercel.app                  dealerdoh-dev.vercel.app
lotsync-api.onrender.com               dealerdoh-api-dev.onrender.com
SQLite on persistent disk              Supabase PostgreSQL (dealerdoh-dev)
```

**This engine split is intentional and temporary** (Sprint 03):
development validates PostgreSQL while production stays on its proven
SQLite architecture. Production migrates only in its own planned,
explicitly-approved sprint (Sprint 06 in the roadmap), after the dev
environment has proven the behavior long enough to trust.

## Components

### Frontend — Vercel project `dealerdoh-dev`

- **URL:** `https://dealerdoh-dev.vercel.app` (future: `dev.dealerdoh.com` —
  requires purchasing/configuring the `dealerdoh.com` domain, then adding
  the subdomain under this project's Domains settings)
- Separate Vercel project from production `lotsync`; same repo, root
  directory `frontend/`, framework Vite.
- **Branch mapping:** deploys from **`dev`** (switched from the
  Sprint 02 task branch on 2026-08-15 after PR #3 merged; the setting
  lives under Settings → Environments → Production → Branch Tracking).
- Env vars (names; values in the Vercel dashboard): `VITE_API_BASE_URL`
  (→ the dev API below), `VITE_ENVIRONMENT=development` (renders the
  permanent "DealerDOH DEV" banner — see `frontend/src/App.tsx`).
- Reserved for Sprint 05 (documented, unused): `VITE_SUPABASE_URL`,
  `VITE_SUPABASE_ANON_KEY` (public anon key ONLY — never service-role).

### Backend — Render web service `dealerdoh-api-dev`

- **URL:** `https://dealerdoh-api-dev.onrender.com` — `GET /health`
  returns `{"status":"ok","environment":"development"}`.
- Free instance (Oregon): no persistent disk (not needed — persistence
  now lives in PostgreSQL), spins down when idle (first request after
  idle takes ~50s — expected, not a bug).
- **Branch mapping:** auto-deploys **`dev`** (switched from the
  Sprint 02 task branch on 2026-08-15 after PR #3 merged; the setting
  lives under Settings → Build & Deploy → Branch).
- Start command is the `/tmp/pypath` symlink convention plus uvicorn
  (same as production's `render.yaml`). **As of Sprint 03 it no longer
  chains `seed_dev.py`** — the database is persistent now, so seeding
  is an explicit operator action, not a boot side effect.
- Env vars (names only): `ENVIRONMENT=development`,
  `DATABASE_ENGINE=postgres`, `DATABASE_URL` (SECRET — the Supabase
  session-pooler DSN; lives only in Render's dashboard),
  `PYTHON_VERSION`, `LOTSYNC_OUT_DIR`, `LOTSYNC_API_UPLOADS_DIR`,
  `LOTSYNC_CORS_ORIGINS` (the dev frontend origin only).

### Database — Supabase project `dealerdoh-dev` (PostgreSQL)

As of Sprint 03 the deployed dev API's persistence IS this database —
provisioned in Sprint 02, migrated and seeded in Sprint 03.

- Org: **DealerDOH** (its own Supabase organization)
- Project ref: `stpoxlfjhpcobnwfzptj`, region `us-west-2` (Oregon),
  Free plan / nano compute
- Public URL: `https://stpoxlfjhpcobnwfzptj.supabase.co`
- **Connection**: the Supabase **session pooler** (IPv4-friendly);
  direct connections are IPv6-only, which Render cannot reach. The
  exact DSN comes from the project's Connect panel and lives only in
  Render's `DATABASE_URL` env var and the owner's password manager.
- Schema: the same 8 numbered migrations as SQLite, in PostgreSQL
  dialect (`database/migrations_postgres/`), tracked in the identical
  `schema_migrations` table and auto-applied by `connect()`.
- Auth provisioned (GoTrue answers `/auth/v1/health`); no app
  integration yet — that's Sprint 05. Data API enabled;
  "auto-expose new tables" deliberately disabled — none of the app
  tables are exposed via the Data API.
- Env var names reserved for Sprint 05: `SUPABASE_URL`,
  `SUPABASE_PUBLISHABLE_KEY` (safe for browsers),
  `SUPABASE_SECRET_KEY` (server-only, never in frontend/git).

### Engine configuration (Sprint 03)

`DATABASE_ENGINE` selects the persistence engine in
`database/repository.py`'s `connect()` — the single entry point every
caller already uses:

- unset / `sqlite` (default): exactly the pre-Sprint-03 behavior.
  Production runs this and sets nothing new.
- `postgres`: connections come from `DATABASE_URL` via a small psycopg
  connection pool; `?`-placeholder SQL is translated at the connection
  boundary (`database/engine.py`); tests' `connect(":memory:")` maps
  to a private, dropped-on-close schema (the exact isolation SQLite's
  per-connection `:memory:` provides).

`GET /health` reports both `environment` and `database_engine`, so
which stack answered is always one curl away.

Local development still defaults to SQLite (zero setup, unchanged).
The full suite runs against both engines in CI — "Backend tests" and
"Backend tests (PostgreSQL)" (disposable service container, never the
live dev project). One test is engine-specific by construction and
self-skips on postgres (SQLite file-reconnect idempotency;
`tests/test_database_slice1.py`).

### Seeding and reset (Sprint 03 reality)

`seed_dev.py` is engine-aware and runs the unmodified reconciliation
pipeline over the checked-in synthetic fixtures (17 vehicles, 31
events, 3 tasks, 1 recommendation, 5 sync runs — all obviously fake:
`1TESTVIN…`, "Test Sedan", `K*` stocks):

- SQLite (local default): `python seed_dev.py --reset` — same as ever.
- PostgreSQL: with `DATABASE_ENGINE=postgres` and `DATABASE_URL` set,
  `python seed_dev.py --reset` drops the app tables and re-migrates/
  re-seeds a clean schema. Guardrails: refuses under
  `ENVIRONMENT=production`, never prints the DSN, and production has
  no PostgreSQL database for it to reach anyway.
- The deployed dev database is **no longer reseeded on boot** —
  restarts/redeploys must preserve data (that persistence is the
  Sprint 03 acceptance proof). Reset is a deliberate operator action.

Troubleshooting: `/health` failing with a 500 under postgres means the
database is unreachable (pool timeout ~15s) — check Render's
`DATABASE_URL` against the Supabase Connect panel (session pooler) and
Supabase project status; `database/engine.py` fails loudly by design
rather than silently falling back to SQLite.

## Isolation guarantees (verified 2026-08-15)

1. **Dev frontend → dev API only:** `VITE_API_BASE_URL` on the dev
   Vercel project points at `dealerdoh-api-dev.onrender.com`; the
   production API's CORS allowlist does not include the dev frontend's
   origin, so even a misconfigured build could not read production
   data from a browser.
2. **Dev API cannot touch production data:** free instance, **no disk
   attached** (the production disk `lotsync-data` is attached
   exclusively to `lotsync-api`; Render disks are single-service);
   its database is Supabase `dealerdoh-dev` PostgreSQL, which contains
   only synthetic data and which production has no connection to.
3. **No production env values in dev:** dev-only values throughout
   (verified at creation and at the Sprint 03 switch); `DATABASE_URL`
   is a dev-only credential that can reach only the dev Supabase
   project; the only shared value is `PYTHON_VERSION=3.12.0`, which
   is public in `render.yaml`. Production has no `DATABASE_ENGINE` or
   `DATABASE_URL` set at all.
4. **Supabase is dev-only:** project `dealerdoh-dev` in the DealerDOH
   org; production has no Supabase project at all yet, so no
   credential of any kind can cross environments.
5. **No deploy path to production:** production deploys ONLY on push
   to `master` (Render `lotsync-api` + Vercel `lotsync`); the dev
   services track `dev`, and neither has any configuration
   referencing `master`.
6. **Data direction:** production data was never copied, imported, or
   referenced — the dev dataset is generated from synthetic fixtures
   already in git.

## Known limitations

- Free-tier cold starts (~50s) on the dev API after idle.
- The dev database is now persistent (Supabase PostgreSQL) — it
  survives restarts and redeploys. It remains synthetic and resettable
  (`seed_dev.py --reset` with the postgres env), just no longer
  disposable-per-boot. Still: do not store anything you care about in
  dev.
- `oms_config.xlsx`-driven business config falls back to documented
  defaults on the dev API (config path not provisioned — the seed uses
  the synthetic test config at seed time only).
- No authentication yet (same as production) — the dev URLs are
  unlisted, not private.
- `dealerdoh.com` is not yet purchased/configured; dev runs on the
  `*.vercel.app` / `*.onrender.com` URLs above.
