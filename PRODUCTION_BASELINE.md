# LotSync — Production Baseline

**Established:** 2026-08-15 (Infrastructure Sprint 01 — Production Baseline & Git Foundation)

> ⚠️ **This environment is actively used by dealership personnel.**
> Normal development must not occur directly against production.
> Production changes go through the release train (`dev` → QA → `master`)
> or an emergency hotfix — nothing else. See "Production lock point" below.

This document records the verified state of the production LotSync
deployment at the moment the development/production split was
established. It is a snapshot, not a living dashboard — see
`PROJECT_STATUS.md` for ongoing status. Every fact below was verified
directly (repository inspection, live endpoint probes, test runs) on
the date above, not copied from older documentation; where older
documents disagree with this one, this one was correct as of its date.

Placed at the repository root, not `docs/`, per this repository's
existing convention (all documentation lives at the root).

---

## Production version

| | |
|---|---|
| **Release** | `v1.0.0-beta.6` — "Daily Work Order PDF" |
| **Git tag** | `v1.0.0-beta.6` (annotated tag `ce7cee36`, created 2026-08-07 08:27 -0700) |
| **Commit SHA** | `13c4f8153561402ef40116d9148c047a8463fe25` |
| **Commit date** | 2026-08-07 08:26:55 -0700 |
| **Branch** | `master` (repo default branch — note: `master`, not `main`) |

**How this was verified, not assumed:** local `master`, `origin/master`,
and the `v1.0.0-beta.6` tag all point at `13c4f815`; GitHub reports
nothing pushed since 2026-08-07 15:29 UTC (the beta.6 push); both
Render and Vercel auto-deploy on push to `master`; and the live backend
at the URL below exposes `GET /tasks/work-order` — the route that
exists only as of beta.6. No later tag or branch exists locally or on
the remote. The deployed production revision **is** `v1.0.0-beta.6`.

## Hosting

| | |
|---|---|
| **Frontend host** | Vercel (static Vite build; project root `frontend/`, config in `frontend/vercel.json`) |
| **Frontend URL** | `https://lotsync-nu.vercel.app` — confirmed by the product owner and verified live on 2026-08-15 (LotSync dashboard loaded with no browser console errors). |
| **Backend host** | Render — web service `lotsync-api` (per `render.yaml`; Starter plan, Oregon region, `autoDeploy: true` on `master`) |
| **Backend URL** | `https://lotsync-api.onrender.com` — verified live: `/health` returns `{"status":"ok"}` (HTTP 200) |
| **GitHub** | `https://github.com/kennett-ho/lotsync` (private, GitHub Free plan) |

## Database

| | |
|---|---|
| **Engine** | SQLite (single instance, single writer — a known, deliberate beta choice; see `SQLITE_TO_POSTGRES_ASSESSMENT.md`) |
| **Production path** | `/var/data/lotsync.db` on Render persistent disk `lotsync-data` (1 GB, mounted at `/var/data`) |
| **Path resolution** | `LOTSYNC_DB_PATH` env var, read in `database/repository.py` (`DEFAULT_DB_PATH`); defaults to repo-relative `data/lotsync.db` when unset (local dev only) |
| **Schema/migration state** | Migration `0008_event_fidelity.sql` — latest of 8 numbered migrations in `database/migrations/`, tracked in the `schema_migrations` table and auto-applied by `connect()`. Production is necessarily at 0008: the deployed beta.6 code applies pending migrations on every connection, and `/health` exercises that path. |
| **Backups** | **First verified manual backup completed 2026-08-15.** The live database was copied with SQLite's online-backup API, downloaded off Render, and independently re-verified locally. No automated backup schedule exists yet; see "Production database backup record and procedure" below. |

## Verification results (2026-08-15, local, at commit `13c4f815`)

| | |
|---|---|
| **Backend tests** | **385 / 385 passing** (`Ran 385 tests in 7.607s — OK`), via `PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"` (Python 3.12.10, repo `.venv`). Matches the count in beta.6's commit message. |
| **Frontend build** | **Passes** — `npm run build` (Vite 8.1.5, Node v22.19.0), clean output to `frontend/dist/`, exit 0. |
| **CI** | **Prepared in Infrastructure Sprint 01.5.** `.github/workflows/ci.yml` runs the backend suite and frontend production build as independent jobs on every push and pull request. The workflow has no deploy steps, secrets, or production database access. |

