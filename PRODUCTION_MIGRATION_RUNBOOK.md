# DealerDOH Production Migration Runbook

**Status: PLANNED, NOT EXECUTED. No step below has been performed.**

Operator checklist for migrating production LotSync (`v1.0.0-beta.6`,
SQLite, no auth) onto the DealerDOH architecture (Supabase PostgreSQL
+ Supabase Auth). Reasoning, reference data, and decision context live
in [`PRODUCTION_MIGRATION_PLAN.md`](PRODUCTION_MIGRATION_PLAN.md) —
read it before running anything here. If reality diverges from this
checklist mid-run, **stop at the current step and consult the plan's
rollback table**; do not improvise forward.

Conventions: every `[ ]` is performed by the operator (product owner
or their delegate). **G1–G9** are the explicit approval gates
(plan §13) — each is a literal step; nothing proceeds past a gate on
inference. "Verify" lines state what must be true before the next
step. All shell work on production uses Render's dashboard Shell/SSH
for the `lotsync-api` service. Never print or commit secrets.

**Prerequisite for this entire runbook: the Sprint 07 rehearsal (plan
§21) has passed end-to-end**, including a deliberate rollback drill,
and `tools/migrate_sqlite_to_postgres.py` + its validation suite exist
at a tagged commit. No rehearsal pass → nothing below is scheduled.

---

## Release A — DealerDOH code on production (behavior unchanged)

### A.0 Before
- [ ] Rehearsal report reviewed; CI green on `dev`; working tree clean
- [ ] `/release-readiness` run for Release A → verdict recorded
- [ ] T-24h routine backup taken, scp'd off, SHA-256 verified
      (plan §7 procedure) — record timestamp/hash in the release notes
- [ ] **G2: owner approves merging `dev` → `master`** (this IS a
      production deployment — Render + Vercel auto-deploy)

### A.1 Release
- [ ] `/release-train`: release PR `dev` → `master`, checks green,
      merge with a merge commit; tag per repo practice
- [ ] Watch both deploys complete (Render events + Vercel deployment)

### A.2 Smoke (plan §16, Release A row)
- [ ] `GET /health` → 200, `database_engine: "sqlite"` (new keys are
      the expected Release A signature)
- [ ] Frontend loads: **no DEV banner, no login gate**
- [ ] Dashboard / Vehicles / Vehicle Detail / Tasks / Activity /
      Recommendations / Inventory Sync history — all load, data is the
      pre-release data (spot-check vehicle total + newest activity)
- [ ] Work-order PDF downloads
- [ ] Browser console clean; no CORS errors
- [ ] Render Shell (read-only):
      `SELECT MAX(version) FROM schema_migrations` → **9**
      (0009 auto-applied — additive only; expected)
- [ ] Verify: production behaves identically to beta.6 for users

### A.3 Decision
- [ ] **GO** (proceed to monitoring) / **ROLLBACK** (Render "rollback
      to previous deploy" + Vercel "promote previous deployment" —
      safe over the v9 database; see plan §14)
- [ ] `/handoff-report` for Release A
- [ ] Let Release A settle **at least one full business day** with
      normal sync activity before scheduling Release B

---

## Release B — database cutover (maintenance window)

### B.0 Before (days ahead)
- [ ] **G1: owner approves creating Supabase project `dealerdoh-prod`**
- [ ] Provision per plan §9: org DealerDOH, region `us-west-2`,
      chosen plan (§22 decision), **signups disabled immediately**,
      no app tables on the Data API, DB password + session-pooler DSN
      → password manager only
- [ ] Verify: project reachable; `psql`-level connect via pooler DSN
      from the operator machine works; project is empty
- [ ] **G3: owner approves the window** — date, start time, up-to-2h
      announcement, freeze contacts (the sync-running staff) notified
- [ ] `/release-readiness` for Release B → verdict recorded
- [ ] Operator machine ready: repo at the tagged rehearsal commit,
      `tools/migrate_sqlite_to_postgres.py` + validation suite proven,
      plan §15 severity list **printed/open**
- [ ] T-24h: routine backup taken, scp'd off, hash verified; Render
      service events clean

