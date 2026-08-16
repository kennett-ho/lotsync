# DealerDOH Production Migration Plan

**Status: PLANNED, NOT EXECUTED.** Nothing in this document has been
performed against production. Production remains LotSync
`v1.0.0-beta.6` (commit `13c4f815`, SQLite, no auth) exactly as
recorded in `PRODUCTION_BASELINE.md`.

**Produced:** 2026-08-16 (Infrastructure Sprint 06 — Production
Migration Planning). Companion operator checklist:
[`PRODUCTION_MIGRATION_RUNBOOK.md`](PRODUCTION_MIGRATION_RUNBOOK.md).
This document holds the reasoning and reference data; the runbook
holds the numbered steps. If they ever disagree, stop and reconcile —
neither is authorized to improvise past the other.

This plan moves production from:

```text
LotSync PROD                          DealerDOH PROD
Vercel (lotsync)                      Vercel (lotsync project, DealerDOH code)
    ↓                                     ↓
Render FastAPI (lotsync-api)   →      Render FastAPI (lotsync-api)
    ↓                                     ↓
SQLite /var/data/lotsync.db           Supabase PostgreSQL (dealerdoh-prod)
no auth                                   + Supabase Auth (email/password)
```

Everything below was verified against the actual repository at `dev` =
`a2f6322`, the live endpoints, and a read-only inspection of the
verified production backup — not assumed from older documents.

---

## 1. Target production architecture

### Frontend
- **Vercel project:** the existing production project (currently
  serving `https://lotsync-nu.vercel.app`). No new project — the same
  project simply builds newer code when `master` advances. Rename and
  custom domain (`app.dealerdoh.com`) are Release D, not part of the
  operational migration.
- **Branch tracking:** `master` (unchanged).
- **Auth configuration:** `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY`
  (publishable anon key only). The login gate activates **only when
  both are set at build time** (`frontend/src/auth/supabase.ts`) —
  this is the mechanism that keeps Releases A and B invisible to
  frontend users and makes Release C an explicit, reversible flip.
  `VITE_ENVIRONMENT` is never set in production (that renders the DEV
  banner).

### API
- **Render service:** the existing `lotsync-api` (Starter plan,
  Oregon). No new service. Service rename is cosmetic and deferred to
  Release D at the earliest (the `.onrender.com` URL is baked into the
  frontend bundle and CORS — renaming is its own small cutover).
- **Branch:** `master`, auto-deploy (unchanged — a push to `master`
  remains a production deployment).
- **Runtime:** Python 3.12, same start command. The persistent disk
  **stays attached** — see §18: it holds `oms_config.xlsx`, upload
  staging, and report output, not just the database.
- **Engine/auth posture by release:** `DATABASE_ENGINE` unset →
  `postgres` at Release B; `AUTH_MODE` unset → `required` at
  Release C. Both are read at documented single points
  (`database/repository.py::connect`, `api/auth.py::auth_mode`) and
  both default to today's behavior.

### Database
- **Supabase project:** `dealerdoh-prod` — a NEW project in the
  existing DealerDOH Supabase org. **Region `us-west-2` (Oregon)** to
  match the Render service and the proven dev topology.
