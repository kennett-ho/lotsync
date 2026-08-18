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
  the owned `dealerdoh.com` domain is not configured yet; add the
  subdomain under this project's Domains settings when approved)
- Separate Vercel project from production `lotsync`; same repo, root
  directory `frontend/`, framework Vite.
- **Branch mapping:** deploys from **`dev`** (switched from the
  Sprint 02 task branch on 2026-08-15 after PR #3 merged; the setting
  lives under Settings → Environments → Production → Branch Tracking).
- Env vars (names; values in the Vercel dashboard): `VITE_API_BASE_URL`
  (→ the dev API below), Sprint 11 observability (browser-public
  identifiers, pending owner setup — see `OBSERVABILITY.md` §9):
  `VITE_SENTRY_DSN`, `VITE_POSTHOG_KEY`, `VITE_POSTHOG_HOST`; the
  backend side adds `SENTRY_DSN` on the Render service. All bake at
  build time on Vercel (redeploy after changing). No production
  project sets any of these. `VITE_ENVIRONMENT=development` (renders the
  permanent "DealerDOH DEV" banner — see `frontend/src/App.tsx`),
  and — Sprint 05 — `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY`
  (public anon key ONLY, never service-role), which activate the
  login gate (`frontend/src/auth/`). Production's Vercel project sets
  neither, so its bundle stays gate-free and unchanged.

### Backend — Render web service `dealerdoh-api-dev`

- **URL:** `https://dealerdoh-api-dev.onrender.com` — `GET /health`
  returns `{"status":"ok","environment":"development"}`.
- Free instance (Oregon): no persistent disk (not needed — persistence
  now lives in PostgreSQL), spins down when idle (first request after
  idle takes ~50s — expected, not a bug).
- **Branch mapping:** auto-deploys **`dev`**. During a sprint's
  pre-merge review window the service may temporarily track that
  sprint's task branch so the deployed dev environment can be smoke
  -tested before merge approval (done for Sprints 02 and 03), and
  returns to `dev` when the sprint's PR merges. The setting lives
  under Settings → Build & Deploy → Branch.
- Start command is the `/tmp/pypath` symlink convention plus uvicorn
  (same as production's `render.yaml`). **As of Sprint 03 it no longer
  chains `seed_dev.py`** — the database is persistent now, so seeding
  is an explicit operator action, not a boot side effect.
- Env vars (names only): `ENVIRONMENT=development`,
  `DATABASE_ENGINE=postgres`, `DATABASE_URL` (SECRET — the Supabase
  session-pooler DSN; lives only in Render's dashboard),
  `PYTHON_VERSION`, `LOTSYNC_OUT_DIR`, `LOTSYNC_API_UPLOADS_DIR`,
  `LOTSYNC_CORS_ORIGINS` (the dev frontend origin only), and —
  Sprint 05 — `AUTH_MODE=required` + `SUPABASE_URL` (public project
  URL; token verification fetches the public JWKS from it) +
  optionally `DEALERDOH_DEALERSHIP_ID` (defaults to `qa-motors`); and
  — Sprint 09 — `SUPABASE_SECRET_KEY` (SECRET: the service-role key
  the user-administration endpoints use against the GoTrue Admin API;
  server-side only, staged by the operator; without it `/users`
  answers 503 and everything else works) + `DEALERDOH_FRONTEND_URL`
  (invite-email redirect base — the dev frontend origin). Supabase
  Auth config must allowlist
  `https://dealerdoh-dev.vercel.app/auth/reset-password` as a
  redirect URL (Sprint 09 recovery/invite landing). See
  `ACCOUNT_LIFECYCLE.md`.
  Production sets none of the Sprint 05 variables: `AUTH_MODE`
  defaults to `disabled`, which is byte-for-byte pre-Sprint-05
  behavior — see `AUTH_ARCHITECTURE.md`.

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
- **Auth integrated (Sprint 05):** email/password sign-in through
  Supabase Auth (email provider only; public signups disabled), ES256
  JWTs verified server-side by FastAPI, access authorized by the
  `user_membership` access model. Synthetic dev users only
  (`*@qa.dealerdoh.example` — see `DEV_QA_GUIDE.md`); RLS deliberately
  deferred with documented conditions. Full design:
  `AUTH_ARCHITECTURE.md`. Data API still exposes no app tables.
- `SUPABASE_SECRET_KEY` (service-role) is used ONLY by the operator
  provisioning script (`tools/provision_dev_auth.py`) — never by the
  deployed API, never in the frontend, never in git or CI.

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

### Seeding and reset (Sprint 04 reality: the standing QA dealership)

`seed_dev.py` is engine-aware and seeds the **standing QA dealership**
(`dev_seed/`, Sprint 04): 34 synthetic vehicles replayed as two
deterministic sync days through the real pipeline path
(`sync/pipeline.run_inventory_sync`), producing 98 events, 18 tasks
(16 open, 1 honored, 1 moot), 2 recommendations, 3 pending identities,
and 10 sync runs — every vehicle exercising a specific implemented
rule, all obviously fake (`1QATEST…` VINs, `QA*` stocks). The scenario
roster and expected outcomes live in `SYNTHETIC_QA_MATRIX.md` (human
form) and `dev_seed/expected.py` (asserted form —
`tests/test_qa_dataset.py` enforces it on both engines in CI). The
operator walkthrough is `DEV_QA_GUIDE.md`:

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
  defaults on the dev API (config path not provisioned). The QA seed
  reads the same canonical defaults directly from `rules/aging.py` —
  one source of truth for the deployed API and the seed alike.
- Authentication is live in dev as of Sprint 05 (`AUTH_MODE=required`,
  synthetic users only — see `AUTH_ARCHITECTURE.md`). Production
  remains unauthenticated until its own planned migration
  (`PRODUCTION_MIGRATION_PLAN.md`). This bullet previously said "no
  authentication yet" — stale since Sprint 05, corrected in Sprint 06.
- `dealerdoh.com` is owned but not yet configured; dev runs on the
  `*.vercel.app` / `*.onrender.com` URLs above.