## Environment variables (names only — values live in each host's dashboard, never in git)

**Backend (Render, service `lotsync-api`):**
`LOTSYNC_DB_PATH`, `LOTSYNC_CONFIG_PATH`, `LOTSYNC_API_UPLOADS_DIR`,
`LOTSYNC_OUT_DIR`, `LOTSYNC_UPLOADS_DIR`, `LOTSYNC_CORS_ORIGINS`,
`PYTHON_VERSION`, `PORT` (injected by Render — never set manually).

**Frontend (Vercel):**
`VITE_API_BASE_URL` (baked into the JS bundle at build time — changing
it requires a redeploy, not just a dashboard save).

## Operational notes

- **No authentication** on any API route — accepted, deliberately
  deferred product decision; the API is effectively "unlisted, not
  private." Do not widen URL distribution until auth lands.
- **`/docs` (FastAPI interactive docs) is publicly reachable** on the
  production API.
- **CORS** rejects unlisted origins with HTTP 400 (verified live);
  only origins listed in `LOTSYNC_CORS_ORIGINS` can call the API from
  a browser.
- **`oms_config.xlsx`** business config lives at
  `/var/data/oms_config.xlsx`, uploaded manually — no in-app upload.
  Without it the app runs on documented defaults
  (`store_name='Mark Kia'`).
- The FastAPI app metadata still says `version="0.2.0"`
  (`api/app.py`) — cosmetic staleness; the app has never reported its
  real release version. Candidate cleanup for a future release, not
  worth a production deploy on its own.

---

## Production lock point

```
LotSync Production
v1.0.0-beta.6  (commit 13c4f815, tag v1.0.0-beta.6)

STATUS: STABLE / LOCKED

Normal feature development:
    DISALLOWED against production (master)

Production changes:
    Release train (dev → QA → master) or emergency hotfix only
```

- `master` is the production branch. Both Render and Vercel
  auto-deploy every push to it — **a push to `master` is a production
  deployment**, immediately, with no intermediate gate.
- **A production migration plan exists but has NOT been executed**
  (Infrastructure Sprint 06, 2026-08-16): the move to Supabase
  PostgreSQL + Auth is fully planned in
  `PRODUCTION_MIGRATION_PLAN.md` / `PRODUCTION_MIGRATION_RUNBOOK.md`,
  gated behind its own explicit approvals. Until those release trains
  run, every fact in this baseline remains the live production state.
- Day-to-day work happens on `feature/*` / `fix/*` branches merged
  into `dev` (created this sprint from exactly `13c4f815`).
- Existing tags are historical records — never moved, never reused.
- No branch protection is currently *possible* on this repo (private
  repo on GitHub Free — protection requires GitHub Pro or a public
  repo), so this lock is **procedural, not enforced**. See
  "Branch protection" below.

## Branch protection (recommended, not yet enforceable)