### B.1 Freeze
- [ ] Window opens; announce freeze start to sync operators
- [ ] Confirm no sync currently running
      (`GET /inventory-sync/history` — newest run complete)

### B.2 Final backup (plan §7)
- [ ] Render Shell: SQLite online backup →
      `lotsync-prod-<UTC>Z-final-pre-cutover.db`
- [ ] Record: timestamp · size · SHA-256 · `integrity_check: ok` ·
      all 13 table counts · `schema_migrations` max = 9 ·
      `sqlite_sequence` values
- [ ] **Freeze-quiet check:** newest `event.observed_at`,
      `sync_run.started_at`, `task.created_at` all pre-date freeze
      start — else re-run backup
- [ ] `scp` to operator machine; **local SHA-256 matches on-Render
      hash** (hard stop if not)
- [ ] Second off-host copy to the approved cloud location

### B.3 Hard stop
- [ ] **Suspend the Render service** (dashboard) — writes now
      impossible; users see API-unreachable inside the announced window

### B.4 Import (plan §5)
- [ ] **G4: owner approves running the migration at the production
      DSN** (typed confirmation in the tool)
- [ ] Run `migrate_sqlite_to_postgres.py`: source = the verified local
      final backup; target = `dealerdoh-prod` pooler DSN
- [ ] Tool applies postgres migrations 0001–0009, copies all tables
      FK-safe with verbatim IDs, resets every identity sequence to
      `max(seq, MAX(id))`

### B.5 Validate (plan §6) — the GO/NO-GO evidence
- [ ] Validation report: **all green** — structural (13 tables,
      versions 1–9, indexes, FKs, sequences) · exact per-table counts
      vs. final backup · all domain invariants · ≥10 sampled VINs +
      newest event/task + all sync_runs + pending identities
      field-identical · behavioral query comparisons identical
- [ ] **Any failure = NO-GO:** resume service (SQLite untouched),
      reopen, announce, diagnose offline. This is the designed abort,
      not an emergency.

### B.6 App cutover
- [ ] **G5: owner approves the env flip**
- [ ] Render env: set `DATABASE_ENGINE=postgres`,
      `DATABASE_URL=<pooler DSN>`, `ENVIRONMENT=production`
      (leave `LOTSYNC_DB_PATH` and all `/var/data` vars in place —
      plan §12/§18)
- [ ] Resume/restart the service; watch boot logs to healthy

### B.7 Smoke (plan §16, Release B row — read-only; NO sync)
- [ ] `/health` → 200, `environment: "production"`,
      `database_engine: "postgres"`
- [ ] Frontend: all Release A page checks again — **numbers equal the
      final-backup counts** (vehicle total, open tasks, newest
      activity)
- [ ] Vehicle detail for 2–3 sampled VINs: identical timeline
- [ ] Work-order PDF regenerates; sync history shows all pre-cutover
      runs
- [ ] Console + network clean; Render logs free of pool errors
- [ ] Supabase dashboard: connections ≤ pool max (4)

### B.8 Decision
- [ ] **GO** — reopen: announce freeze end; frontend back in service
- [ ] **FIX FORWARD** — only §15's minor list qualifies
- [ ] **ROLLBACK** — revert the three env vars → service restarts on
      untouched SQLite → reopen on old stack (zero loss before first
      PG write); record everything
- [ ] `/handoff-report` for Release B

### B.9 Post-cutover (plan §17)
- [ ] First 15 min / first hour monitoring per plan table
- [ ] **Next business morning: the supervised first sync** — the
      deliberate point-of-no-return write, watched end-to-end (upload
      → run → history → generated tasks/events sane). From this moment
      rollback is no longer loss-free (plan §14)
- [ ] Days 2–7 daily checks per plan §17; first Supabase-side backup
      verified present

---

## Release C — authentication enabled

