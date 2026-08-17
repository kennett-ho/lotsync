# DealerDOH v1.1.0-beta.1 — Release Scope & Readiness Register

**Status: authoritative release contract for `v1.1.0-beta.1`.**
Created Infrastructure Sprint 08 (2026-08-16). Production remains
LotSync **`v1.0.0-beta.6`** (`master` @ `13c4f815`, SQLite, no auth)
and stays there until every REQUIRED rail below passes its exit
conditions and `/release-readiness` returns ready.

`v1.1.0-beta.1` is the first DealerDOH-era production release: the
Sprint 06/07-proven migration (Releases A–C: code → PostgreSQL →
Auth) carrying the product work defined here. The migration rail is
technically proven (`PRODUCTION_MIGRATION_REHEARSAL.md`: PASS);
cutover is deferred **only** because the rails in this register are
deliberately planned first.

**How this document is amended:** scope changes go through the Scope
Discipline rules (§3). Classification changes (REQUIRED ↔ CONDITIONAL
↔ POST-v1.1) require an explicit owner decision recorded in this file
and `SPRINT_HISTORY.md`. Nothing enters or leaves the release
silently.

**Rail lettering note:** this document follows the Sprint 08
specification's lettering (A–M). `SPRINT_HISTORY.md`'s rail catalog
letters diverge from D onward (its D=Notifications, E=Ingestion,
F=Automated Ingestion, then G–N). Mapping: prompt D = history E ·
prompt E = history D · prompt F/G = history G/H · prompt H–M =
history I–N. Same rails, same intent; this file is the operative
register.

---

## 1. Readiness Register