- **Connection:** the **session pooler** DSN (IPv4 — Render cannot
  reach Supabase's IPv6-only direct connections; proven in dev).
  Server-side app pool: `psycopg_pool`, min 1 / max
  `DATABASE_POOL_MAX` (default 4) — well inside session-pooler limits
  for a single-instance service.
- **Schema:** migrations 0001–0009 from
  `database/migrations_postgres/`, applied by the same runner
  production code already uses, tracked in `schema_migrations`.
- **Data API:** no app tables exposed (match dev). The browser never
  queries the database; FastAPI remains the only boundary. RLS remains
  deferred under the documented conditions in `AUTH_ARCHITECTURE.md`.
- **Backups:** Supabase-side automated backups become the primary
  ongoing mechanism (daily on Pro plan — see §20 cost decision), with
  the final pre-cutover SQLite backup retained as the migration-epoch
  artifact.

### Auth
- **Supabase Auth on `dealerdoh-prod`:** email/password provider only,
  **public signups disabled from the moment the project is created**,
  admin-created pre-confirmed users, ES256 signing (project JWKS;
  FastAPI pins the algorithm and checks issuer/audience/exp — the
  Sprint 05 verifier, unchanged).
- **Site URL / redirect URLs:** the production frontend URL at
  Release C (updated again at Release D when the domain lands).
- **First users:** manager/admin only, provisioned before the auth
  flip — see §11.

### Data ownership
- From Release B GO onward, **Supabase PostgreSQL is the sole
  authoritative production datastore.** The SQLite file stops being
  written the moment the service restarts with `DATABASE_ENGINE=postgres`
  (nothing else writes it) and becomes a frozen rollback artifact.
- **No dual-write exists and none is designed.** The rollback story is
  restore-from-frozen-SQLite (§15), not reverse synchronization.
- The frozen SQLite file and its verified backups remain the rollback
  boundary until the stabilization declaration (§17), then become
  legacy archives (§18).

---

## 2. Cutover strategy — decision

**Recommended: Option A, short maintenance window.**

The deciding facts, measured from the verified production backup
(§4): the entire production dataset is **14,606 business rows in a
4.02 MiB file**, write traffic is a single operator-triggered route
(`POST /inventory-sync/run` is the **only** non-GET route in the
API — verified by enumerating every route decorator), and actual
usage is ~2 sync batches per day concentrated in business hours. A
full copy of this dataset is a seconds-scale operation; validation is
the long pole at minutes-scale.

| Option | Verdict | Reasoning |
|---|---|---|
| **A — short maintenance window** | **RECOMMENDED** | Freeze → backup → import → validate → flip → smoke, in one sitting. Every step is observable, every abort path is "keep SQLite, reopen, nothing happened." Total window fits in 90 scheduled minutes with ~20–30 expected active minutes. The dealership already tolerates larger interruptions (dev cold starts, overnight closes). |
| B — shadow migration + delta copy | Rejected | Preloading PostgreSQL early buys nothing when the full copy takes seconds. The delta step requires change-tracking the schema does not have (most tables lack updated-at columns; `event` is append-only but `vehicle` is upserted in place), so "copy only what changed" means building new tracking machinery — new code, new failure modes, zero payoff at this size. |
| C — dual write | Rejected | Two authoritative stores, split-brain risk on partial failure, doubled write-path code in a codebase whose value is that `connect()` is one line of difference between engines. Weeks of work to avoid a maintenance window measured in minutes. Assessed as required by the sprint scope; rejected without reservation. |

Simplicity and rollback clarity win over zero-downtime engineering at
this scale, exactly as the sprint direction anticipated.

---

## 3. Release decomposition — decision

**Recommended: four releases, in order, each with its own approval,
smoke, and rollback.** Splitting is safer than one big cutover: each
release changes exactly one thing, so a failure implicates exactly one
change and each rollback is independently trivial.

### Release A — DealerDOH code on production, behavior unchanged
Merge `dev` → `master` via the normal release train. Production gets
the dual-engine + auth-capable code while **running exactly as
before**: `DATABASE_ENGINE` unset (SQLite), `AUTH_MODE` unset
(disabled), no new env vars, frontend built without Supabase vars (no
gate, no banner — the frontend delta is confined to the env-gated
banner, the env-gated auth module, and an inert Bearer-attachment
branch in `client.ts`).

- The 454-test suite passing on both engines, with auth tests, is the
  standing proof that the disabled-path is byte-for-byte pre-Sprint-05
  behavior.
- **One deliberate production change rides along:** on first boot the
  migration runner applies `0009_access_model.sql` to the production
  SQLite database — purely additive (two new empty tables, one
  nullable column, one index). This is planned, not incidental: it
  means the final pre-cutover backup is already schema-v9 and imports
  1:1 into the v9 PostgreSQL schema.
- **Rollback:** redeploy beta.6 (Render rollback + Vercel promote, or
  `git revert`). Verified safe against the applied 0009:
  `_pending_migrations` only applies files the running code ships and
  skips versions already recorded, so beta.6 code runs cleanly over a
  v9 database and never touches the two tables it doesn't know about.
- `/health` gains `environment` ("unspecified" until the var is set at
  Release B) and `database_engine: "sqlite"` keys — the expected smoke
  signature of Release A.

### Release B — database cutover (the maintenance window)
No code deploys. Provision `dealerdoh-prod` (pre-approved, §10), then
inside the window: freeze → final backup → import → validate → set
`DATABASE_ENGINE=postgres` + `DATABASE_URL` (+ `ENVIRONMENT=production`)
on Render → service auto-restarts on PostgreSQL → smoke → reopen.
Users see a brief outage and then the identical application.

- **Rollback:** remove/revert the env vars; the service restarts on
  the untouched SQLite file. Free until the first PostgreSQL write
  (§15's point of no return).

### Release C — authentication enabled
Users and memberships provisioned first (§11–12), login flow validated
on a Vercel preview build against `dealerdoh-prod`, then: production
frontend redeployed with the Supabase vars (login gate live; backend
still `disabled` — the app works normally after login, tokens are
attached and ignored), verify real logins, then flip
`AUTH_MODE=required` on Render.

- **Why after B, not before:** membership rows live in the app
  database. Provisioning them after the database cutover means they
  are created once, directly in the final store, instead of being
  created in SQLite and migrated a day later. It also keeps the
  auth flip's rollback (env revert) from ever interacting with the
  database flip's rollback.
- **Rollback:** `AUTH_MODE` → `disabled` (env revert, ~1 min) returns
  the API to open access; Vercel "promote previous deployment"
  returns the gate-free frontend instantly. Both proven mechanisms.

### Release D — rebrand and domain cutover
`dealerdoh.com` purchase, `app.`/`api.` subdomains, service/project
renames, CORS and `VITE_API_BASE_URL` updates, Site URL updates.
**Deliberately excluded from the operational migration** — see §19.
Brand risk and infrastructure risk stay separate.

**Combined-vs-separate assessment (required by the sprint):** merging
B and C into one window was considered and rejected. The failure
diagnosis would span two unrelated subsystems (data layer and
identity), the rollbacks interleave (does an auth failure revert the
database flip?), and nothing forces them together — B is invisible to
users, C is visible and deserves its own communication. Separation
costs one extra evening and buys clean fault isolation.

---

## 4. Production data inventory — pre-migration reference

Source: **read-only inspection of the verified production backup**
`lotsync-2026-08-15.db` (SHA-256
`7111f117…c7f226c` re-verified identical at inspection time; taken
2026-08-15T07:33Z via SQLite online backup — see
`PRODUCTION_BASELINE.md`). The live database was not touched. These
figures are the planning reference; the runbook recaptures exact live
counts at freeze time, and THOSE are the numbers validation compares
against.

| | |
|---|---|
| File size | 4,210,688 bytes (4.02 MiB; 1,028 × 4,096-byte pages, 0 freelist) |
| `PRAGMA integrity_check` | `ok` |
| Encoding | UTF-8 |
| Schema | migrations 1–8 applied (all on 2026-08-07 — the database was born at the beta.6 deploy) |
| `PRAGMA foreign_key_check` | 0 violations |
| Data span | first sync 2026-08-07T16:35Z → last activity 2026-08-13T21:32Z |

### Row counts (2026-08-15 snapshot)

| Table | Rows | Notes |
|---|---|---|
| `vehicle` | 4,672 | 4,672 distinct VINs, none null/empty; `display_name` fully populated |
| `event` | 8,876 | |
| `event_freshness` | 682 | |
| `task` | 362 | |
| `task_execution_event` | 0 | |
| `recommendation` | 0 | engine live, nothing currently open |
| `sync_run` | 12 | all `complete`; sources: tekion 3, keyper 3, recovr 3, rapidrecon 2, mdd 1 |
| `pending_identity` | 2 | both `pending` |
| `dealership` | **0** | see anomalies |
| `employee` | **0** | see anomalies |
| `schema_migrations` | 8 | |
| **Business rows total** | **14,606** | |

### Domain profile (validation invariants draw from these)

- `vehicle.tekion_status`: Sold 3,482 · Stocked In 1,158 · Reserved 30
  · Received 1 · On hold 1 (⇒ 1,190 non-Sold)
- `vehicle.keyper_status`: NULL 3,635 · In 772 · Out 265
- `vehicle.mdd_status`: NULL 4,334 · not_paired 338
- `vehicle.recovr_status`: NULL 3,266 · paired 1,162 · not_paired 244
- `task.commitment_standing`: outstanding 358 · moot 3 · honored 1;
  every `execution_status` = not_started
- `task.task_type`: install_mdd_beacon 332 · install_recovr_device 22
  · investigate_key_for_recovr 8
- Orphan checks: 0 orphans on `event.vin`, `task.vin`,
  `recommendation.vin`, and `event.sync_run_id` (loose-affinity
  compare)
- Timestamps: ISO-8601 TEXT with microseconds throughout;
  `event.event_time` spans 2022-10-26 → 2026-08-13 (historical
  in-service dates — legitimate)

### AUTOINCREMENT high-water marks (`sqlite_sequence`)

| Table | seq | Rows | |
|---|---|---|---|
| `event` | 8,876 | 8,876 | |
| `task` | 362 | 362 | |
| `sync_run` | 12 | 12 | |
| `pending_identity` | **3** | **2** | one row was inserted and later removed — sequence exceeds count |

### Anomalies relevant to migration (recorded, none blocking)

1. **`dealership` and `employee` are empty.** Production has never
   populated either table (importer-level attribution was never
   wired). Consequences: the import ships zero rows for them, and the
   production `organization` + `dealership` rows required by auth are
   **created as an explicit Release C provisioning step** — they do
   not exist to migrate. `DEALERDOH_DEALERSHIP_ID` must be set to the
   created dealership's id (a naming decision — §22).
2. **`pending_identity` sequence (3) > row count (2)** — proof that
   sequence resync must key off high-water marks, never `COUNT(*)`.
3. **`event.sync_run_id` is 100% integer-like strings** (8,876/8,876)
   — no opaque tags in real data. The dev migration's TEXT-preserving
   cast strategy applies verbatim; values copy unchanged.
4. **All twelve sync runs are `complete`** — no in-flight or failed
   run states to reason about at import time (freeze checks re-verify
   this on the final backup).

---

## 5. Migration tooling (to be built and rehearsed in Sprint 07)

No import tool exists yet (`seed_dev.py` seeds synthetic fixtures; it
does not import). The cutover requires
**`tools/migrate_sqlite_to_postgres.py`**, built and proven during the
rehearsal (§21) — never first-run against production. Requirements:

1. **Reads a SQLite backup FILE** (opened read-only), never a live
   database. The import source is the verified final backup — the
   exact artifact whose hash and counts were recorded.
2. **Targets a DSN** passed explicitly. Refuses to run without
   `--i-am-migrating-production` plus a typed confirmation phrase when
   the target is not a known dev/rehearsal project (same guardrail
   family as `seed_dev.py` / `provision_dev_auth.py`).
3. Applies `database/migrations_postgres/` 0001–0009 to the empty
   target via the existing runner, then verifies the target is empty
   of business rows before copying (refuses a non-empty target unless
   told it's a re-run after wipe).
4. Copies tables in FK-safe order: `organization` → `dealership` →
   `employee` → `vehicle` → `sync_run` → `event` → `event_freshness`
   → `pending_identity` → `task` → `task_execution_event` →
   `recommendation` → `user_membership`. IDs copied **verbatim**;
   TEXT timestamps and JSON `detail_fields` copied unchanged; batched
   inserts inside a transaction per table.
5. **Resets every identity sequence** after copy:
   `setval(max(sqlite_sequence.seq, MAX(id)))` per AUTOINCREMENT table
   — PostgreSQL identity sequences do not advance on explicit-ID
   inserts, and skipping this makes the first post-cutover INSERT
   collide. (§4's pending_identity row is the standing reminder.)
6. Runs the §6 validation suite automatically and emits a
   pass/fail report with every count and invariant — the operator
   GO/NO-GO artifact.

---

## 6. Validation plan (Release B, inside the window, before the flip)

Validation compares the **migrated PostgreSQL** against the **final
frozen backup** (not against §4's planning snapshot). All checks are
read-only and scripted (§5's tool); the operator reads a report, not
raw tables. Any failure = NO-GO, keep SQLite, reopen, diagnose outside
the window.

**Structural**
- `schema_migrations` contains exactly versions 1–9.
- All 13 expected tables exist (§4's eleven + `organization` +
  `user_membership`).
- Every index from `database/migrations_postgres/` exists.
- FK constraints valid (a full-scan re-check, not just trusting
  import order); CHECK constraint on `user_membership.role` present.
- Every identity sequence ≥ its table's MAX(id) and ≥ the SQLite
  high-water mark.

**Counts** — per-table exact equality with the final backup, all 13
tables, zero tolerance.

**Domain invariants** — recomputed on PostgreSQL and compared to the
same queries on the final backup: the full §4 domain profile
(tekion/keyper/mdd/recovr status breakdowns, task standing ×
execution × type, sync_run status+source, pending_identity status),
distinct-VIN = vehicle count, the four orphan checks all zero (the
`event.sync_run_id` check via the dev-proven explicit-cast query), and
min/max of `event.observed_at`, `event.event_time`,
`sync_run.started_at`/`completed_at`, `task.created_at`.

**Representative rows** — script-compared field-by-field, both stores:
≥10 operator-sampled VINs covering: Sold, Stocked In, Keyper Out,
RecovR paired, RecovR not_paired, MDD not_paired, a multi-task
vehicle, a vehicle with recent events; plus the newest event, the
newest task, all 12+ sync_run rows, and both pending_identity rows.
(Real VINs appear only in the operator's terminal, never in committed
docs.)

**Behavioral** — the app's own query layer
(`queries/dashboard.py`, `queries/vehicles.py`, `queries/tasks.py`,
work-order data query, activity feed) run locally with
`DATABASE_ENGINE=postgres` pointed at the migrated database, results
compared to the same functions against the final backup. Read-only
paths only — **no sync is run and no task is mutated during
validation**; the first real write is a deliberate post-cutover event
(§17).

---

## 7. Backup & recovery plan

Naming convention:
`lotsync-prod-<UTC timestamp, e.g. 2026-09-05T0300Z>-<purpose>.db`
plus a `.sha256` sidecar; `<purpose>` ∈ `routine | pre-release-A |
final-pre-cutover`.

**T-24h before Release B:**
- Verify the standing backup chain: latest backup's SHA-256 re-checked
  on the local copy; Render disk healthy (service events clean);
  rehearsal-proven scripts (`migrate…py`, validation) at their tagged
  versions.
- Take a fresh routine backup (same online-backup procedure as
  `PRODUCTION_BASELINE.md`), scp off, verify hash — confirms the
  whole pipeline works today, not just last month.

**T-0, inside the window (after freeze, before anything else):**
1. SQLite online backup on the Render disk (the documented
   `src.backup(dst)` procedure — safe against concurrent writes, but
   the freeze means there are none).
2. Record: UTC timestamp, size, SHA-256, `PRAGMA integrity_check`,
   all 13 table counts, `schema_migrations` max (must be 9
   post-Release-A), and `sqlite_sequence` values.
3. **Freeze-quiet check:** newest `event.observed_at`,
   `sync_run.started_at`, and `task.created_at` must all pre-date the
   announced freeze start. If anything is newer, a write slipped in —
   re-run the backup. This closes the backup-to-suspend gap honestly
   (see §8).
4. Copy off-host: `scp` to the operator machine; SHA-256 must match
   the on-Render hash. This local, verified copy is the **import
   source and the rollback artifact**.
5. Second off-host copy to the approved cloud location (per the
   standing baseline procedure).

**No cutover proceeds without step 4's hash matching.** The final
backup is retained permanently as the migration-epoch artifact (§18).

---

## 8. Write freeze / maintenance window

**Write surface (verified by route enumeration):** exactly one
mutating route exists — `POST /inventory-sync/run`. Everything else
is GET (the work-order PDF is a GET; report CSVs are written by sync
runs, not by reads). No scheduled jobs, no background writers. A
"write freeze" therefore means: no one triggers an inventory sync.

**Mechanism (simplest safe, in layers):**
1. **Scheduling** — the window runs outside sync hours (syncs happen
   ~2×/day in business hours; an evening window has a naturally empty
   write calendar).
2. **Coordination** — the operator tells the small set of sync-running
   staff the freeze start/end. This is a one-store deployment with
   ~2 known sync operators; a phone call is a real control here.
3. **Verification** — §7's freeze-quiet check proves, from the backup
   itself, that nothing wrote after freeze start.
4. **Hard stop** — immediately after the backup is copied off and
   verified, the operator **suspends the Render service** (dashboard
   action). From that moment writes are impossible, not just
   forbidden. The service stays suspended through import and
   validation and comes back only via the env-flip restart.

Suspend-first-then-backup was considered and rejected: Render's
shell/SSH (needed for the online backup) requires a running instance.
The residual backup-to-suspend gap is ~1 minute, covered by layers
1–3.

**Window:** schedule **90 minutes**, announce up to 2 hours.
Expected actual: backup+scp ~5 min, import ~5 min, validation ~10
min, env flip + restart ~5 min, smoke ~15 min ⇒ ~40 min with slack.
During suspension users see the frontend load but API calls fail —
acceptable inside an announced window (an optional static
maintenance note is a Release D-era nicety, not a requirement).

**Abort at any point before the env flip:** resume the service —
SQLite was never touched; nothing happened.

---

## 9. Production Supabase provisioning plan (execute only with explicit approval)

| Item | Plan |
|---|---|
| Project | `dealerdoh-prod`, in the existing DealerDOH org — **created only after the §14 approval gate, not during Sprint 06** |
| Region | `us-west-2` (Oregon) — colocated with Render |
| Plan | Pro recommended (§20) — decision in §22 |
| DB password | Generated at creation, straight into the owner's password manager; never in git, never printed |
| Connection | Session pooler DSN only (IPv4); recorded solely in Render's `DATABASE_URL` + password manager |
| Data API | No app tables exposed (match dev posture) |
| Auth | Email provider only; **public signups disabled at creation time** (before any DNS/URL is public); Site URL + redirect URLs set at Release C prep |
| Signing | ES256 (project default asymmetric keys); FastAPI pins ES256 — the legacy-HS256 consideration from the Sprint 05 findings applies to configuration review, not code |
| Secrets storage | DSN + service-role key: password manager + Render env only. Anon key: public by design (frontend bundle). Service-role key used only by the operator provisioning tool, never deployed |

Provisioning produces an empty, configured project. Schema and data
arrive only inside the Release B window via §5's tool.

---

## 10. Real user onboarding plan (Release C prep)

- **Rollout order:** (1) owner/admin + managers — the people who run
  syncs; (2) lot staff; (3) other departments later. First cohort is
  deliberately small (~3–5 accounts).
- **Account creation:** admin-created via the provisioning tool
  (production-guarded evolution of `tools/provision_dev_auth.py` —
  Sprint 07 scope), pre-confirmed (no email-delivery dependency), no
  public signup ever. Roster (real names/emails/roles) comes from the
  owner at C-prep — **real emails do not appear in git docs**.
- **Membership:** one `user_membership` row per user against the
  production organization + dealership rows (created in the same
  provisioning step), role per the owner's roster. Roles are the four
  governed values; only admin/manager may trigger syncs (the one
  enforced restriction — unchanged).
- **Password delivery:** operator-generated strong passwords delivered
  in person / by phone (a dealership is a physical workplace — this
  beats configuring production SMTP for launch); users may change
  passwords via Supabase's standard flow later. No passwords in git,
  chat logs, or email.
- **First login flow:** user signs in at the production URL → gate
  passes → `/me` shows identity/role/store (the `IdentityFooter`).
  Nothing else changes about the UI.
- **Disablement/offboarding:** set the membership row `active=false`
  (access dies at the FastAPI boundary regardless of Supabase session
  state — the membership lookup runs per request), then ban/delete the
  Supabase user. Employee departure = same two steps, documented in
  the runbook as a standing procedure.

---

## 11. Auth cutover sequence (Release C, exact order)

1. **Prep (any time after Release B stabilizes):** provision users +
   organization + dealership + membership rows (§10) directly in
   `dealerdoh-prod`. Configure Supabase Auth Site URL + redirects for
   the production frontend origin.
2. Set Render env `SUPABASE_URL` + `DEALERDOH_DEALERSHIP_ID` (the
   production dealership id) **while `AUTH_MODE` stays disabled** —
   verified inert: `api/auth.py` reads them only on the required
   path. (The restart this causes is a normal sub-minute Render env
   restart.)
3. **Validate off-production:** a Vercel **preview deployment** of the
   same frontend commit, built with the production Supabase vars,
   pointed at the production API. Real first-cohort users log in on
   the preview URL; API keeps ignoring tokens (disabled mode). Proves
   the full Supabase-Auth ↔ frontend flow against `dealerdoh-prod`
   with zero production exposure. (Preview origin may need a temporary
   CORS allowlist entry — remove after validation.)
4. Set the production Vercel env (`VITE_SUPABASE_URL`,
   `VITE_SUPABASE_ANON_KEY`) and redeploy → **login gate is live** on
   the production URL; backend still disabled, so a logged-in user
   gets the identical app (tokens attached, ignored). Confirm each
   first-cohort user can sign in.
5. Flip `AUTH_MODE=required` on Render (auto-restart).
6. Smoke (§16's auth section): unauthenticated API → 401;
   authenticated user → data; `/me` correct; lot_staff sync attempt →
   403 (a denial is a safe positive test); cross-checks on CORS and
   console.
7. Announce to the first cohort; monitor per §17.

**Frontend-first is deliberate:** gate-without-enforcement (step 4) is
harmless; enforcement-without-gate would 401 every browser call. The
sequence never passes through the broken combination, and each step is
individually revertible.

---

## 12. Environment variable cutover matrix (names only — values live in host dashboards / password manager)

### Backend — Render `lotsync-api`

| Variable | Today (beta.6) | After A | After B | After C | Notes |
|---|---|---|---|---|---|
| `DATABASE_ENGINE` | absent (⇒ sqlite) | absent | **postgres** | postgres | the Release B flip |
| `DATABASE_URL` | absent | absent | **prod pooler DSN (secret)** | same | |
| `DATABASE_POOL_MAX` | absent | absent | optional (default 4) | same | headroom knob; default fits |
| `ENVIRONMENT` | absent (⇒ "unspecified") | absent | **production** | production | set in B's env batch for honest `/health` |
| `AUTH_MODE` | absent (⇒ disabled) | absent | absent | **required** | the Release C flip |
| `SUPABASE_URL` | absent | absent | absent | **prod project URL** | set at C-prep (inert while disabled) |
| `DEALERDOH_DEALERSHIP_ID` | absent | absent | absent | **prod dealership id** | must match the provisioned row (§22 naming) |
| `LOTSYNC_DB_PATH` | `/var/data/lotsync.db` | same | **kept, unused** | kept, unused | rollback pointer; removed at §18 retirement |
| `LOTSYNC_CONFIG_PATH` | `/var/data/oms_config.xlsx` | same | same | same | **still live — disk stays (§18)** |
| `LOTSYNC_API_UPLOADS_DIR` / `LOTSYNC_OUT_DIR` / `LOTSYNC_UPLOADS_DIR` | `/var/data/…` | same | same | same | sync staging + report output — still live |
| `LOTSYNC_CORS_ORIGINS` | prod Vercel URL | same | same | same (+ temporary preview origin during C-3 only) | domain additions are Release D |
| `PYTHON_VERSION` | 3.12.0 | same | same | same | |

### Frontend — Vercel production project

| Variable | Today | After A | After B | After C | Notes |
|---|---|---|---|---|---|
| `VITE_API_BASE_URL` | prod Render URL | same | same | same | changes only at Release D |
| `VITE_SUPABASE_URL` | absent | absent | absent | **prod project URL** | build-time; requires redeploy |
| `VITE_SUPABASE_ANON_KEY` | absent | absent | absent | **prod publishable key** | public by design |
| `VITE_ENVIRONMENT` | absent | absent | absent | absent | never set in production (DEV banner) |

Frontend vars are **baked at build time** — every frontend env change
implies a redeploy, and Vercel "promote previous deployment" is the
instant rollback for exactly this reason.

---

## 13. Deployment train mapping and approval gates

Every release runs the committed process: `/release-readiness` →
explicit approval → `/release-train` (merge `dev` → `master` **only
in Release A**; B and C are env-and-operations trains that still get
readiness review, approval, smoke, and handoff) → `/production-smoke`
→ `/handoff-report`. `/data-migration`'s hard rules govern every
database-touching step.

**Explicit operator (product-owner) approvals — nothing proceeds past
these on inference:**

| Gate | Approves | Before |
|---|---|---|
| G1 | Create `dealerdoh-prod` Supabase project | any provisioning (§9) |
| G2 | Release A: merge `dev` → `master` | the code release train |
| G3 | Release B window date/time + freeze | announcing the window |
| G4 | Migrate data (run §5's tool at production DSN) | the import |
| G5 | Flip production env to PostgreSQL | the B env change |
| G6 | Create real production users/memberships | C-prep provisioning |
| G7 | Flip `AUTH_MODE=required` | the C enforcement flip |
| G8 | Declare migration stable (ends rollback window) | §17 stabilization |
| G9 | Retire legacy SQLite artifacts | any §18 action |

The runbook enumerates these as literal checklist items. There are no
"continue automatically" steps anywhere in the sequence.

---

## 14. Rollback plan by failure point

| Failure point | Production impact | Rollback |
|---|---|---|
| Before Release A merge | none | nothing to roll back |
| Release A deploy fails / smoke fails | code-level only; SQLite untouched | Render "rollback to previous deploy" + Vercel "promote previous deployment" (or `git revert` on `master`); DB safe under beta.6 code even with 0009 applied (verified runner behavior) |
| B: pre-flip (backup, import, or validation fails) | none — service suspended, SQLite authoritative and untouched | fix nothing live: resume service, reopen, diagnose offline. **This is the designed abort path — validation failure is a NO-GO, not an emergency** |
| B: post-flip smoke fails | service running on PostgreSQL; **no writes yet** (smoke is read-only) | revert the three env vars → service restarts on the untouched SQLite; window reopens on the old stack; zero data loss |
| B: failure discovered after reopening, before any write | same as above | same env revert, still zero-loss |
| B: failure after post-cutover writes exist | **the hard case** — see point of no return below | env revert loses PostgreSQL-only writes; §15 governs |
| C: gate or login broken (step 4) | users can't get in; API unaffected | Vercel promote previous deployment (instant, gate gone) |
| C: `AUTH_MODE=required` misbehaves (valid users rejected, etc.) | API rejects traffic | `AUTH_MODE` → `disabled` env revert (~1 min restart) → exact pre-C behavior; frontend gate can stay (harmless) or be reverted too |

### Point of no return — explicit

> **The rollback boundary is the first accepted production write into
> PostgreSQL** (in practice: the first post-cutover inventory sync,
> deliberately scheduled and supervised the next business morning —
> §17). Before it, reverting to SQLite is a pure env change with zero
> data loss. After it, SQLite is stale: reverting loses every
> PostgreSQL-era write unless it is manually re-entered (at ~2
> operator-triggered syncs/day, re-running the day's syncs is the
> realistic recovery, and source CSVs make that possible — but it is
> manual, lossy-by-default, and to be avoided).

Policy: PostgreSQL must survive smoke + the supervised first sync
before the freeze is lifted mentally — and the **stabilization
period is 7 days** (recommended, §22) during which the frozen SQLite
file, disk, and backups are untouched and the env-revert procedure
stays documented and ready. G8 (stability declaration) formally ends
the rollback window; §18 retirement begins only after it.

---

## 15. Rollback acceptance criteria (decided before the window, not during)

**Immediate rollback (revert env now, diagnose later):**
- API cannot reach PostgreSQL (pool exhaustion/connection failures)
  persisting beyond ~5 minutes of triage
- Any count/invariant mismatch discovered post-flip (missing
  tasks/events/vehicles)
- Data-corrupting behavior (writes failing mid-sync, constraint
  errors on normal operations)
- (C) valid first-cohort users systematically rejected while
  `required`

**Release-blocking NO-GO (abort before the flip — not a rollback,
nothing changed):**
- Final backup hash mismatch or freeze-quiet check failure
- Any §6 validation failure
- Import tool error of any kind

**Fix-forward (note, monitor, do not roll back):**
- Cosmetic issues; console noise; CORS grumbles from non-production
  origins
- Single-user login trouble (credential fix, not systemic)
- Moderately elevated latency (Supabase pooler adds network hops —
  expected small increase; rollback only if it breaks usability,
  which §17's day-one supervision judges)

The operator carries this list into the window printed in the runbook;
severity assignment happens against the list, not ad hoc.

---

## 16. Production smoke plan (first DealerDOH production release train)

The `/production-smoke` workflow, extended per release. All checks
read-only except where marked; write actions minimal and explicit.

**Release A** (code on SQLite, no auth): frontend loads with **no
banner and no login gate**; `/health` 200 with
`database_engine: "sqlite"`; Dashboard / Vehicles / Vehicle Detail /
Tasks / Activity / Recommendations / Inventory Sync history all load
with **pre-release data unchanged** (spot-check total vehicle count
4,672-era figure and newest events); work-order PDF downloads; no
console errors; CORS behavior unchanged; `/docs` reachable (unchanged
beta posture); production SQLite now at schema v9 (verify via a
read-only shell query, or infer from healthy boot + logs).

**Release B** (PostgreSQL): `/health` 200 with
`environment: "production"`, `database_engine: "postgres"`; every
Release A page check again — **numbers must equal the final-backup
counts** (vehicle total, open-task count, newest activity timestamps);
vehicle detail for 2–3 of the §6 sampled VINs renders identical
timelines; work-order PDF regenerates; sync **history** shows all
pre-cutover runs; no console/network errors; **no sync is triggered**
(first write is the §17 supervised event); Render logs clean of pool
errors over the smoke period.

**Release C** (auth): unauthenticated API call → 401; login page
renders at production URL; each first-cohort user logs in; `/me`
reports the right identity/role/store; all pages load authenticated;
work-order PDF (authed GET); `lot_staff` account attempting sync run
→ 403 (safe positive test of the only role gate); logout works;
session survives refresh; no token material in logs; CORS still
scoped; console clean.

**Cross-store checks** apply when a second store ever exists (blocked
on per-row scoping — out of scope here, noted to keep the checklist
honest).

---

## 17. Post-cutover monitoring

| Horizon | Who | Watch |
|---|---|---|
| **First 15 min** (inside window) | operator, live | smoke checklist; Render logs streaming (no tracebacks, no pool warnings); Supabase dashboard connection count (expect ≤ pool max 4); `/health` repeatedly |
| **First hour** | operator | error scan of Render + Supabase logs; memory/CPU on the Render service; latency feel on Dashboard/Vehicles; (C) failed-login count in Auth logs |
| **Next business day** | operator + managers | **the supervised first sync** — the deliberate point-of-no-return write, watched end-to-end (upload → run → history → tasks/events generated sane); manager confirmation that numbers/workflows look right; count spot-checks vs. expectations |
| **Days 2–7** | operator daily | Render + Supabase error logs; pool saturation; sync success each day; task-generation anomalies (counts that jump inexplicably); backup verification (first Supabase-side backup restorable/present); performance perception |

**Decider:** the product owner declares the migration stable (gate
G8), on the recommendation of this monitoring record — target day 7.
Until G8, the rollback artifacts stay frozen and the env-revert
procedure stays on the table.

---

## 18. Legacy SQLite retirement plan (only after G8)

**Correction to the "disk no longer needed" assumption — verified
against the live env contract:** the persistent disk carries more than
the database. `oms_config.xlsx` (business config, actively read),
sync upload staging (`LOTSYNC_API_UPLOADS_DIR`), and report output
(`LOTSYNC_OUT_DIR`) all live on `/var/data`. **The disk stays after
the database migrates.** Only `lotsync.db` becomes legacy. (Moving
config/staging off-disk is possible future work, not part of this
migration.)

Timeline (recommendations; G9 gates every destructive step):
- **Cutover → G8 (day ~7):** everything frozen in place.
- **G8 → day 90:** `lotsync.db` renamed to
  `lotsync.db.legacy-<cutover date>` on the disk (prevents any
  accidental engine-revert from silently writing it; the rename is
  the "read-only/legacy" marker — SQLite has no server to configure).
  `LOTSYNC_DB_PATH` env removed at the next routine env touch.
  Off-host backups untouched.
- **Day 90:** with owner approval (G9), delete the legacy file from
  the disk (the disk itself stays, per above — no plan-downgrade
  decision arises; §20). Off-host final backup + the migration-epoch
  backup are retained **≥ 1 year** (recommended) in the standing
  backup locations.
- LotSync-era artifacts (tags, `PRODUCTION_BASELINE.md`) are permanent
  git history — nothing to archive beyond what git already keeps.

---

## 19. Rebrand / domain cutover (Release D — separate risk, later)

Operational migration (A–C) completes on the existing
`lotsync-nu.vercel.app` / `lotsync-api.onrender.com` URLs. Rationale:
DNS propagation, CORS origin changes, baked `VITE_API_BASE_URL`, and
Supabase Site URL changes are a coupled set with user-facing failure
modes that have nothing to do with the database or auth — mixing them
into B or C would widen every rollback.

Release D outline (its own plan, post-G8): purchase `dealerdoh.com` →
stage `api.dealerdoh.com` on Render + `app.dealerdoh.com` on Vercel
(both platforms serve old and new hostnames simultaneously — a
gradual, revertible cutover) → update `LOTSYNC_CORS_ORIGINS` (add,
don't replace), rebuild frontend with the new API base, update
Supabase Site URL/redirects → verify → retire old URLs only after a
comfortable overlap. Marketing site and in-app brand strings ride
this release. **Recommendation: after stabilization (post-G8), not
before, not during.**

---

## 20. Cost & service plan

| Service | Today | After migration (steady state) | Notes |
|---|---|---|---|
| Render `lotsync-api` | Starter (paid) + 1 GB disk | **Starter (unchanged) + disk (unchanged)** | Free tier's ~50s cold starts are unacceptable for a dealership tool in active use, and the disk remains required for config/staging/outputs (§18). No plan change from this migration. |
| Vercel frontend | Hobby (free) | Hobby, **flagged**: commercial use of a dealership ops tool sits poorly with Hobby's non-commercial terms — Pro (~$20/mo) is the compliant choice. Decision §22. | Static Vite build either way |
| Supabase | Free (`dealerdoh-dev` only) | **Pro recommended (~$25/mo) for `dealerdoh-prod`** | Free tier: no daily backups, project pausing risk, 500 MB cap. Real dealership data deserves automated daily backups + PITR option. Decision §22. Dev project stays free. |
| GitHub | Free (private repo) | Free; **Pro (~$4/mo) still recommended** for branch protection on `master` — the standing `PRODUCTION_BASELINE.md` recommendation gets sharper once `master` deploys the real DealerDOH stack | Decision §22 |
| Domain | none | ~$12–30/yr at Release D | |
| **Net new** | — | **~$25/mo (Supabase Pro) + optional ~$24/mo (Vercel Pro + GitHub Pro) + domain at D** | |

---

## 21. Dry-run strategy (the gate to scheduling any real cutover)

**Sprint 07 (recommended next sprint) = full rehearsal.** No
production cutover is scheduled until a rehearsal has passed
end-to-end. Using dev-side infrastructure only:

1. Build §5's migration tool + §6's validation suite.
2. Generate a **production-shaped synthetic SQLite database** at real
   scale (~4,700 vehicles / ~9,000 events / ~360 tasks, status
   distributions per §4's profile) via a deterministic generator —
   **not** production data (no real data in dev without explicit
   approval and sanitization; synthetic-at-scale also tests import
   performance honestly, which the 34-vehicle QA dataset cannot).
3. Rehearse the full Release B sequence against a disposable
   PostgreSQL target (fresh free-tier Supabase project
   `dealerdoh-rehearsal`, or the CI container locally first): backup
   → hash → import → validate → env flip on a rehearsal API instance
   → smoke.
4. Rehearse Release C: provision synthetic users/memberships with the
   production-guarded tool → gate → `AUTH_MODE=required` → smoke.
5. **Rehearse the rollback deliberately:** revert the env, prove the
   pre-flip stack returns; practice the §15 severity calls.
6. Produce a timing report per step → feeds the real window estimate
   (§8) and the `/release-readiness` evidence for Release B.

The standing QA dealership and its CI assertions remain untouched;
the rehearsal uses disposable stores.

---

## 22. Decision register

### Decided by this plan (standing unless the owner overrides)
- Cutover strategy: **Option A** — short maintenance window (§2)
- Release decomposition: **A → B → C → D**, four separate approvals
  (§3); DB and Auth deliberately in **separate releases**
- Import source: the **verified final backup file**, never the live DB
  (§5); import runs from the operator machine
- SQLite remains authoritative until the G5 flip; **no dual-write**
- Validation is scripted, exact-count, invariant-checked (§6); any
  failure = NO-GO
- Point of no return: **first accepted PostgreSQL write**; supervised
  first sync the next business day (§14, §17)
- The Render persistent disk **stays** post-migration (§18)
- Rehearsal (Sprint 07) is a prerequisite to scheduling Release B (§21)

### Recommended (owner accepts or overrides, no blocker either way)
- Supabase **Pro** for `dealerdoh-prod` (~$25/mo) — §20
- Keep Render **Starter**; no plan changes — §20
- Stabilization period **7 days** (G8 target); legacy DB file deleted
  at **day 90**; off-host backups kept **≥ 1 year** — §17, §18
- Rebrand/domain (Release D) **after** G8 — §19
- Evening maintenance window, 90 min scheduled — §8
- `ENVIRONMENT=production` set during Release B's env batch — §12

### Unresolved — owner decisions required before execution
1. **Release B date/time + window** (G3) — after rehearsal passes
2. **First-account roster** — names, emails, roles for the first
   cohort (G6 input); password delivery method confirmation (§10)
3. **Canonical production identifiers** — `organization_id` /
   `organization.name`, `dealership_id` (=`DEALERDOH_DEALERSHIP_ID`)
   / `dealership.name`/`brand` (e.g. `mark-auto-group` / `mark-kia` —
   naming is the owner's call)
4. **Supabase plan** — Pro vs Free for production (§20)
5. **Vercel plan** — Hobby vs Pro (commercial-terms compliance, §20)
6. **GitHub Pro** — branch protection on `master` (§20; standing
   recommendation from the baseline)
7. **Who besides the owner may declare an immediate rollback** during
   the window (§15) — default: owner only
8. **Rollback-artifact retention** — accept the 90-day / 1-year
   recommendation or set different periods (§18)
9. **Release D timing** — when (and whether) the domain/rebrand
   executes relative to G8 (§19)

---

*Sprint 06 (this document + the runbook) is planning only. The first
execution step — creating `dealerdoh-prod` (G1) — happens in a future,
explicitly approved sprint, after the Sprint 07 rehearsal proves the
tooling this plan requires.*