GitHub's API confirms branch protection is unavailable on this
private Free-plan repository ("Upgrade to GitHub Pro or make this
repository public to enable this feature"). Options, in order of
preference:

1. **Upgrade the owning account to GitHub Pro** (small monthly cost) —
   then apply the settings below to `master`.
2. Keep the Free plan and rely on the procedural lock above (current
   state). Workable for a single-developer repo, but nothing stops an
   accidental `git push origin master`.

Recommended settings for `master` once available:

- Require a pull request before merging (release train from `dev`).
- Block force pushes; block branch deletion.
- Require the `Backend tests` and `Frontend production build` CI checks
  once branch protection becomes available.
- Do **not** enable "require review approvals ≥ 1" while this is a
  single-maintainer repository — with no second reviewer it locks the
  owner out of their own release train (GitHub does not let the PR
  author approve their own PR).

## Production database backup record and procedure

The first backup was completed on 2026-08-15 through Render's dashboard
shell and SSH. This is a **live** SQLite database — never copy the raw
file while the service is running; use SQLite's online-backup mechanism,
which is safe against concurrent writes:

**Step 1 — in the Render dashboard → `lotsync-api` → Shell tab:**

```bash
mkdir -p /var/data/backups
python3 - <<'EOF'
import sqlite3, hashlib, os
src = sqlite3.connect("/var/data/lotsync.db")
dst = sqlite3.connect("/var/data/backups/lotsync-2026-08-15.db")
src.backup(dst)          # SQLite online backup -- safe on a live DB
dst.close(); src.close()
chk = sqlite3.connect("/var/data/backups/lotsync-2026-08-15.db")
print("integrity_check:", chk.execute("PRAGMA integrity_check").fetchone()[0])
print("migrations:", chk.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0])
print("vehicles:", chk.execute("SELECT COUNT(*) FROM vehicle").fetchone()[0])
chk.close()
h = hashlib.sha256()
with open("/var/data/backups/lotsync-2026-08-15.db", "rb") as f:
    for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
print("sha256:", h.hexdigest())
print("size_bytes:", os.path.getsize("/var/data/backups/lotsync-2026-08-15.db"))
EOF
```

Expect `integrity_check: ok`. Record the printed sha256, size, and row
counts in the table below.

**Step 2 — get the backup OFF the Render disk.** A copy sitting next
to the production DB on the same disk is not disaster recovery. The
Starter plan supports SSH — from your own machine (after adding an SSH
key under Render → Account Settings → SSH Public Keys; the exact
`srv-…` service address is on the service's Connect panel):

```bash
scp <SERVICE-SSH-ADDRESS>:/var/data/backups/lotsync-2026-08-15.db "C:/Users/demon/LotSync-Backups/"
```

**Step 3 — verify the downloaded copy locally** (same integrity check
and sha256 as Step 1; the hash must match) and store it somewhere that
survives loss of both the laptop and the Render disk (e.g. cloud
drive).

**Never commit any database file to git** (already enforced by
`.gitignore`'s `*.db` rule).

| Backup record | |
|---|---|
| Taken at | `2026-08-15T07:33:14.549079+00:00` |
| Schema / row count | Migration `8`; `4,672` vehicles |
| Size | `4,210,688` bytes (`4.02 MiB`) |
| `PRAGMA integrity_check` | `ok` on Render and on the downloaded copy |
| SHA-256 | `7111f1176d420b984a3e7fdcd0d217e15897e4c0b951204ea5e4f5fedc7f226c` (identical on Render and locally) |
| Stored at | Render: `/var/data/backups/lotsync-2026-08-15.db`; local off-Render copy: `C:\Users\demon\LotSync-Backups\lotsync-2026-08-15.db`; independent cloud copy pending explicit approval |

---

## Discrepancies found while establishing this baseline

Recorded here so they are decisions, not surprises:

1. **`master` vs `main`** — the production branch is `master`; the
   long-term workflow docs assume `main`. Renaming is deliberately NOT
   done this sprint: Render (`render.yaml: branch: master`) and Vercel
   both track `master`, so a rename is a production-affecting change
   that belongs in a planned release-train step, if it happens at all.
2. **`CHANGELOG.md` ends at v0.7.4** — releases v0.8.0 through
   v1.0.0-beta.6 (8 tags) have no changelog entries; the git tag
   messages are currently the only release record for them.
3. **`PROJECT_STATUS.md` was last updated at v0.7.4** (2026-08-03) —
   updated this sprint to point here.
4. **Stale test counts in older docs** — `PROJECT_STATUS.md` says 328,
   `DEPLOYMENT.md` says 360; actual (verified) is **385**. Each was
   correct when written; this file's count is the baseline.
5. **Production frontend URL was not recorded anywhere in the repo** —
   the product owner confirmed `https://lotsync-nu.vercel.app` on
   2026-08-15; it is now recorded under Hosting above.
6. **CI was absent at baseline; branch protection is still unavailable
   on the current GitHub plan** — Infrastructure Sprint 01.5 adds the
   CI workflow, but the production lock remains procedural.