| Rail | Priority | Status | Planned Sprint | Blocks v1.1? | Exit Condition (summary — full text in §5) | Evidence Required |
|---|---|---|---|---|---|---|
| A — Account Lifecycle & User Administration | REQUIRED | **Verified** (Sprint 09, 2026-08-16: PR #12 merged as `02958f2`; CI green on the merged head — 488/488 SQLite, 488/488 PostgreSQL, frontend build, Vercel; post-merge smoke on `dev`-tracking DEV re-passed the full matrix incl. the real emailed invite→fresh-link→set-password→global-signout→login loop, manager/lot-staff authorization probes, deactivate→reactivate cycle, deployed-bundle secret scan clean, and a live `signup_disabled` probe) | 09 | **Yes** | Password reset + provisioning + Profile/Settings + offboarding all pass their §5.A criteria on deployed DEV | Merged PR `02958f2` · CI green on merged head · deployed-DEV smoke (branch + post-merge) · `tests/test_user_management.py` matrix |
| B — Onboarding & Contextual Help | REQUIRED | Planned | 12 | **Yes** | Tutorial, Help entry points, empty/loading/error states pass §5.B; UAT confirms no-coaching operation | Merged PR · CI · DEV smoke · Rail M UAT evidence |
| C — Role-Aware Presentation | REQUIRED | Planned | 12 | **Yes** | Manager + Lot Staff presentations verified; zero authorization drift (§5.C) | Merged PR · CI · DEV smoke both roles · negative authz tests · UAT |
| D — Inventory Ingestion Safety | REQUIRED (high operational priority) | **In Progress** (Sprint 10, 2026-08-16: implementation complete on `feature/sprint-10-ingestion-safety` — all seven §5.D classes + preview + execution revalidation built and fixture-tested, suites 548/548 both engines locally, local UI verification passed; pending: PR gate/CI, deployed-DEV smoke, and **owner ratification of the proposed suspicious-count thresholds** — see the §5.D decisions block) | 10 | **Yes** | All seven §5.D validation classes enforced + pre-sync preview; invalid evidence cannot reach the sync engine | Merged PR · CI (incl. adversarial fixtures) · DEV smoke · QA-dataset regression intact |
| E — Notifications | **CONDITIONAL** (Sprint 08 decision — §6.1) | Deferred pending trigger | 12.5 if triggered | Only if triggered | Trigger fires (§6.1) → minimal in-app center passes its criteria | Trigger record · then B-style evidence |
| F — Observability (Sentry + PostHog) | REQUIRED | Planned | 11 | **Yes** | §5.F: DEV/PROD separation, redaction verified, synthetic failure visible, events arriving, telemetry cannot break workflows | Merged PR · CI · DEV smoke incl. synthetic error · redaction test evidence |
| G — Structured Logging & Monitoring | REQUIRED | Planned | 11 | **Yes** | §5.G: structured fields present, denylist enforced by test, alert conditions defined with owners | Merged PR · CI incl. redaction tests · DEV log samples |
| H — Production Security Hardening | REQUIRED | Planned | 13 | **Yes** | §5.H: audit → remediate → adversarially verify → re-audit; no reachable Critical/High open | Audit reports (both passes) · fix PRs · adversarial test evidence |
| I — Dependency / Supply-Chain Security | REQUIRED | Planned | 13 (within H's sprint) | **Yes** | §5.I: scans clean of reachable Critical/High or explicitly excepted; CI scanning live | Scan outputs · exception register · CI job green |
| Repository Public-Release Sanitation | REQUIRED before any private→public visibility change | **Not Audited** | 13 (within H's sprint) | **No — blocks repository publication only, not v1.1** | §5.H.1: full-history secret audit passes; every historical exposure rotated/revoked; current-tree checks pass; final re-scan clean | Audit report · rotation records · history-cleanup assessment · re-scan |
| J — Performance & Resilience | REQUIRED | Planned | 14 | **Yes** | §5.J thresholds met at 4,700+ vehicle scale incl. slow-network behavior | Measurement report vs thresholds · fix PRs · CI |
| K — Accessibility | REQUIRED (blocking subset — §5.K) | Planned | 14 | **Yes** (blocking subset) | Blocking subset passes on core workflows; remainder documented as tracked remediation | Audit checklist · fix PRs · DEV keyboard/contrast evidence |
| L — Privacy / Legal Readiness | REQUIRED ASSESSMENT (internal-beta subset blocks — §5.L) | Planned | 15 | **Yes** (subset) | Data inventory accurate; internal-beta documents published; commercial items explicitly deferred with owner sign-off | Data-flow inventory · published docs · deferral record |
| M — Human User Acceptance Testing | REQUIRED | Planned | 16 | **Yes** | Manager + Lot Staff UAT complete; all release-blocker findings fixed and re-verified | UAT session notes · blocker list dispositions · re-test evidence |
| Production migration (Releases A–C) | REQUIRED | **Rehearsed** (Sprint 07 PASS — not executed) | RC/cutover (17+) | **Yes** | Runbook executes at cutover; Sprint 18-era re-verification confirms rehearsal assumptions still hold | `PRODUCTION_MIGRATION_REHEARSAL.md` · refreshed rehearsal if drift · runbook completion record |
| Automated Report Ingestion | **CONDITIONAL** (§6.2) | Discovery (owner) | v1.1 only if trigger met; else v1.1.x | Only if triggered | Vendor capability confirmed + bounded scope → owner opts in | Vendor discovery answers · scope estimate · owner decision |

Register statuses used: Planned · Discovery · In Progress ·
Implementation Complete — Awaiting Merge · Verified · Deferred · N/A.
**Nothing above is marked Verified** — no rail has release-grade
evidence yet; the migration rail is deliberately "Rehearsed," not
Verified, because rehearsal ≠ production execution.

---

## 2. Classification Summary

**REQUIRED (blocks v1.1.0-beta.1):** A, B, C, D, F, G, H, I, J,
K (blocking subset), L (internal-beta subset), M, and the production
migration itself.

**CONDITIONAL (enters only if its trigger fires — §6):**
E (Notifications), Automated Report Ingestion.

**POST-v1.1 (explicitly out, cannot silently re-enter — §7):** MFA,
enterprise SSO, advanced user administration, SMS/push/Slack/digest
notifications, notification preferences, session replay (pending
privacy review), RLS, full per-row store scoping (Store #2 trigger),
webhooks, AI-assistant tooling, GLBA-regulated data handling, public
API, payments/billing, object storage, commercial legal pack
(SaaS agreement/DPA), Release D domain/rebrand execution (its own
post-cutover release train), CHANGELOG backfill beyond release notes.

---

## 3. Scope Discipline (the anti-creep contract)

After Sprint 08, a new requirement may enter `v1.1.0-beta.1` **only**
if at least one is true:

1. It fixes a release blocker found by a REQUIRED rail's own exit
   testing (including UAT).
2. It fixes a Critical/High security finding that is actually
   reachable.
3. It prevents material data or operational-truth corruption.
4. It is necessary for real dealership UAT to proceed at all.
5. The owner makes an explicit, recorded scope decision.

Everything else lands in `v1.1.x`, `v1.2`, or Backlog — recorded, not
argued into the release. A CONDITIONAL rail cannot be promoted because
implementation "seems interesting"; its trigger must actually be met
and the promotion recorded. Anything that would push a POST-v1.1 item
into scope requires rule 5 explicitly.

---

## 4. Evidence Rules (what "done" means)

| Change class | Minimum evidence to mark a register row Verified |
|---|---|
| Any implementation | Merged into `dev` (not merely on a branch) |
| All code | CI green on the merged `dev` head — SQLite suite, PostgreSQL suite, frontend build |
| Runtime-visible change | Deployed-DEV smoke (`/smoke-test`) of the real path — e.g. Rail A's reset flow must be exercised on the deployed DEV stack with real Supabase recovery email, not only unit-tested |
| Security-sensitive change | Negative/adversarial tests (wrong role, wrong store, expired/forged token, malicious input) committed to the suite, not run once by hand |
| Operational-workflow change | QA-dealership scenario coverage and/or Rail M UAT observation |
| Database/migration change | Dual-engine tests; migration applied on both engines; `tools/migrate_sqlite_to_postgres.py` expectations updated if schema moves past 0009 (see migration-drift note, §8) |
| Telemetry/logging change | Redaction proven by test (denylist strings asserted absent from emitted records) |
| Legal/privacy | Written record of what was reviewed, what is published, and what still requires counsel — no unsupported claims |
| Conditional rail | The trigger record itself, then the rail's normal evidence |

Only evidence of these kinds moves a row to Verified. "It worked when
I tried it" is not a register state.

---

## 5. REQUIRED Rails — purpose, risk, exact exit conditions

### 5.A — Rail A: Account Lifecycle & User Administration
- **Owner sprint:** 09 · **Blocks `/release-readiness`:** yes
- **Purpose:** real dealership users must be able to get in, get
  back in, and be removed — without the developer acting as the
  identity system.
- **Release risk addressed:** locked-out staff on day one; orphaned
  access after departures; support burden concentrated on one person;
  credential-handling improvisation under pressure.
- **Established decisions honored:** no public signup — accounts are
  created/invited by an authorized Manager/Admin; roles/stores come
  from the membership table only (Sprint 05 architecture, unchanged).

**Exit conditions (all must hold on deployed DEV):**

*Password reset*
1. Login screen exposes "Forgot password".
2. Reset requests flow through Supabase-managed secure recovery (no
   custom token scheme).
3. The public response does not disclose account existence beyond
   what the chosen policy accepts (uniform "if an account exists…"
   messaging).
4. The recovery link returns the user to DealerDOH and lets them set
   a new password meeting policy — **including via direct URL
   navigation: the SPA deep-link rewrite (`vercel.json`) is REQUIRED
   scope of this rail** (owner decision 2026-08-16 — recovery/reset
   links may depend on direct routing; see §8).
5. A used or expired recovery link fails safely with a
   comprehensible, non-leaking message and a retry path.
6. The new password works; the old one does not.
7. Session/token behavior after reset matches the **selected,
   documented policy** (Sprint 09 must decide and record: revoke all
   other sessions on reset [recommended default] or keep them — and
   test whichever is chosen).
8. The full path — request → email → link → new password → login —
   is smoke-verified on deployed DEV with a synthetic user and real
   email delivery.

*User provisioning*
9. A Manager/Admin can execute the approved provisioning workflow
   (the production-guarded evolution of `tools/provision_dev_auth.py`
   and/or an in-app flow — Sprint 09 decides the v1.1 mechanism and
   records it) which assigns dealership + role membership
   authoritatively.
10. `lot_staff`/`sales_manager` cannot create, promote, or disable
    users — proven by negative tests.
11. No public signup path exists (Supabase signups remain disabled;
    verified in DEV config and by attempting it).

*Profile/Settings*
12. Every control on Profile/Settings works, is clearly read-only,
    or is removed — zero decorative controls. Identity, role, and
    store are displayed from the authenticated membership.

*Disablement/offboarding*
13. Setting a membership `active=false` revokes access at the next
    request (already the architecture); the operator procedure
    (membership first, then Supabase user ban/delete) is documented
    where operators will find it and exercised once on DEV.

*Session lifecycle*
14. Sign-out works; session survives refresh; expiry behaves
    per policy; the chosen reset-revocation policy (7) is tested.

**Evidence:** merged PR(s); CI green both engines; deployed-DEV smoke
transcript of 1–8; committed negative tests for 10–11; the recorded
policy decisions (7, 9).

### 5.B — Rail B: Onboarding & Contextual Help
- **Owner sprint:** 12 · **Blocks:** yes
- **Purpose:** a new dealership user performs ordinary work without
  the developer standing beside them.
- **Release risk addressed:** the product's operator knowledge
  currently lives in one person; onboarding friction converts
  directly into abandoned workflows and phone calls.

**Exit conditions:**
1. First login presents a tutorial that can be completed **or**
   skipped; either choice persists (it does not re-trap the user
   every login; persistence survives refresh and re-login).
2. Help is reachable from every core screen (Dashboard, Vehicles,
   Vehicle Detail, Tasks, Inventory Sync).
3. Inventory Sync help explains, in dealership language, which
   reports/slots/files are expected and what common rejections mean
   (kept consistent with Rail D's validation messages).
4. Every critical workflow has deliberate empty, loading, and error
   states (no blank panels, no raw stack text, no dead ends without
   a next action).
5. Rail M UAT: both roles complete their core tasks without
   developer coaching; tutorial/help usage observed rather than
   assumed.

**Evidence:** merged PR; CI; DEV smoke walking tutorial complete AND
skip paths; state-persistence check; UAT notes (Rail M).

### 5.C — Rail C: Role-Aware Presentation
- **Owner sprint:** 12 (with B — one coherent UX sprint) ·
  **Blocks:** yes
- **Purpose:** Manager and Lot Staff get presentations matched to
  their work — one application, one operational model, no fake role
  switcher; the authenticated membership decides.
- **Release risk addressed:** management noise buries lot-staff
  execution; managers miss oversight surfaces; worst case, UI
  divergence quietly widens into authorization divergence.

**Exit conditions:**
1. Manager presentation emphasizes overview, inventory health,
   recommendations, sync controls, wider task visibility, system
   warnings — verified against the QA dealership on DEV.
2. Lot Staff presentation emphasizes Today's Work, grouped tasks,
   vehicle lookup/detail, work orders — verified likewise.
3. **Zero authorization drift:** no action becomes available or
   performable because presentation differs — the backend remains
   the only authority; negative tests prove lot_staff still cannot
   reach manager-gated actions through any UI path or direct call
   (the Sprint 05 guarantee re-proven after UI change).
4. Role presentation derives from the server-verified membership
   (`/me`), never client-selectable state.
5. Rail M UAT validates both experiences.
6. The two UX findings planned into this sprint (§8: sold-vehicle
   browse path, sidebar/Vehicle-Detail dismissal) are addressed as
   planned work — **non-blocking for v1.1 unless Rail M UAT
   demonstrates otherwise** (owner decision 2026-08-16; the SPA
   deep-link rewrite moved to Rail A as REQUIRED, same decision).

**Evidence:** merged PR; CI incl. re-run auth negative suite; DEV
smoke both roles; UAT notes.

### 5.D — Rail D: Inventory Ingestion Safety
- **Owner sprint:** 10 (deliberately early) · **Blocks:** yes
- **Purpose:** DealerDOH must never convert a wrong, empty, or
  mis-generated spreadsheet into false operational truth. *Missing
  evidence ≠ zero. Invalid evidence ≠ valid zero.*
- **Release risk addressed:** the highest-severity failure the
  product can produce — silently corrupting the dealership's picture
  of reality (e.g., a 14-row export processed against 987 tracked
  vehicles).
- **Architecture:** one classification/validation boundary that all
  ingestion paths converge on (manual upload today; scheduled
  email/vendor API later — the conditional rail reuses this exact
  boundary):

```text
Manual Upload ─────┐
Scheduled Email ───┼─→ Report Classification / Validation → Preview → Accept/Reject → Sync Engine
Vendor API ────────┘
```

**Exit conditions — each validation class enforced, tested with
committed adversarial fixtures, and explained to the user in plain
language:**
1. **Empty spreadsheet** → rejected (message names the likely export
   mistake).
2. **Headers but no data rows** → rejected.
3. **Missing required columns** → rejected, missing fields named
   (extends the existing header check with report-type awareness).
4. **Wrong report type** → detected and blocked from the wrong
   contract: at minimum Keyper Full Inventory vs Key Event, and
   Tekion Current vs Sold, are classified and never interchangeable;
   additional contracts driven by real vendor formats as they are
   confirmed.
5. **Invalid VIN/record shape** → rejected or quarantined per the
   governed decision Sprint 10 records (reject-row vs quarantine
   file — decide once, document, test).
6. **Duplicate rows** → identified before any mutation; policy
   (dedupe rule) recorded and tested.
7. **Suspicious count change** → a configured threshold (Sprint 10
   sets the default, e.g. drop >N% vs the prior comparable report)
   forces warning/review or rejection — never silent processing.
8. **Pre-sync preview** shows: detected source, detected report
   type, row count, valid-VIN count, duplicate count, invalid count,
   prior comparable count, difference (count/percent), warnings, and
   readiness — and only validated evidence can proceed to the sync
   engine.
9. The standing QA dealership regression (both engines) still
   passes untouched — validation must not alter accepted-evidence
   semantics.

**Evidence:** merged PR; CI with fixture-driven tests for every
class above; DEV smoke of preview accept AND reject paths; QA
regression green.

**Sprint 10 recorded decisions (2026-08-16 —
`INGESTION_ARCHITECTURE.md` is the canonical detail):**
- *Exit 5 (invalid VIN/record shape):* **quarantine-file, never
  silent row drops** — blank VINs in identity-originating reports
  (Tekion current/sold) reject the file with line numbers; malformed
  VINs warn; identity-inert sources (RecovR/MDD/RapidRecon) warn
  only. Evidence files are never edited.
- *Exit 6 (duplicates):* surfaced as warnings with counts/samples
  per contract semantics; sold-report VIN repeats deliberately
  unflagged (legitimate history, owned by the existing
  `tekion_sync_conflicts` machinery); never silently deduplicated.
- *Exit 7 (suspicious count):* mechanism complete (scoped
  `report_baseline` comparisons, migration 0010). **Default
  thresholds are PROPOSED, PENDING OWNER RATIFICATION at the Sprint
  10 PR gate:** warn on drop >15% AND ≥10 rows; warn on increase
  >50% AND ≥25 rows (grounding: `INGESTION_ARCHITECTURE.md` §8).
  Rail D cannot be marked Verified until the owner ratifies or
  adjusts these numbers.
- *Exit 4 (wrong type / Keyper):* the Keyper **Key Event Report is
  recognized-but-unsupported with zero invented schema** (no sample
  exists); it is rejected explicitly and can never satisfy the full
  snapshot requirement. Filling the real contract awaits §6.2 vendor
  discovery — Event *ingestion* is not a Rail D requirement.
- *Zero-row policy per contract:* hard-reject for authoritative/
  historical snapshots (Tekion current/sold, Keyper full, RecovR);
  warn + explicit acknowledgement for the exception/contextual lists
  (MDD not-paired, RapidRecon), whose empty state is plausible; the
  acknowledged zero is then recorded honestly as zero.
- *Standing rule for future unattended ingestion:* any WARNING
  defaults to **HOLD** — automation never auto-acknowledges (the
  §6.2 conditional rail inherits this boundary unchanged).

### 5.F — Rail F: Observability (Sentry + PostHog)
- **Owner sprint:** 11 (deliberately before the UX build — §9) ·
  **Blocks:** yes
- **Purpose:** *what is breaking* (Sentry) and *what are users doing*
  (PostHog) answerable without SSH-ing into anything — before UAT
  and before production.
- **Release risk addressed:** flying blind in the first production
  weeks; UAT anecdotes with no telemetry to confirm them.

**Exit conditions:**
1. DEV and (future) PROD telemetry are separated (distinct
   projects/keys/environments); release version and environment tag
   every event.
2. Sentry captures frontend and backend exceptions with request
   correlation, route, and safe user/dealership context.
3. **Redaction proven, not promised:** passwords, JWTs,
   Authorization headers, DB credentials, recovery links, and raw
   report contents never appear — asserted by tests that emit
   would-be-sensitive payloads and verify scrubbing.
4. A synthetic frontend error and a synthetic backend error each
   appear in Sentry from deployed DEV.
5. The chosen PostHog product events arrive from deployed DEV with
   correct properties. Initial event set (trim/extend in Sprint 11
   with rationale): Inventory Sync Started / Validated / Rejected /
   Completed / Failed · Help Opened · Tutorial Completed · Work
   Order Generated.
6. Telemetry failure cannot break workflows: with Sentry/PostHog
   unreachable or keys absent, the app functions (proven by test or
   DEV exercise).
7. Session replay stays **off** pending an explicit privacy/
   redaction review (POST-v1.1 unless that review happens and
   passes).

**Evidence:** merged PR; CI incl. redaction tests; screenshots/links
of the synthetic events in both tools from DEV; the event-set
decision record.

### 5.G — Rail G: Structured Logging & Operational Monitoring
- **Owner sprint:** 11 (with F) · **Blocks:** yes
- **Purpose:** every request leaves a structured, correlatable,
  redacted trace; defined conditions alert a human.
- **Release risk addressed:** undiagnosable production incidents;
  secrets leaking into logs; silent sustained failure.

**Exit conditions:**
1. Backend logs are structured records carrying: timestamp, level,
   environment, request/correlation ID, safe user ID, dealership ID,
   route, HTTP status, duration, safe error code, release version.
2. The denylist is enforced by test: passwords, access tokens,
   Authorization headers, private/service keys, DB credentials,
   recovery tokens, sensitive raw report bodies — never logged.
3. Request IDs correlate app logs ↔ Sentry events.
4. Monitoring/alert conditions are defined with thresholds and a
   named recipient, at minimum: sustained 5xx rate, DB unreachable,
   Inventory Sync failure, repeated auth failures, storage problems,
   abnormal operational-result counts (e.g., a sync that would
   change counts beyond Rail D's threshold). Delivery mechanism may
   be simple (email) — the condition inventory is the requirement.
5. **The telemetry census (anti-duplication):** one recorded table
   states what goes to logs vs Sentry vs PostHog vs alerts — each
   signal has exactly one primary home.

**Evidence:** merged PR; CI redaction tests; DEV log samples showing
the structured fields; the alert-condition inventory.

### 5.H — Rail H: Production Security Hardening
- **Owner sprint:** 13 · **Blocks:** yes
- **Purpose:** audit-then-remediate the system that actually exists,
  adversarially verified, before real dealership data sits behind
  it on the public internet with auth newly enabled.
- **Release risk addressed:** the beta-era acceptance of "unlisted,
  not private" ends at v1.1; auth, uploads, and multi-user roles are
  new attack surface.

**Exit conditions:**
1. **Read-only audit #1** across the full catalog (authentication,
   object/function-level authorization, store/tenant isolation, role
   escalation, secrets, SQLi, XSS, request validation, upload
   validation, path traversal, rate limiting, brute-force, resource
   limits, excessive data exposure, error leakage, debug/test
   routes, security headers, CSP, clickjacking, session/token
   policy, CORS, logging/redaction, race/double-submission,
   business-logic abuse, environment separation) — every item
   classified PASS / FAIL / UNKNOWN / N/A **with code evidence**;
   no control invented for systems that do not exist.
2. Findings prioritized by actual reachability; remediation
   targeted accordingly.
3. Every fix carries adversarial verification (the attack that
   motivated it, committed as a test where feasible).
4. **Read-only audit #2** confirms closure and hunts regressions.
5. Release gate: no reachable Critical/High open; every UNKNOWN
   resolved to a real classification or an owner-accepted,
   documented risk.
6. Known specific items folded in: legacy HS256 key
   disablement/retirement review (Sprint 05 finding); `/docs`
   exposure decision under auth; rate limiting on the new
   reset/login surfaces (coordinates with Rail A's Supabase
   settings).
7. The **Repository Public-Release Sanitation** audit (below) is
   executed as part of this sprint's security pass. Its outcome
   gates a **repository-visibility change, not the v1.1 release**.

**Evidence:** both audit reports; fix PRs with adversarial tests;
the accepted-risk register (owner-signed).

#### 5.H.1 — Repository Public-Release Sanitation (added 2026-08-16, pre-Sprint-09 governance task)

**Context, stated precisely:** current DealerDOH secret-handling
practices are strong — deployment env vars, password-manager
storage, deleted scratch staging, pre-PR secret scans, and a
deliberate frontend-public vs server-secret key separation. **But
historical repository exposure has not yet been proven clean**: a
`.gitignore` entry or a later file deletion does not remove a secret
from prior commits, and earlier LotSync-era history predates these
practices. Public visibility therefore has its own explicit gate.
This does not imply the repository is currently unsafe, and it does
not mean the repository must (or will) become public during v1.1 —
**publication itself remains a separate owner decision**; this
subsection defines what must be true before that decision may
execute.

**Full-history audit (read-only first).** Using appropriate
secret-scanning tooling plus targeted pattern review — never
assuming today's clean tree proves historical cleanliness — inspect:
the current working tree; **all reachable commits, branches, and
tags**; deleted historical files; `.env` / `.env.*`;
deployment/config files; shell scripts; GitHub Actions workflows;
test fixtures; documentation; database dumps; SQLite backups;
temporary/export files ever committed; and old release artifacts if
reachable from the repository.

**Material to search for (minimum):** PostgreSQL/Supabase DSNs
containing passwords; `DATABASE_URL` values; Supabase `sb_secret_*`
keys; legacy `service_role` keys; legacy JWT signing secrets;
database passwords; Render credentials/tokens; Vercel tokens;
GitHub PATs/tokens; SMTP/email credentials; private API keys;
private cryptographic keys; passwords; recovery tokens; webhook
secrets; future Sentry/PostHog server-side secrets; other
high-entropy credential-like material. **Classification must
distinguish intentionally public frontend identifiers (e.g. a
Supabase publishable/anon browser key) from actual secrets** — the
former are findings to note, not exposures to rotate.

**Required response to any real historical secret** (even if later
removed): (1) classify the exposure; (2) determine whether the
credential is still live; (3) rotate/revoke it; (4) update deployed
environments to the replacement; (5) verify application health;
(6) assess whether Git-history cleanup is warranted; (7) **never
treat history rewriting alone as sufficient remediation**.
Principle: *a secret that has entered Git history is exposed —
private-at-the-time is not a reason to retain it.*

**Git-history cleanup rules:** if historical sensitive material
exists, Sprint 13 assesses whether history should be rewritten
before public release (e.g. `git filter-repo` or equivalent) — but:
no automatic rewriting, no automatic force-push, no invalidating
branches/tags without explicit approval; **credential rotation comes
first**; any rewrite requires its own operator approval and a
recovery plan.

**Current-tree public-release checks** (before any visibility
change): `.gitignore` excludes local secret files; `.env.example`
holds placeholders only; no production database/backup files
tracked; no private deployment files publicly served; frontend
bundles contain no server-side secrets; public source maps reviewed;
workflow configuration exposes no unnecessary secrets; CI
secret-scanning exists; dependency/security scanning exists;
repository documentation reveals no credentials; old tags/releases
carry no sensitive attached artifacts.

**Gate and states.**

> **Repository Public Visibility: BLOCKED until the full Git-history
> sanitation audit passes and every historically committed credential
> has been rotated/revoked.**

States: `Not Audited` → `Audit Clean` **or** `Remediation Required`
→ `Remediated — Awaiting Re-scan` → `Cleared for Public Visibility`.

**Current state: `Not Audited`** (no history scan has been
performed; nothing so far proves — or disproves — historical
cleanliness).

**Evidence when executed:** the audit report (tool output + targeted
review notes); per-finding classification; rotation/revocation
records with post-rotation health checks; the history-cleanup
assessment; the current-tree checklist; the final re-scan.

### 5.I — Rail I: Dependency / Supply-Chain Security
- **Owner sprint:** 13 (executes inside H's sprint — one security
  pass, one evidence set) · **Blocks:** yes
- **Purpose/risk:** the app is only as trustworthy as what it ships;
  today there is no scanning gate at all.

**Exit conditions:**
1. npm and Python dependency scans run and are triaged: full
   direct/transitive inventory, lockfiles verified authoritative.
2. Policy applied: reachable **Critical/High** block release until
   fixed or explicitly owner-excepted with rationale and revisit
   date; unreachable/transitive findings documented, not blindly
   upgraded (the standing `nanoid` classification is the model);
   **no breaking auto-upgrades**.
3. Scanning runs in CI (advisory job acceptable at first — the gate
   is the triaged register, not a red X on every transitive notice).
4. Provenance/trust review for anything unusual (install scripts,
   typosquat-adjacent names) — documented pass.

**Evidence:** scan outputs; the exception register; CI job visible
on `dev`.

### 5.J — Rail J: Performance & Resilience
- **Owner sprint:** 14 · **Blocks:** yes
- **Purpose:** the app holds up under the dealership's real shape —
  4,700+ vehicles, large event history, a handful of concurrent
  staff, phones on the lot, Render/Supabase latencies — with no
  invented internet-scale goals.

**Exit conditions (thresholds finalized early in Sprint 14 from
first measurements; targets below are the starting contract):**
1. Dashboard, Vehicles (incl. filter/search), Tasks, Vehicle Detail
   render usable at production scale — interactive under ~3 s on
   broadband DEV, under ~8 s on throttled "slow 4G", each measured.
2. Work-order PDF generation at full outstanding-task volume
   completes within a stated bound (measure first; bound recorded).
3. Inventory Sync round-trip at production scale measured; timeout
   behavior explicit (no infinite spinners — coordinates with
   Rail B states).
4. Query/index review on PostgreSQL at scale: no obviously
   unindexed hot path (the rehearsal dataset generator provides the
   scale fixture); pagination or bounded responses on any list that
   can exceed a few hundred rows — Vehicles at 4,700 must not ship
   the whole table to the browser unpaginated unless measured
   acceptable and recorded.
5. Frontend bundle audited; no accidental multi-MB regressions;
   repeated/unnecessary request patterns identified and fixed.
6. Cold-start behavior (Render) measured and either accepted with
   a loading treatment or mitigated; Supabase pool behavior under
   concurrent staff load verified (no exhaustion at realistic
   concurrency; `DATABASE_POOL_MAX` tuned if evidence says so).
7. Slow/offline behavior: requests fail with comprehensible errors,
   not hangs.

**Evidence:** the measurement report (before/after where fixes
landed) with the recorded thresholds; fix PRs; CI.

### 5.K — Rail K: Accessibility
- **Owner sprint:** 14 (with J) · **Blocks:** the subset below
- **Target:** WCAG 2.2 AA-quality behavior as the engineering
  target; pragmatic blocking subset for an internal dealership beta.

**Blocking subset (must pass on core workflows — login, dashboard,
vehicles/detail, tasks, sync, work-order):**
1. Full keyboard operability (no mouse-only action), visible focus
   throughout, no keyboard traps; modal focus containment + escape.
2. Every form input labeled; errors announced/associated with their
   fields.
3. Color contrast meets AA on text and essential UI.
4. Touch targets usable on phone-scale screens; page zoom to 200%
   doesn't break core flows.
5. Loading/status changes announced (coordinates with Rail B's
   states).

**Documented-remediation (tracked, non-blocking for v1.1):** full
screen-reader flow polish beyond the above, reduced-motion
treatment, comprehensive audit closure across secondary screens —
each carried as register items with owner-visible status, not
dropped.

**Evidence:** audit checklist with per-item pass/fail; fix PRs; DEV
keyboard-walkthrough and contrast-check records; the remediation
register.

### 5.L — Rail L: Privacy / Legal Readiness
- **Owner sprint:** 15 · **Blocks:** internal-beta subset
- **Purpose:** know exactly what data DealerDOH holds and state it
  honestly — before dealership colleagues use it in production; no
  generic policies promising controls that don't exist.

**Exit conditions — internal-beta subset (blocking):**
1. Accurate data-flow inventory: user identity, employee/account
   info, vehicle data, uploaded reports, telemetry (Sentry/PostHog
   as configured by Rails F/G), IP/device metadata actually
   collected, logs, retention per store, subprocessor list (Vercel,
   Render, Supabase, Sentry, PostHog, GitHub — as actually used).
2. Published, accurate internal-beta documents: Privacy Policy and
   Terms of Service scoped to actual behavior; support/security
   contact; internal incident-response procedure (who does what
   when telemetry alarms); data retention/deletion statement
   consistent with the migration plan's retention decisions.
3. Accessibility Statement drafted from Rail K's real results.
4. Every claim in every document traceable to something real.

**Explicitly deferred to commercial rollout (non-blocking,
recorded):** attorney-reviewed customer/SaaS agreement, DPA/security
addendum, formal GLBA posture (back-burner trigger), marketing-site
legal pack. **Attorney review of even the internal-beta set is
recommended and its absence is recorded as an owner-accepted risk —
this register makes no legal-sufficiency claims.**

**Evidence:** the inventory; the published docs; the deferral/risk
record.

### 5.M — Rail M: Human User Acceptance Testing
- **Owner sprint:** 16 · **Blocks:** yes
- **Purpose:** AI smoke testing does not replace dealership users;
  the release gate includes real humans doing real work uncoached.
- **Prerequisite ordering:** runs after Rails A–D, F–G (so telemetry
  observes the sessions) and the UX rails; Sentry/PostHog active
  during sessions.

**Exit conditions:**
1. **Manager UAT:** a real manager receives a login and goals (run
   a sync from real exports; review recommendations; find a
   specific vehicle's history; produce a work order) with zero
   coaching. Observed: hesitation, misclicks, terminology misses,
   missed controls, Help usage, failure recovery, assumptions.
2. **Lot Staff UAT:** same discipline on the operational workflow
   (today's work → vehicle → task → work order).
3. Every finding dispositioned: **release blocker** (user cannot
   complete a core task, data-corrupting confusion, security
   surprise) → fixed and **re-verified with a human**; everything
   else → recorded as post-release UX debt (v1.1.x/Backlog), not
   silently fixed into scope (Scope Discipline rule 1 covers true
   blockers only).
4. Telemetry from the sessions reviewed against observations.

**Evidence:** session notes per role; the dispositioned finding
list; re-test records; telemetry cross-check.

---

## 6. CONDITIONAL Rails

### 6.1 Rail E — Notifications (**Sprint 08 decision: CONDITIONAL — ratified by owner 2026-08-16**)
**Decision rationale (recorded per the sprint's mandate to decide):**
v1.1's ingestion is manual-upload only; the person who runs a sync
sees its outcome immediately on the Inventory Sync page (Rail D's
preview/reject UX strengthens exactly that surface), and dashboard
sync-status already surfaces last-sync state to managers. The
async-failure scenario that makes notifications genuinely necessary
arrives with **unattended ingestion** — which is itself conditional.
Building a notification center ahead of that need is scope the
release doesn't require. This deliberate tightening of
`SPRINT_HISTORY.md`'s "LIKELY REQUIRED" was **ratified by the owner
on 2026-08-16**, with automated ingestion or UAT evidence as the
promotion triggers.

**Triggers (any one fires the rail into scope):**
1. Automated Report Ingestion (§6.2) enters v1.1 → notifications
   become REQUIRED alongside it (unattended failures must reach a
   human), scoped minimal: in-app center, unread/read, timestamp,
   deep link, mark-read, retention.
2. Rail M UAT demonstrates users miss operationally significant
   conditions the existing surfaces don't carry → REQUIRED at the
   UAT-blocker level.
3. Owner explicitly opts it in (Scope Discipline rule 5).

If triggered: owner sprint ≈ 12.5 (between UX and security), and the
POST-v1.1 exclusions stay excluded (no SMS/push/Slack/digests/
preferences).

### 6.2 Automated Report Ingestion (**CONDITIONAL — vendor discovery pending**)
**Trigger to enter v1.1:** vendor capability confirmed **and**
implementation scope bounded (a schedule-stable emailed full
snapshot with a parseable attachment for at least one high-value
source) **and** owner opts in. Otherwise → `v1.1.x`.

**Discovery checklist (owner action — these are dealership/vendor
questions, not code): status Discovery, target: answers before
Sprint 12 planning**
- **Tekion:** scheduled email capability? which report types?
  snapshot vs delta? frequency? attachment format? sender/subject/
  filename stability? export completeness behavior?
- **Keyper:** scheduled Full Inventory Report? Key Event Report?
  formats? snapshot vs event semantics?
- **RecovR:** API availability? dealership IT/vendor approval path?
  browser-automation fallback acceptability?
- **RapidRecon:** confirm the ~daily emailed-summary limitation and
  its exact shape.
- **MDD:** export/API/email mechanisms?

**Standing architectural rule regardless of outcome:** automated
attachments pass through **the same Rail D classifier/validator** as
manual uploads — no second ingestion path, ever. (Rail D is built
with this seam explicitly.)

---

## 7. POST-v1.1 / Back-Burner Trigger Register

Explicit triggers, so future work starts when reality demands it —
never silently before:

| Item | Trigger | Required when triggered |
|---|---|---|
| RLS | Browser gains direct sensitive Supabase table access, or richer multi-store architecture | Policy design sprint per `AUTH_ARCHITECTURE.md`'s documented conditions (policies + non-owner role + tests) |
| Full per-row store scoping | **Before onboarding Store #2** (hard prerequisite, already governed) | Per-row `dealership_id` population + query filters + tests across business tables |
| Webhooks | First inbound third-party webhook | Signature verification, replay protection, idempotency |
| AI tool authorization | DealerDOH assistant gains protected read/action tools | AuthZ outside the model, least-privilege validated tools, prompt-injection defenses, confirmation for irreversible actions |
| GLBA / customer financial data | Any customer financial/leasing/credit data enters the system | Dedicated legal + security review before shipping |
| Public API | First external API consumer | Scoped credentials, rotation/revocation, least privilege, rate limits |
| Payments | Billing/subscriptions introduced | Dedicated payment/security implementation |
| Object storage | Reports/artifacts move to Supabase Storage or similar | Private-by-default policy + authorized access design |
| **Public repository visibility** | Owner intends to change the repo from private → public | Full-history secret audit · credential rotation for every historical exposure · history-cleanup assessment · current-tree sanitation · CI secret/dependency scanning · final re-scan · explicit owner approval (§5.H.1 — audit itself executes in Sprint 13) |
| MFA / SSO / advanced user admin | Owner decision or first enterprise requirement | Rail A extension sprint |
| Session replay | Privacy/redaction review passes | Rail F extension |
| Release D (domain/rebrand) | Post-cutover stabilization (G8) per the migration plan | Its own release train |

---

## 8. Known Findings / Technical Debt Register

| Finding | State | Blocks v1.1? | Owner sprint / disposition |
|---|---|---|---|
| Sold vehicles lack a normal UI browse path (API `include_sold` works) | Open — planned | **No** — unless Manager UAT or a required workflow demonstrates it must ship (owner decision 2026-08-16) | Sprint 12 |
| Sidebar navigation doesn't dismiss open Vehicle Detail | Open — planned | **No** — unless Rail M UAT demonstrates otherwise (owner decision 2026-08-16) | Sprint 12 |
| SPA deep links 404 on Vercel (no rewrites) | Open | **Yes — REQUIRED via Rail A** (owner decision 2026-08-16: recovery/password-reset links may depend on direct routing) | Sprint 09 |
| Tasks page crashes on unknown non-null `priority` values (Sprint 07 finding; latent — production writes NULL) | Open (chip filed) | No (latent) | Sprint 12 with Rail C, or the standing chip |
| Admin ≈ Manager equivalence | Open — by design | No | Revisit only on product justification (POST-v1.1) |
| Full per-row store scoping before Store #2 | Deferred — triggered | No (single-store release) | §7 trigger |
| Legacy HS256 key retirement | Open — operator review | **Yes, via Rail H** exit 6 | Sprint 13 |
| `CHANGELOG.md` stale (ends v0.7.4) | Open — documentation debt | No | Release-notes work at RC freeze (Sprint 17); full backfill POST-v1.1 |
| Automated-ingestion vendor discovery | Discovery (owner) | No (gates only the conditional rail) | Answers before Sprint 12 planning (§6.2) |
| Privacy/legal docs don't exist yet | Planned | **Yes, via Rail L** subset | Sprint 15 |
| Migration-tool schema drift | Standing guard | Contextual | Any sprint that adds migration 0010+ must update `tools/migrate_sqlite_to_postgres.py`'s expectations (`EXPECTED_SCHEMA_VERSION`, tables/order) and its tests, and note it for the RC-freeze rehearsal refresh |
| `SPRINT_HISTORY.md` canonicalization | Resolved this sprint | — | Landed in-repo (Sprint 08); rolling-update procedure applies from here |

---

## 9. Recommended Sprint Order (Sprint 08 analysis)

**Final recommendation — 9 sprints to RC, then cutover:**

| # | Sprint | Rails | Why here |
|---|---|---|---|
| 09 | Account Lifecycle & Settings | A (incl. the REQUIRED `vercel.json` SPA rewrite — owner decision 2026-08-16) | Identity is the foundation every later rail's testing logs in through; smallest-dependency start |
| 10 | Inventory Ingestion Safety | D | **Kept early on purpose:** bad input silently corrupting operational truth outranks UX polish; also defines the seam §6.2 would reuse |
| 11 | Observability & Structured Logging | F + G | **Moved up from the provisional 13 (ratified by owner 2026-08-16):** instrument *before* building the big UX surfaces so the tutorial/help/sync flows ship with events built in (not retrofitted), Sentry watches the UX sprint's own QA, the security audit (13) can audit real telemetry redaction, and UAT (16) runs fully observed |
| 12 | Role-Aware UX + Onboarding/Help | C + B (+ §8 UX findings) | The two UX rails are one coherent build; lands instrumented (11) and validated against safe ingestion (10) |
| 12.5 | *Notifications — only if triggered* | E | §6.1 |
| 13 | Security Hardening + Supply Chain | H + I + Repository Public-Release Sanitation audit (§5.H.1 — gates repo visibility, not v1.1) | Audits the finished auth/ingestion/UX/telemetry surface once, not twice; folds I and the history audit into the same evidence pass |
| 14 | Performance + Accessibility | J + K | After features stabilize so measurements and audits hit the real product; shared browser-audit tooling |
| 15 | Privacy / Legal Readiness | L | Data flows are final only after F/G (and E-if-triggered) settle |
| 16 | Human UAT | M | Everything observable, secure, performant first; fix only true blockers |
| 17 | Release Candidate Freeze | Migration rail + `/release-readiness` | Freeze scope; final audits/regression/smoke; verify Sprint 07 migration assumptions still hold (schema drift → targeted rehearsal refresh with the updated tool); select the production window (G3) |

**Changes from the provisional Sprint 09–18 plan, with reasons:**
1. **Observability moved from 13 → 11** (rationale above — the
   single highest-leverage reorder).
2. **Notifications removed from the required path** (provisional 12)
   → conditional slot 12.5 (§6.1 decision).
3. **Dependency/supply-chain folded into the security sprint**
   (was implicit) — one security evidence pass.
4. Net: **10 sprints → 9** to RC freeze without dropping any
   REQUIRED rail.
5. `SPRINT_HISTORY.md`'s older draft order (10=UX, 11=Ingestion) is
   superseded by ingestion-first — matching the Sprint 08
   specification's own reasoning ("bad input can silently create
   false operational truth").

Sequencing rule: a sprint may start only when the rails it depends
on are Verified or the dependency is explicitly waived by the owner.

---

## 10. Release Gates Summary (the short list that ends in cutover)

1. **Account lifecycle** — real users get in, recover, and are
   removable; no public signup (5.A).
2. **Ingestion safety** — invalid evidence cannot become
   operational truth; preview before mutation (5.D).
3. **Role-aware onboarding** — both roles work uncoached, with
   presentation matched to their jobs and zero authorization drift
   (5.B + 5.C).
4. **Observability** — breakage and behavior visible, redaction
   proven, before any real user depends on it (5.F + 5.G).
5. **Security** — audited, remediated, adversarially verified,
   re-audited; no reachable Critical/High (5.H + 5.I).
6. **Performance & accessibility** — usable at real scale, on real
   phones, by keyboard (5.J + 5.K blocking subset).
7. **Privacy/legal honesty** — accurate inventory and internal-beta
   documents; recorded deferrals (5.L).
8. **Human UAT** — dealership users succeed uncoached; blockers
   fixed and re-verified (5.M).
9. **Final `/release-readiness`** — all register rows Verified,
   scope frozen, migration assumptions re-confirmed → the Sprint
   06/07 runbook executes as Releases A–C at the owner-approved
   window.

---

*This register supersedes all prior informal v1.1 scope lists.
`SPRINT_HISTORY.md` §"Proposed v1.1.0-beta Sprint Roadmap" remains as
historical context; scope and order are governed here. Amendments
follow §3 only.*