### C.0 Prep (after B is comfortable; G8 not required first)
- [ ] Owner supplies the first-cohort roster (names/emails/roles) and
      the canonical identifiers (organization_id, dealership_id —
      plan §22 #2–3)
- [ ] **G6: owner approves creating real production users**
- [ ] Production-guarded provisioning tool: create `organization` +
      `dealership` rows, Supabase Auth users (pre-confirmed, strong
      generated passwords → password manager), one `user_membership`
      row each with the rostered role
- [ ] Supabase Auth config: Site URL = production frontend URL;
      redirect URLs; email provider only; signups still disabled
- [ ] Render env: set `SUPABASE_URL`,
      `DEALERDOH_DEALERSHIP_ID=<prod dealership id>` — `AUTH_MODE`
      stays unset (inert; sub-minute restart)
- [ ] Verify: `/health` fine; app unchanged (auth still disabled)

### C.1 Off-production validation (plan §11 step 3)
- [ ] Vercel **preview** build of the same commit with production
      Supabase vars, pointed at the production API (temporary CORS
      entry for the preview origin if needed)
- [ ] Each first-cohort user logs in on the preview URL successfully;
      `IdentityFooter` shows the right identity
- [ ] Remove any temporary CORS entry

### C.2 Gate on (frontend first — deliberately before enforcement)
- [ ] Production Vercel env: `VITE_SUPABASE_URL`,
      `VITE_SUPABASE_ANON_KEY`; redeploy
- [ ] Verify: production URL now shows the login gate; each
      first-cohort user signs in and reaches the normal app (backend
      still ignoring tokens); no console errors
- [ ] Problem here? → Vercel "promote previous deployment" (instant,
      gate gone) — plan §14

### C.3 Enforcement
- [ ] **G7: owner approves `AUTH_MODE=required`**
- [ ] Render env: `AUTH_MODE=required` (auto-restart)

### C.4 Smoke (plan §16, Release C row)
- [ ] Unauthenticated `GET /vehicles` (curl) → **401**;
      `GET /health` → still 200 public
- [ ] Each first-cohort user: login → Dashboard/Vehicles/Tasks load;
      `/me` shows correct identity, role, store
- [ ] Work-order PDF as an authenticated user
- [ ] `lot_staff` account attempts sync run → **403** (safe positive
      test of the one role gate); admin/manager sees sync page + history
- [ ] Logout works; session survives refresh; no token material in
      Render logs; console clean
- [ ] Verify next real sync (admin/manager, normal business flow) runs
      normally under auth

### C.5 Decision
- [ ] **GO** / **FIX FORWARD** (single-user credential issues) /
      **ROLLBACK**: `AUTH_MODE` → `disabled` (~1 min) restores open
      access; optionally revert the frontend gate too — both proven
      independent reverts (plan §14)
- [ ] Announce to the cohort; `/handoff-report` for Release C
- [ ] Monitor per plan §17 (auth-failure counts added to the watches)

---

## Stabilization, retirement, and Release D

- [ ] Day ~7 after B (with C landed and quiet): **G8 — owner declares
      the migration stable** on the monitoring record (plan §17).
      Rollback window formally ends
- [ ] Post-G8: rename `lotsync.db` →
      `lotsync.db.legacy-<cutover date>` on the disk; remove
      `LOTSYNC_DB_PATH` at the next routine env touch. **The disk
      itself stays** — it still serves config/staging/outputs
      (plan §18)
- [ ] Day ~90: **G9 — owner approves deleting the legacy DB file**
      from the disk; off-host backups retained ≥ 1 year (or per §22
      decision). LotSync git tags/baseline docs remain permanent
      history
- [ ] Release D (domain/rebrand): its own plan and approvals, only
      post-G8 — plan §19. Not covered by this runbook
- [ ] Employee offboarding (standing procedure from C onward):
      membership `active=false` first, then ban/delete the Supabase
      user (plan §10)

---

## Quick-reference: rollback moves

| Situation | Move |
|---|---|
| Release A bad | Render rollback-to-deploy + Vercel promote-previous (or `git revert` on `master`) |
| B before env flip | Resume service; nothing changed |
| B after flip, before first PG write | Revert `DATABASE_ENGINE`/`DATABASE_URL`/`ENVIRONMENT` → restarts on untouched SQLite |
| B after writes exist | Loss-bearing: env revert + manually re-run the day's syncs from source CSVs — owner call, plan §14 |
| C gate broken | Vercel promote-previous |
| C enforcement broken | `AUTH_MODE=disabled` env revert |
