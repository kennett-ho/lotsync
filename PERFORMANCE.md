# DealerDOH Performance & Resilience (Sprint 14 — Rail J)

**Status: canonical.** How DealerDOH stays responsive at the
dealership's real shape — 4,700+ vehicle historical datasets, growing
event/sync history, a handful of concurrent staff, phones on the lot,
Render/Supabase latencies — and the regression guards that keep it
that way. Established by Sprint 14; amend in the same PR as any
behavior change it describes. Rail contract:
`V1_1_RELEASE_READINESS.md` §5.J.

Philosophy (the sprint's own): **measure first, fix second,
re-measure.** No fix below shipped without a number that justified it,
and no number below is an SLA — they are recorded evidence and
regression alarms for realistic dealership usage, not marketing
promises or hyperscale goals.

---

## 1. The measured shape of the product

All local numbers: SQLite engine, uvicorn on 127.0.0.1, warm process,
15-run median/p95, desktop-class machine, Sprint 14 branch from `dev`
= `73dee99`. Datasets: the standing 34-vehicle QA dealership, and the
Sprint 07 rehearsal generator's production-shaped dataset (4,700
vehicles → 1,197 active + 3,503 sold, 365 tasks, schema v10 — the
same generator the migration rehearsal trusts).

### Backend warm latency + payload (after Sprint 14 fixes)

| Endpoint | QA scale | Production shape | Payload at prod shape (raw / gzip) |
|---|---|---|---|
| `/health` | 3.0 ms | 2.9 ms | 123 B |
| `/me` | 3.0 ms | 3.2 ms | 46 B |
| `/dashboard` | 3.7 ms | 4.4 ms | 9.8 kB / 1.5 kB |
| `/vehicles` (active) | 4.0 ms | 45.9 ms (1,197 rows) | 370 kB / 12.5 kB |
| `/vehicles?include_sold=true` | 4.7 ms | 159.4 ms (4,700 rows) | 1.43 MB / 47 kB |
| `/vehicles/{vin}` | 4.1 ms | 4.5 ms | ~2–3 kB / ~1 kB |
| `/tasks` | 3.5 ms | 8.1 ms (365 rows) | 190 kB / 11.7 kB |
| `/recommendations` | 3.3 ms | 3.3 ms | ~1 kB |
| `/inventory-sync/history` | 3.3 ms | 3.5 ms | ~2–5 kB |
| `/inventory-sync/exceptions` | 3.0 ms | 3.2 ms | ~0.5 kB |
| `/tasks/work-order` (PDF) | 17.6 ms | 66.6 ms | 5.3 kB / 11.3 kB PDF |

Deployed DEV (Supabase PostgreSQL via pooler, Render, browser in
another region): warm authenticated requests measured 110–360 ms
round-trip — network/TLS/pooler dominated; server-side time is the
milliseconds above. Re-measured in the feature-branch review window
(authenticated landing, fresh tab): `/me` 149 ms · `/dashboard`
213 ms · `/tasks` 114 ms; initial-JS wire transfer 173.9 kB
compressed (entry 117.5 + supabase 56.4 — Vercel-served encoding);
exactly ONE `/dashboard` request on the real landing; the PostHog
chunk arrived deferred with explicit events flowing; zero console/CSP
violations with the lazy chunk graph live.

### Ingestion validation benchmark (Sprint 10 continuity)

`validate_report_set`, 4,700-row Tekion export, current tree:
**0.033 s** (historical Sprint 10 reference ≈ 0.04 s). The Sprint 11
observability and Sprint 13 security layers added no measurable cost.
Regression tripwire: `tests/test_ingestion_validation.py::
PerformanceSanityTest` (loose 10 s bound; prints the real number).

### Work-order PDF

17.6 ms / 5.3 kB at the QA workload (16 tasks); 66.6 ms / 11.3 kB at
the production-shaped 365-task outstanding set. ReportLab holds the
whole document in memory; at these sizes that is nothing. No bound
recorded beyond the CI sanity of the endpoint tests — revisit only if
outstanding-task volume changes class.

---

## 2. What Sprint 14 fixed, with the evidence that justified it

### 2.1 Unbounded `sync_run` reads on hot paths (backend)

`connected_systems_status()` (called by `/dashboard` AND every
`/vehicles/{vin}`) and `sync_run_history()` read **every** sync_run
row per call and reduced in Python. With +5,000 synthetic rows (≈
years of Sprint 17 automated acquisition at 5 sources): `/dashboard`
4.4 → 10.5 ms, vehicle detail 4.5 → 10.7 ms, history 3.5 → 13.4 ms —
linear, unbounded, and amplified over a network pooler where row
transfer dominates.

**Fix:** aggregate in SQL (latest-run-per-source; newest-N-batches).
Re-measured at 5,012 rows: 4.7 / 4.9 / 6.1 ms — the growth path is
gone. Semantics byte-identical (key order, batch order, worst-status
rules) and pinned by `tests/test_queries_sync_scale.py`. No schema
change, no migration; the PK + `idx_sync_run_source` suffice.

### 2.2 Duplicate `/dashboard` fetch on every landing (frontend)

