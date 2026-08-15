# Deploying LotSync

> ⚠️ **Production is live and locked (2026-08-15).** This deployment is
> actively used by dealership personnel. Every push to `master`
> auto-deploys to production on both Render and Vercel — so pushing to
> `master` **is** deploying. Normal work goes to `feature/*`/`fix/*` →
> `dev`; production changes arrive via the release train or an
> emergency hotfix only. See [`PRODUCTION_BASELINE.md`](PRODUCTION_BASELINE.md)
> for the verified production baseline and lock rules.

Target stack: **Vercel** (frontend, static Vite build) + **Render** (backend, FastAPI/uvicorn + SQLite on a persistent disk). Database strategy for this first deployment is unchanged (SQLite) — see `SQLITE_TO_POSTGRES_ASSESSMENT.md` for the scoped follow-up plan if/when Postgres becomes worth the cost.

This document is the primary, step-by-step reference. `render.yaml` at the repo root is an optional convenience for a one-click Render "Blueprint" deploy — if its exact syntax ever drifts from what Render's Blueprint parser currently expects, follow the manual dashboard steps below instead; they don't depend on that file at all.

---

## Required accounts

- **GitHub** — this repo already lives at `https://github.com/kennett-ho/lotsync` (existing `origin` remote). No new account needed, just confirm you can push to it (already working — see recent `v0.8.1`/`v0.8.2` pushes).
- **Render** (https://render.com) — for the backend. Sign up/sign in with GitHub for the simplest repo-connection flow.
- **Vercel** (https://vercel.com) — for the frontend. Same recommendation: sign in with GitHub.

No other external accounts or API keys are required — `PRE_DEPLOYMENT_REVIEW.md` confirmed no secrets/credentials exist anywhere in this codebase.

---

## Required environment variables

### Backend (Render) — set under the service's **Environment** tab

| Variable | Value for this deployment | Why |
|---|---|---|
| `LOTSYNC_DB_PATH` | `/var/data/lotsync.db` | SQLite file, on the persistent disk (see below) so it survives deploys/restarts. |
| `LOTSYNC_CONFIG_PATH` | `/var/data/oms_config.xlsx` | Business config (store name, aging buckets, excluded VINs). **You must upload this file yourself after deployment** — see Post-Deployment Verification. Until you do, the app runs on documented defaults (`store_name='Mark Kia'`) — not broken, just not your real dealership's numbers. |
| `LOTSYNC_API_UPLOADS_DIR` | `/var/data/api_uploads` | Where Inventory Sync stages uploaded CSVs per run. |
| `LOTSYNC_OUT_DIR` | `/var/data/outputs` | Where the 8 CSV reports are written after each sync. |
| `LOTSYNC_UPLOADS_DIR` | `/var/data/uploads` | CLI-only path, unused by the web API. Harmless to set for consistency. |
| `LOTSYNC_CORS_ORIGINS` | *(set after Vercel deploy — see Deployment Order)* | Comma-separated list of allowed browser origins. Until set to the real Vercel URL, no browser can call the API — this is a safe default, not a bug. |
| `PYTHON_VERSION` | `3.12.0` | Pins the Python runtime. |
| `PORT` | *(do not set — Render injects this automatically)* | The start command reads it via `$PORT`. |

### Frontend (Vercel) — set under the project's **Settings → Environment Variables**

| Variable | Value for this deployment | Why |
|---|---|---|
| `VITE_API_BASE_URL` | *(set after Render deploy — see Deployment Order)* | The Render backend's public URL, e.g. `https://lotsync-api.onrender.com`. **Baked into the JS bundle at build time** — changing this later requires a redeploy, not just a dashboard save. |

Both `.env.example` (repo root) and `frontend/.env.example` document the same variables for local development, with local-appropriate defaults.

---

## Deployment order (matters — read before starting)

Backend and frontend each need to know the other's URL, but neither URL exists until that side is deployed once. Break the chicken-and-egg problem in this order:

1. **Deploy the backend to Render first**, with `LOTSYNC_CORS_ORIGINS` set to a harmless placeholder (already the case in `render.yaml`). It will come up fine — CORS only affects browser calls, not the deploy itself.
2. **Note the Render URL** (e.g. `https://lotsync-api.onrender.com`).
3. **Deploy the frontend to Vercel**, setting `VITE_API_BASE_URL` to that Render URL.
4. **Note the Vercel URL** (e.g. `https://lotsync.vercel.app`).
5. **Go back to Render** and update `LOTSYNC_CORS_ORIGINS` to the real Vercel URL, then trigger a restart (env var changes on Render restart the service automatically; no rebuild needed since this isn't baked into anything at build time).

---

## Deployment steps

### Part A — Backend on Render

> **STOP — this part requires your direct interaction with Render's dashboard.** I cannot create accounts, click buttons in an external dashboard, or enter billing details on your behalf. Everything below is exactly what to do; tell me the results (URLs, any error messages) as you go and I'll keep helping from there.

1. Go to https://dashboard.render.com and sign in (GitHub sign-in recommended).
2. Click **New +** → **Web Service**.
3. Connect your GitHub account if prompted, then select the `kennett-ho/lotsync` repository.
4. Configure the service:
   - **Name**: `lotsync-api` (or anything you prefer — you'll use whatever URL Render assigns)
   - **Region**: your choice (Oregon is `render.yaml`'s default; pick whatever's closest to you)
   - **Branch**: `master`
   - **Root Directory**: leave blank (the backend lives at the repo root)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**:
     ```
     mkdir -p /tmp/pypath && ln -sfn "$PWD" /tmp/pypath/lotsync && PYTHONPATH=/tmp/pypath uvicorn lotsync.api.app:app --host 0.0.0.0 --port $PORT
     ```
     (See `render.yaml`'s comments for why this isn't a plain `uvicorn lotsync.api.app:app` — the short version: every backend module imports as `from lotsync.x import y`, which needs a directory literally named `lotsync` on the Python path, and Render's checkout directory isn't named that. This one-liner recreates it via a symlink without touching any application code. Verified locally against a simulated mismatched-directory-name checkout before being written here.)
   - **Instance Type**: **Starter** (or higher) — **not Free**. The Free tier has no persistent disk, so the SQLite database and your uploaded `oms_config.xlsx` would be wiped on every deploy and every restart. If you're only doing a short-lived demo and don't care about data surviving a restart, Free works — just know that's the tradeoff.
5. Under **Advanced** (or after initial creation, under the service's **Disks** tab):
   - Add a disk: **Name**: `lotsync-data`, **Mount Path**: `/var/data`, **Size**: 1 GB (plenty of headroom for this app's data volume).
6. Set the environment variables from the table above (`LOTSYNC_DB_PATH`, `LOTSYNC_CONFIG_PATH`, `LOTSYNC_API_UPLOADS_DIR`, `LOTSYNC_OUT_DIR`, `LOTSYNC_UPLOADS_DIR`, `LOTSYNC_CORS_ORIGINS` as a placeholder for now, `PYTHON_VERSION`).
7. Set **Health Check Path**: `/health`.
8. Click **Create Web Service**. Render will build and deploy — first deploy typically takes a few minutes.
9. Once live, note the URL Render assigns (shown at the top of the service dashboard, format `https://<name>.onrender.com`).

*(Alternative: if you'd rather not click through each field, use **New +** → **Blueprint**, point it at this repo, and Render will read `render.yaml` and propose the same configuration for you to confirm. Same STOP applies — you still need to click through Render's confirmation UI yourself.)*

### Part B — Frontend on Vercel

> **STOP — this part requires your direct interaction with Vercel's dashboard**, for the same reason as Part A.

1. Go to https://vercel.com/new and sign in (GitHub sign-in recommended).
2. Import the `kennett-ho/lotsync` repository.
3. When configuring the project:
   - **Root Directory**: click "Edit" and set it to `frontend` — this is the one setting that can't be expressed in `frontend/vercel.json` itself; it must be set here, in the dashboard, at import time.
   - Vercel should auto-detect **Framework Preset: Vite** once the root directory is set (matches `frontend/vercel.json`).
4. Under **Environment Variables**, add `VITE_API_BASE_URL` = the Render URL from Part A, step 9 (e.g. `https://lotsync-api.onrender.com`) — no trailing slash.
5. Click **Deploy**.
6. Once live, note the URL Vercel assigns (format `https://<project>.vercel.app`, or a project-specific variant).

### Part C — Close the loop

> **STOP — back to Render's dashboard for one more setting.**

1. In Render, open `lotsync-api`'s **Environment** tab.
2. Update `LOTSYNC_CORS_ORIGINS` to the exact Vercel URL from Part B, step 6 (e.g. `https://lotsync.vercel.app`). If you expect multiple frontend URLs (e.g. Vercel's preview-deployment URLs too), comma-separate them.
3. Save — Render restarts the service automatically on an env var change (no rebuild needed).

At this point LotSync is live at your Vercel URL, talking to your Render backend.

---

## Verify (what was already confirmed locally, before any of the above)

These were run and passed during deployment prep, ahead of asking for your involvement:

- ✅ `npm run build` in `frontend/` succeeds cleanly (confirmed twice, including with `VITE_API_BASE_URL` set — verified the value is correctly baked into the built JS).
- ✅ The backend starts correctly under a simulated Render environment (a checkout directory *not* named `lotsync`, exercising the exact symlink trick in `render.yaml`'s start command) — confirmed via a real running process, not just a read-through.
- ✅ `GET /health` returns `{"status": "ok"}` (200).
- ✅ Real API routes respond correctly (`GET /vehicles`, `GET /dashboard` both 200).
- ✅ `GET /docs` (FastAPI's interactive docs) responds (200) — see the note under Known Limitations below about what this means once this is publicly reachable.
- ✅ CORS correctly allows a configured origin and rejects (400) an unlisted one, end to end against a running server.
- ✅ The SQLite database file is created at exactly the path given by `LOTSYNC_DB_PATH`, confirming env-var-driven paths (and therefore the Render persistent-disk plan) work as intended.
- ✅ Full backend test suite: 360/360 passing.

What can only be verified after Parts A–C above (since it requires the real deployed URLs):

- [ ] Vercel frontend loads and successfully calls the Render backend (no CORS error in the browser console).
- [ ] `GET https://<your-render-url>/health` returns 200 from the public internet.
- [ ] Inventory Sync's upload flow works end-to-end against the deployed backend with a real or synthetic CSV.
- [ ] The persistent disk actually persists: trigger a manual redeploy on Render and confirm previously-synced data is still present afterward (not reset).

---

## Post-deployment verification checklist

Run through this after Part C:

1. Open the Vercel URL in a browser. Dashboard should load without a "backend unreachable" error.
2. Open browser DevTools → Network tab, confirm requests to the Render URL return `200`, not CORS errors.
3. Curl the health endpoint directly: `curl https://<your-render-url>/health` → expect `{"status":"ok"}`.
4. Upload your real `oms_config.xlsx` to the persistent disk at `/var/data/oms_config.xlsx`. Render doesn't currently expose a file-upload UI for this — the practical options are: (a) Render's **Shell** tab (under the service dashboard) to `curl`/`scp` it in, or (b) temporarily add a one-off authenticated upload route (not currently part of this app — treat as a manual, one-time operational step, not something to build for this deployment). Until this file is in place, the app runs correctly on its documented defaults (`store_name='Mark Kia'`) — confirm that's acceptable for your first live session, or complete this step before relying on real output.
5. Run one real (or synthetic) Inventory Sync from the deployed frontend. Confirm `GET /inventory-sync/history` shows the new run.
6. Redeploy the backend once (Render's "Manual Deploy" button) and confirm the data from step 5 is still present afterward — this is the actual proof the persistent disk is doing its job.

---

## A risk worth naming out loud before you share this URL

`PRE_DEPLOYMENT_REVIEW.md`'s S3 finding (no authentication anywhere in the API) was accepted as reasonable *for a localhost-only deployment*. Tonight's deployment changes that calculus: `POST /inventory-sync/run` (a write endpoint) and every read endpoint will be reachable by anyone who finds the Render URL, with zero login. This wasn't in scope to fix tonight (per your explicit "no new features," and authentication has been a deliberately deferred product decision throughout this project's history), but it's now a live consideration, not a hypothetical one. Two low-effort mitigations that don't require adding an auth feature to the app itself:
- Render supports IP allowlisting on paid plans (dashboard setting, no code change) — worth enabling if only your team needs access.
- Don't share the Render/Vercel URLs beyond who needs them, and treat both as effectively unlisted, not private, until real authentication is prioritized.

---

## Rollback instructions

**Backend (Render):**
1. Open the `lotsync-api` service → **Events** (or **Deploys**) tab.
2. Find the last known-good deploy in the list.
3. Click **Rollback to this deploy** (or **Redeploy** on that specific commit, depending on Render's current UI wording).
4. The persistent disk is *not* affected by a rollback — your data isn't touched, only the running code changes.

**Frontend (Vercel):**
1. Open the project → **Deployments** tab.
2. Find the last known-good deployment.
3. Click the "..." menu → **Promote to Production** (Vercel keeps every deployment addressable; this instantly repoints the production URL, no rebuild needed).

**Git-level rollback (either side):** every deploy corresponds to a real commit on `master` (tagged `v0.8.x` per this project's convention). `git revert` the offending commit and push — both Render (`autoDeploy: true`) and Vercel redeploy automatically on a push to `master`, so this achieves the same result as the dashboard rollback, just via git instead.

**Database:** if a bad deploy also wrote bad data (not just bad code), the code rollback above does *not* undo data changes — there is currently no automated backup of the Render persistent disk (see `PRE_DEPLOYMENT_REVIEW.md`'s P5 finding, noted there and here, not implemented). Manually download `data/lotsync.db` via Render's Shell tab before any risky operation if you want a restore point.

---

## Known limitations of this first deployment

- **SQLite, not Postgres** — a deliberate choice for this first deployment (see `SQLITE_TO_POSTGRES_ASSESSMENT.md`). Fine for a single instance at today's scale; revisit if this ever needs to scale beyond one Render instance or handle meaningfully concurrent writers.
- **No authentication** — see the callout above. A known, pre-existing, deliberately-deferred product decision, now live on a public URL instead of localhost.
- **`/docs` is publicly reachable** — FastAPI's interactive API docs are enabled by default (`PRE_DEPLOYMENT_REVIEW.md`'s S4). Combined with the no-auth point above, anyone who finds the URL can browse the full API schema and try requests directly. Not fixed here (out of scope — no business-logic or app-behavior changes tonight), but worth knowing before you promote this from "quiet demo URL" to something more widely shared.
- **No automated backups** of the persistent disk — see Rollback instructions above.
- **`oms_config.xlsx` must be uploaded manually** post-deploy — there's no in-app upload UI for it (it's a business-config file read directly from disk, by design — see `README.md`'s Configuration section).
