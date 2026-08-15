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
SQLite on persistent disk              Ephemeral SQLite, reseeded per boot
(no Supabase)                          Supabase dealerdoh-dev (Postgres+Auth)
```

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
- Free instance (Oregon): **no persistent disk**, spins down when idle
  (first request after idle takes ~50s — expected, not a bug), and the
  filesystem is wiped on every deploy/restart.
- **Branch mapping:** auto-deploys **`dev`** (switched from the
  Sprint 02 task branch on 2026-08-15 after PR #3 merged; the setting
  lives under Settings → Build & Deploy → Branch).
- Start command chains `seed_dev.py` before uvicorn (same
  `/tmp/pypath` symlink convention as production's `render.yaml`), so
  every boot starts from a freshly seeded synthetic database — the dev
  database is disposable *by design*; restarting the service IS the
  reset procedure.
- Env vars (names only): `ENVIRONMENT=development`, `PYTHON_VERSION`,
  `LOTSYNC_DB_PATH` (an ephemeral `/tmp` path — NOT `/var/data`),
  `LOTSYNC_OUT_DIR`, `LOTSYNC_API_UPLOADS_DIR`, `LOTSYNC_CORS_ORIGINS`
  (the dev frontend origin only).

### Database (current) — ephemeral SQLite + synthetic seed

`seed_dev.py` runs the unmodified reconciliation pipeline over the
checked-in synthetic fixtures (`tests/fixtures/synthetic/` — the same
data the test suite uses): 17 vehicles, ~31 events, 3 tasks,
1 recommendation, 5 sync runs, all obviously fake (`1TESTVIN…`,
"Test Sedan", `K*` stock numbers). Guardrails: refuses to run when
`ENVIRONMENT=production` or when pointed at the production DB path.
Local equivalent: `python seed_dev.py --reset` then
`tools/run_dev_seed_api.py` (or the `backend-dev-seed` launch config).

### Database (future) — Supabase project `dealerdoh-dev`

Provisioned and proven reachable in Sprint 02; **the application does
not use it yet** — the SQLite → PostgreSQL migration is Sprint 03.

- Org: **DealerDOH** (its own Supabase organization)
- Project ref: `stpoxlfjhpcobnwfzptj`, region `us-west-2` (Oregon),
  Free plan / nano compute
- Public URL: `https://stpoxlfjhpcobnwfzptj.supabase.co`
- Postgres proven live via SQL (bootstrap marker table
  `public.dealerdoh_dev_bootstrap`, RLS enabled, 1 row; may be dropped
  by the Sprint 03 migration)
- Auth provisioned (GoTrue answers `/auth/v1/health`); no app
  integration yet — that's Sprint 05
- Data API: enabled; "auto-expose new tables" deliberately disabled
- Env var names for later sprints: `SUPABASE_URL`,
  `SUPABASE_PUBLISHABLE_KEY` (safe for browsers),
  `SUPABASE_SECRET_KEY` (server-only, never in frontend/git),
  `DATABASE_URL` (direct/pooler Postgres connection)
- **Sprint 03 planning note:** direct Postgres connections are
  IPv6-only by default on Supabase; connecting from Render will likely
  need the session/transaction **pooler** endpoints (or the paid IPv4
  add-on). Copy exact strings from the project's Connect panel.
- The database password is held only in the owner's password manager
  (resettable under Settings → Database); no secret values exist in
  git, and the secret API key has never left the Supabase dashboard.

## Isolation guarantees (verified 2026-08-15)

1. **Dev frontend → dev API only:** `VITE_API_BASE_URL` on the dev
   Vercel project points at `dealerdoh-api-dev.onrender.com`; the
   production API's CORS allowlist does not include the dev frontend's
   origin, so even a misconfigured build could not read production
   data from a browser.
2. **Dev API cannot touch production data:** free instance, **no disk
   attached** (the production disk `lotsync-data` is attached
   exclusively to `lotsync-api`; Render disks are single-service);
   `LOTSYNC_DB_PATH` is an ephemeral `/tmp` path.
3. **No production env values in dev:** the dev service carries only
   the six names listed above with dev-only values (verified at
   creation); the only shared value is `PYTHON_VERSION=3.12.0`, which
   is public in `render.yaml`.
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
- The dev database resets on every deploy/restart — deliberate now,
  but anything typed into dev is lost; do not use dev to store
  anything you care about.
- `oms_config.xlsx`-driven business config falls back to documented
  defaults on the dev API (config path not provisioned — the seed uses
  the synthetic test config at seed time only).
- No authentication yet (same as production) — the dev URLs are
  unlisted, not private.
- `dealerdoh.com` is not yet purchased/configured; dev runs on the
  `*.vercel.app` / `*.onrender.com` URLs above.