Live on deployed DEV: the manager landing issued `/dashboard` twice
(161 ms + 362 ms over the pooler) because the header and the landing
surface each ran their own `useApi(getDashboard)`; the lot-staff
landing did the same. The header additionally fetched only once per
session, so its "Synced N ago" badge went stale.

**Fix:** one provider (`frontend/src/api/dashboardData.tsx`) with
in-flight dedup; surfaces keep their fetch-per-visit freshness via
`refreshOnMount`, the header consumes passively and now updates on
every surface refresh. One request per view, verified live. This is
in-memory request sharing within a page view — nothing is cached
across views or persisted (the API stays `Cache-Control: no-store`
per `SECURITY_ARCHITECTURE.md`; no HTTP caching was added anywhere).

### 2.3 The bundle (frontend initial load)

Sprint 13 baseline: **one 885.1 kB chunk (256.1 kB gzip)**.
Sourcemap attribution: posthog-js 234.6 kB (27.2% — the single
largest contributor), react-dom 174.4 kB, @supabase/* ≈ 197.6 kB
(≈ 93.6 kB of it realtime/storage/postgrest/functions sub-clients the
app never uses), @sentry/* ≈ 82.9 kB, app code 155.8 kB (18%).

**Fixes** (in `frontend/src`):
- **PostHog deferred** via dynamic `import()` — telemetry is
  secondary by doctrine (`OBSERVABILITY.md`) and must not sit on the
  critical path. The wrapper API is unchanged and synchronous;
  pre-ready calls queue in order (identify → its events; reset still
  severs identity). Builds without `VITE_POSTHOG_KEY` — including
  current production — never fetch the chunk at all. Sentry stays
  synchronous **deliberately**: deferring it would lose early-error
  capture, the one thing it exists for.
- **Route-level chunks** for the role-gated / rarely-first surfaces
  (Inventory Sync, Profile + User Management, Help, Onboarding,
  Login, ResetPassword). Landing surfaces (Overview, Today's Work,
  Vehicles, Tasks, Vehicle Detail) deliberately stay in the initial
  bundle so first use never waits on a second fetch.

**Result:**

| | raw | gzip |
|---|---|---|
| Sprint 13 initial JS | 885.1 kB | 256.1 kB |
| Sprint 14 initial JS (entry + supabase chunk) | 592.5 kB | **167.2 kB (−35%)** |
| PostHog chunk (post-paint, only when configured) | 240.0 kB | 79.5 kB |
| Role-gated surface chunks (on nav) | 4.8–27.1 kB each | 1.6–6.4 kB each |
| CSS | 61.5 kB | 11.3 kB |

**Deliberately not done:** slimming `@supabase/supabase-js` to the
auth-only client (≈ 94 kB raw / ~25 kB gzip further) — it rewires the
verified Rail A auth stack for a modest gain; recorded in §6 as a
future candidate, not silently absorbed. Sentry/PostHog were **not
removed** (hard sprint boundary).

### 2.4 DOM rendering at production scale (frontend)

The payload was never the problem (12.5 kB gzip active / 47 kB Sold —
Render's proxy brotli-compresses responses; verified live). The DOM
was: rendering all 1,197 active rows measured **755 ms** to paint
with a 417 ms main-thread block; every search keystroke that widened
the result set re-blocked **400–850 ms** (a phone-class CPU is 3–6×
worse); Sold mode rendered 3,503 rows / **131,460 DOM nodes** with a
939 ms block. A 602-event vehicle timeline measured **1.4 s** / 976 ms
block.

**Fix:** bounded rendering with explicit, truthful escape hatches —
Vehicles paints the first 100 matches of the current sort plus
"Showing the first 100 of N — Show all N"; the timeline paints the
newest 150 events plus "Show older history (N more)". Search, filter
chips, counts, and sort always operate on the **complete** dataset —
nothing is hidden silently, and at the standing QA scale (≤ 34 rows)
rendering is pixel-identical. Re-measured: 27–74 ms per keystroke at
production scale. A review-window measurement of the PRODUCTION build
then caught the expansion reset landing one frame late (first
keystroke after "Show all" re-rendered the full roster once — a
1.4 s block — and returning to the expanded query surprise-
re-expanded); the expansion is now derived state keyed to the result
set it was requested for, so every render after any query change is
bounded, including the first (measured 171 ms, then 42 ms). Virtualization (a new dependency) and server-side
pagination were both rejected as larger tools than the evidence
demands; §6 records the reopening conditions.

### 2.5 Slow-network resilience

Every `fetch` in the API client now carries a 30 s timeout
(`AbortSignal.timeout`): a dead network fails into the existing
comprehensible "API unreachable" error path instead of an eternal
spinner. 30 s is generous headroom over every measured operation.
All mutation paths already had pending-state disable + double-submit
guards (validate, run sync, invite, de/reactivate, display-name save,
recovery email, work order, sign-in/forgot/reset — verified in the
audit) and keep them; the Sprint 12 onboarding rapid-click clamp
survives with a test pin.

---

## 3. Cold start vs application latency (the distinction)

Measured this sprint on DEV (Render free tier): first request after
idle sleep = **32.3 s**; the same endpoint immediately after:
0.21–0.27 s round-trip, ~3 ms server-side. The 32 s is the platform
waking the service, not DealerDOH code — application startup itself
is a normal uvicorn boot. **Do not optimize application code against
free-tier sleep.** Mitigation is a hosting-tier decision at
commercial readiness; the frontend's loading states (Rail B) are the
UX treatment meanwhile. Production (paid tier questions, real
traffic) is measured at its own release train.

Also verified while measuring: Render's proxy applies Brotli
compression to API responses (`Content-Encoding: br` observed), so no
in-app compression middleware is warranted.

---

## 4. Budgets (regression alarms, not promises)

| Budget | Ceiling | Measured (Sprint 14) | Enforced by |
|---|---|---|---|
| Initial-load JS (gzip) | 200 kB | 161.8 kB | `tools/check_bundle_budget.py` — CI gate in the frontend job |
| Total JS all chunks (gzip) | 320 kB | 255.9 kB | same |
| CSS (gzip) | 25 kB | 11.0 kB | same |
| 4,700-row validation | < 10 s (tripwire; prints real value ≈ 0.03 s) | 0.033 s | `PerformanceSanityTest` |
| Rendered rows per list paint | 100 (+ explicit Show all) | — | `tests/test_frontend_performance.py` |
| Timeline events per paint | 150 (+ explicit Show older) | — | same |
| `/dashboard` fetches per view | 1 | 1 (verified live) | same (structural) |
| Request hang | 30 s timeout | — | same |
| sync_run reads | bounded by sources/batches, not history | — | `tests/test_queries_sync_scale.py` |

Raising a ceiling is legitimate when a deliberate feature warrants it
— do it in the same PR, with the reasoning recorded here. CI machines
never assert wall-clock timings (they vary); every guard is
structural or size-based.

Interactive-latency intent (measured context for Rail J exit 1, not
CI-enforced): landing surfaces interactive well under ~3 s on
broadband against warm DEV; at 32 s the cold-start dominates any
first visit and is excluded from application budgets (§3).

---

## 5. Measurement playbook (repeat after meaningful change)

- **Backend warm latency/payloads:** seed locally
  (`PYTHONPATH=.. python seed_dev.py --reset`), serve
  (`tools/run_dev_seed_api.py`, honors `PORT`/`LOTSYNC_DB_PATH`),
  measure medians against `/vehicles`, `/dashboard`, `/tasks`,
  `/vehicles/{vin}`, the PDF. Production shape:
  `tools/generate_rehearsal_dataset.py --scale production`.
- **Growth probes:** add synthetic `sync_run` rows / a long
  per-vehicle event history to a COPY of the dataset and re-measure
  the hot endpoints.
- **Bundle:** `npm run build` (sizes print; the budget gate runs in
  CI); contributor attribution via `npx vite build --sourcemap` and a
  sourcemap-attribution pass when the shape changes.
- **Render cost:** drive the local dev frontend against the
  production-shape API; measure keystroke/paint main-thread blocks
  with the Performance API (long tasks) at desktop AND a throttled/
  mobile profile.
- **Deployed:** the browser's resource timings on DEV for request
  counts/latency; one idle-wake request for the cold-start figure.
- Structured logs already carry `duration_ms` per request
  (`OBSERVABILITY.md`) — deployed latency evidence needs no new
  instrumentation.

## 6. Accepted limitations & reopening conditions

| Item | State | Reopens when |
|---|---|---|
| Render free-tier cold start (~32 s) | Accepted for DEV; hosting-tier decision at commercial readiness | Production activation / UAT feedback |
| `/vehicles` unpaginated payload (1.43 MB raw / 47 kB gz worst case) | Measured acceptable; recorded | Roster grows well past ~5–10k rows, or UAT shows slow-link pain → server pagination |
| List/timeline render caps at 100/150 with explicit Show-all | Working as designed | UAT shows the escape hatch is too coarse → virtualization becomes the proportionate tool |
| Supabase full client (~94 kB raw of unused sub-clients) | Deferred — touches verified Rail A auth | A dedicated auth-hardening or bundle sprint with its own verification |
| Sentry synchronous (~83 kB in initial) | Deliberate — early-error capture is its purpose | Never for size alone |
| No Sentry tracing / no new perf telemetry | Per Sprint 11 posture (`traces_sample_rate=0`) | Owner-approved observability expansion |
| Legacy pre-DealerDOH dashboards (~9,000 lines, `frontend/src/dashboards/*`) | Dead files OUTSIDE the bundle graph (verified) — repo weight only | Owner-approved cleanup chore |
| Concurrent-staff load testing against Supabase pool | Not exercised this sprint (single-user measurements; `DATABASE_POOL_MAX` untouched) | Rail M UAT with several real concurrent users, or Sprint 17 unattended acquisition going live |

Store #2 / multi-rooftop performance is explicitly out of scope
(`SECURITY_ARCHITECTURE.md` §4 gates the architecture itself);
nothing in this sprint's design worsens the Sprint 17 acquisition
path — the `sync_run` fixes exist precisely because that path grows
history.
