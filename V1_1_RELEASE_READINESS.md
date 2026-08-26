# DealerDOH v1.1.0-beta.1 — Release Scope & Readiness Register

**Status: authoritative release contract for `v1.1.0-beta.1`.**
Created Infrastructure Sprint 08 (2026-08-16). Production remains
LotSync **`v1.0.0-beta.6`** (`master` @ `13c4f815`, SQLite, no auth)
and stays there until every REQUIRED rail below passes its exit
conditions **or carries an explicit, dated owner-waived deferral
recorded in this register** and `/release-readiness` returns ready.

**Release posture amendment (owner decision 2026-08-25 — §11):**
`v1.1.0-beta.1` is a **controlled technical/internal beta release —
Human Validation Deferred to v1.5 Readiness**. It is not the
commercial pilot candidate and is not presented as commercially
validated. Rail M (Human UAT) is deferred from the v1.1 ship gate by
explicit owner waiver and **remains required, unweakened, before
v1.5 Commercial Pilot Candidate readiness** (§11). Sprint 18 is
redefined as the **compressed v1.1 release gate** (§11). This is a
sequencing change only: no UAT requirement is weakened, no absent
evidence is claimed.

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
| B — Onboarding & Contextual Help | REQUIRED | **Verified** (Sprint 12 merged as PR #19 → `dev` = `bafd747`, CI green on the merged head; both DEV services redeployed from `dev` and verified serving the merge SHA. Merged-head evidence 2026-08-19: first-run/completion/replay correct for BOTH roles with completion persisted in `user_metadata` across deploys; Help role-gating verified both directions; the rapid-click clamp survived an 8-click assault on the merged deployment; Sentry clean in the smoke window; six analytics events arriving stamped with the merge SHA, zero PII. UAT no-coaching confirmation deliberately remains Rail M scope. Original branch evidence follows —) (Sprint 12: role-aware Getting Started tour with completion in Supabase `user_metadata` (no migration; skip = completion; replay from Help), Help & Getting Started surface with role-gated sections, contextual recommendations explainer, empty states audited. Deployed-DEV evidence: first-run fired for BOTH roles, completion persisted across reload, replay verified both roles; a rapid-click index-overflow crash was FOUND by the smoke, captured by the Sprint 11 boundary+Sentry (ref `9f338b8d`), fixed and clamp-pinned. Pending: merge · CI on merged head · merged-DEV both-role smoke. Full record in `SPRINT_HISTORY.md`) | 12 | **Yes** | Tutorial, Help entry points, empty/loading/error states pass §5.B; UAT confirms no-coaching operation | Merged PR · CI · DEV smoke · Rail M UAT evidence |
| C — Role-Aware Presentation | REQUIRED | **Verified** (Sprint 12 merged as PR #19 → `dev` = `bafd747`, CI green on the merged head; both DEV services verified serving it. Merged-head evidence 2026-08-19: Manager smoke PASS (Overview landing, manager nav, sync surface + translated reasons) and Lot Staff smoke PASS (Today's Work landing, no-sync nav, freshness, truthful breadcrumb, dismissal, Sold 6-of-34, work order, **live `POST /inventory-sync/run` → 403 with request-id** — zero authorization drift); QA dealership intact, zero mutations, no reseed. UAT confirmation deliberately remains Rail M scope. Original branch evidence follows —) (Sprint 12: server-confirmed-role navigation/landing (manager/admin → Overview; lot_staff → Today's Work over the unchanged task engine; sales_manager shared-honest), Inventory Sync nav omitted where every action 403s, AUTH-disabled generic shape byte-identical to pre-Sprint-12 (test-pinned + verified locally and deployed), audit honesty fixes (dead My Tasks/emp-0142, VIN-only search truth, 9 dead controls incl. local-only Dismiss, exception-code translation, minimal Sold mode), the promoted sidebar-dismissal defect FIXED and verified deployed. 625/625 SQLite · 625/625 PostgreSQL · 37 posture tests. Pending: merge · CI on merged head · merged-DEV both-role smoke. Full record in `SPRINT_HISTORY.md`) | 12 | **Yes** | Manager + Lot Staff presentations verified; zero authorization drift (§5.C) | Merged PR · CI · DEV smoke both roles · negative authz tests · UAT |
| D — Inventory Ingestion Safety | REQUIRED (high operational priority) | **Merged — NOT Verified; Awaiting Vendor Evidence** (Sprint 10: **PR #14 owner-approved and merged as `b389072`, CI green on the merged head** — 548/548 SQLite, 548/548 PostgreSQL, frontend build; all seven §5.D classes + preview + execution revalidation fixture-tested against known vendor evidence; suspicious-count thresholds **owner-ratified** as initial beta policy; **deployed-DEV smoke PASSED pre-merge on the branch review window** — accept + reject matrix + suspicious-count/acknowledgement + direct-API bypass probes (422/409/409) + authz 401s + product tour, QA dealership intact; full record in `SPRINT_HISTORY.md`. **Why not Verified (owner-corrected evidence status):** the real Keyper Event-vs-Full structural distinction is **PENDING VENDOR EVIDENCE** — only safe rejection of nonmatching Keyper-shaped evidence is proven; sprint state: **Implementation Paused — Awaiting Vendor Evidence**) | 10 | **Yes** | All seven §5.D validation classes enforced + pre-sync preview; invalid evidence cannot reach the sync engine | Merged PR ✓ · CI on merged head ✓ (incl. adversarial fixtures) · DEV smoke ✓ (pre-merge branch window) · QA-dataset regression intact ✓ · Keyper Event vendor evidence for the exit-4 Keyper half — **outstanding** |
| E — Notifications | **CONDITIONAL** (Sprint 08 decision; 2026-08-18 amendment — §6.1) | Deferred pending Sprint 17/18 checkpoint, UAT evidence, or owner opt-in | Scheduled only if triggered | Only if triggered | Trigger fires (§6.1) → minimal in-app center passes its criteria before Sprint 18 can pass | Checkpoint/trigger record · then B-style evidence |
| F — Observability (Sentry + PostHog) | REQUIRED | **Verified** (Sprint 11 merged as PR #16 → `dev` = `5ae6c79`, CI green on the merged head; both DEV services redeployed from `dev` and verified serving the merge SHA. Merged-head evidence 2026-08-18: real Sentry receipt from the merged deployment (frontend event, release = merge SHA, environment development, NO user identity/PII, Replay unconfigured — and no crash endpoint exists, the verification trigger was removed pre-merge; backend capture path fake-transport-proven on the same tree); PostHog explicit events arriving with release/environment and internal-UUID identity (anonymous→`auth_user_id` flip observed), zero `$autocapture`/`$pageview` in the project, recorder/replay absent from the deployed bundle; `signup_disabled` live-probed; payload inspection clean (no email/VIN/token). DEV providers configured; production providers deliberately NOT. Full record in `SPRINT_HISTORY.md`) | 11 | **Yes** | §5.F: DEV/PROD separation, redaction verified, synthetic failure visible, events arriving, telemetry cannot break workflows | Merged PR · CI · DEV smoke incl. synthetic error · redaction test evidence |
| G — Structured Logging & Monitoring | REQUIRED | **Verified** (Sprint 11 merged as PR #16 → `dev` = `5ae6c79`, CI green on the merged head incl. redaction tests. Merged-head evidence 2026-08-18: JSON records streaming on the redeployed DEV service with the full schema and the merge SHA as `release`; fresh response↔log correlation proven (curl `X-Request-ID` `ff9b69a8…` found verbatim in the deployed record — `/vehicles` template, 401 = INFO, severity policy live); alert-condition inventory + telemetry census stand with named recipient (`OBSERVABILITY.md` §8). Full record in `SPRINT_HISTORY.md`) | 11 | **Yes** | §5.G: structured fields present, denylist enforced by test, alert conditions defined with owners | Merged PR · CI incl. redaction tests · DEV log samples |
| H — Production Security Hardening | REQUIRED | **Verified** (Sprint 13 merged as PR #21 → `dev` = `6bb3a9c`, CI green on the merged head incl. the new Security scans job; both DEV services verified serving the merge SHA — API `/health` release + bundle bake. **Merged-head deployed evidence 2026-08-19:** API security headers live on 200/404/500 paths (nosniff, DENY, `frame-ancestors 'none'`, no-referrer, no-store); frontend CSP + full header set live; CORS allowlist echo / evil-origin rejection / `X-Request-ID` exposure / preflight all correct; `signup_disabled` live-probed via the bundle key; manager login + Overview/Vehicles/Tasks/Help/Profile/User Management functional under the CSP; work-order PDF 200 `%PDF` with request-id; validate-only upload matrix (UNRECOGNIZED_REPORT, UNSUPPORTED_FORMAT, valid→ready) with zero mutation; tokenless/garbage 401s + unknown-VIN 404 generic; **Sentry zero issues across the probe window** (expected 4xx = no noise, live); QA dealership intact, no reseed; the fail-closed seed guard exercised all four ways non-destructively; production docs-gating subprocess-proven without touching production. The smoke found one Low CSP correction (Google Fonts `@import` blocked — cosmetic fallback) fixed in the closeout PR with a pinning test. Lot Staff/outsider live re-login was credential-gated this pass; the unchanged authz matrix is covered by merged-head CI (`test_auth` role/cross-store negatives) + the Sprint 12 live 403 evidence 20h prior on identical authz code. Audit #1 → remediation → re-audit record: `SECURITY_AUDIT.md`; 0 Critical / 0 reachable High; deferrals owner-visible) | 13 | **Yes** | §5.H: audit → remediate → adversarially verify → re-audit; no reachable Critical/High open | Audit reports (both passes) · fix PRs · adversarial test evidence |
| I — Dependency / Supply-Chain Security | REQUIRED | **Verified** (Sprint 13 merged as PR #21 → `dev` = `6bb3a9c`; the CI `security` job is **live and green on the merged head**: secret scan + `npm audit --omit=dev --audit-level=high` hard gates, `pip-audit` + full `npm audit` advisory. npm production deps clean; `pip-audit` no known vulns; the one `nanoid` High is a build-only devDependency reachable only through vite — documented exception, not force-fixed. Scan outputs + exception register: `SECURITY_AUDIT.md`) | 13 (within H's sprint) | **Yes** | §5.I: scans clean of reachable Critical/High or explicitly excepted; CI scanning live | Scan outputs · exception register · CI job green |
| Repository Public-Release Sanitation | REQUIRED before any private→public visibility change | **Audit Clean** (Sprint 13, 2026-08-19: full-history read-only scan of 685 blobs across all commits/branches/tags → **zero real secrets ever committed**; the only credential-shaped strings are the CI container's throwaway DSN and doc/test placeholders. No rotation required; no history rewrite warranted or performed. Current-tree checklist passes; CI secret + dependency scanning now exist. **Publication remains a separate owner decision; the repository stays PRIVATE.** One non-secret note: the client dealership identity is present throughout — an owner disclosure decision, not a secret. Record: `SECURITY_AUDIT.md`) | 13 (within H's sprint) | **No — blocks repository publication only, not v1.1** | §5.H.1: full-history secret audit passes; every historical exposure rotated/revoked; current-tree checks pass; final re-scan clean | Audit report · rotation records · history-cleanup assessment · re-scan |
| J — Performance & Resilience | REQUIRED | **Verified** (Sprint 14 merged as PR #23 → `dev` = `c916208`, CI green on the merged head incl. the new bundle-budget gate; both DEV services restored to `dev` and verified serving the merge SHA (API `/health` release + bundle-baked SHA; Vercel auto-deployed on the Production-Branch push — no manual promote needed). **Merged-head deployed evidence 2026-08-20:** exactly ONE `/dashboard` request per role landing (both roles, live — the sprint's original duplicate-fetch finding closed); initial JS wire 169.2 kB compressed on a fresh fetch of the merged assets (Sprint 13 single-chunk baseline ≈ 256 kB gzip); deferred PostHog chunk loading with explicit events flowing and Sentry present; lazy Inventory Sync/Profile+User Management/Help chunks loading on nav; QA-scale search 3–9 ms/keystroke with the render caps correctly dormant; work-order generation exercised keyboard-only by both roles (pending state → one request → 227–269 ms); warm request band 104–293 ms after pool settle; zero console/CSP violations with the full lazy graph live. Production-scale behavior (bounded first-100/Show-all, newest-150/Show-older, 27–186 ms keystrokes at 1,197 rows, 0.033 s validation, sync_run growth eliminated) verified on the identical build against the production-shaped dataset during the review window and pinned by CI guards. Cold start measured and separated: 32.3 s and 52.3 s free-tier wakes (timed idle) vs ~3 ms warm server-side — platform band, documented, not an application defect. Full record: `PERFORMANCE.md` + `SPRINT_HISTORY.md`) | 14 | **Yes** | §5.J thresholds met at 4,700+ vehicle scale incl. slow-network behavior | Measurement report ✓ (`PERFORMANCE.md`) · fix PRs ✓ (#23) · CI gates ✓ · deployed smoke ✓
| K — Accessibility | REQUIRED (blocking subset — §5.K) | **Verified** (Sprint 14 merged as PR #23 → `dev` = `c916208`; both DEV services verified serving it. **Merged-head deployed evidence 2026-08-20, both roles (Manager + the owner's Lot Staff account), real key events:** first Tab on an authenticated fresh load reveals the skip link and Enter lands focus in `<main>`; visible focus throughout; onboarding replay is a true modal live (lazy chunk, focus entry, containment, step announcements, Escape=Skip, close returns focus to `<main>`); Vehicle Detail open/Escape focus cycles with truthful breadcrumbs on both roles; mobile drawer inert-when-closed → open-focuses-Close → Escape-returns-to-hamburger with `aria-expanded`; keyboard-focusable upload inputs with a visible focus ring; a zero-mutation validate-only pass announced its outcome live (`role=status`, Rejected verdict rendered, Run stayed disabled); phone-width Lot Staff flow and 640 px zoom-equivalent with zero horizontal overflow and zero sub-24px targets; signature 5.27:1 and sync-badge 6.92:1 measured from the merged stylesheet. axe: **0 violations on all five audited surfaces at production data shape** on the identical build (deployed-origin injection is blocked by our own CSP — recorded as a tooling constraint; supporting evidence only, no formal WCAG conformance claimed). The blocking subset passes on the core workflows; remainder tracked in `ACCESSIBILITY.md` §5 (SR-user study carried to Rail M). Full record: `ACCESSIBILITY.md` + `SPRINT_HISTORY.md`) | 14 | **Yes** (blocking subset) | Blocking subset passes on core workflows; remainder documented as tracked remediation | Audit checklist ✓ (`ACCESSIBILITY.md` §3) · fix PRs ✓ (#23) · DEV keyboard/contrast evidence ✓ (deployed, both roles)
| L — Privacy / Legal Readiness | REQUIRED ASSESSMENT (internal-beta subset blocks — §5.L) | **Merged — NOT Verified; Execution Pending** (Sprint 15 merged as **PR #25 → `dev` = `608dcaf`**, 2026-08-21; parents `daf5ae0` + `0e83425`; CI green on the merged head — both backend engines, frontend build + bundle budget, security scans; feature branch deleted both sides. **Verified waits on execution only:** D2 real monitored mailbox → owner-approved final text → D5 publication on `dealerdoh.com` before the v1.1 production cutover. Separately, **D4's tested implementation: MERGED + DEV-VERIFIED — production NOT activated** (**PR #27 merged 2026-08-25 as `dev` = `b3c35e1`**, CI green on the merged head; 7-day/30-day ratified windows, +20 boundary tests, 732/732; **deployed DEV review window PASSED 2026-08-25 on `52596d1`**: request-id-correlated `upload_retention_sweep` records live (scanned 0→1→1→2→3, all kept, zero deletions/errors — in-flight safety and counts-plus-server-timestamps-only logging proven; client filenames appear nowhere), all three `/run` outcome markers exercised through their exact unchanged 422/409 contracts, and the **kill-switch cycle live-proven**: `UPLOAD_RETENTION_SWEEP=disabled` → sweep silent, unknown value → fails closed, variable removed → default sweep returns; DEV env restored to its original 12 variables — no override remains. **Production still runs pre-D4 code; activation is governed by the hard 8-step Sprint 18 checklist in §5.L** (backup → deploy-with-kill-switch → verify → inspect legacy → explicit approval → one-time prune → remove switch → verify steady state); the legacy prune stays operator-gated per `DATA_RETENTION.md` §3). **The Sprint 15 merged-head no-cookie proof COMPLETED on deployed DEV 2026-08-25**: `document.cookie` empty (length 0) on a fresh load AND after authenticated navigation while PostHog is demonstrably active (`ph_phc_…` persistence in localStorage; deployed-bundle byte-check `persistence:'localStorage'` + `person_profiles:'identified_only'` with the key baked) — DealerDOH sets no cookies at all, live-confirmed. Original branch record follows —) (Sprint 15, 2026-08-20, branch `feature/sprint-15-privacy-legal`: audit-FIRST, then documents. Evidence-tagged privacy/data-flow inventory in **`PRIVACY_ARCHITECTURE.md`** (all 13 tables; **consumer-data boundary verified at the data-model level: no customer/consumer personal information is ingested by any current contract or persist path**, raw-upload verbatim-retention caveat recorded; workforce-data reality — no structured person names until the planned Sprint 17 contract, incidental vendor free-text = audit F2; browser-storage census MEASURED on deployed DEV + deployed-bundle telemetry-flag byte-check 2026-08-20; platform-layer IP/device metadata stated honestly; upload/output/file lifecycle; backups; internal incident-response procedure §10; minimization review). Retention record **`DATA_RETENTION.md`** (current behavior vs adopted v1.1 policy vs future requirement per artifact; the raw-upload indefinite-retention finding → owner decision **D4 — ratified 2026-08-21: 7-day accepted / 30-day rejected-or-HOLD bounded retention with deletion, never an indefinite default; implementation pending as the bounded retention remediation**; **no deletion behavior changed**; migration-plan retention decisions §17–18 carried through consistently). **`LEGAL_READINESS.md`** point-in-time assessment from authoritative sources (FTC Act §5 Applicable; A.R.S. §§ 18-551/552 breach frame incl. the 45-day/1,000-person mechanics; **GLBA/Safeguards stated carefully, non-categorically: the intended/validated flows do not appear to involve Safeguards "customer information" and DealerDOH does not currently appear to act as a Safeguards service provider for such information — retained raw uploads keep incidental receipt a live data-minimization risk, and the reassessment trigger covers receiving, retaining, maintaining, processing, or being permitted access to customer information**; Arizona: no enacted comprehensive consumer privacy law (SB 1815 introduced in the 2026 session, not enacted); CCPA/other-state/GDPR/COPPA/DPPA classified with rationale) + **owner decision register D1–D10** + **counsel register C1–C8**. Five customer-facing documents DRAFTED (`PRIVACY_POLICY.md`, `BETA_TERMS.md`, `ACCESSIBILITY_STATEMENT.md` strictly from Rail K's real results, `SECURITY_OVERVIEW.md`, `SUBPROCESSORS.md` — environment-honest incl. the GitHub not-a-subprocessor determination and the future email provider marked Planned) — every one marked **Draft — not in effect, not published** (banners carry the resolved-decision context and the D9 disposition), placeholders only where genuinely fill-at-publication (effective dates, the D2 contact), zero invented facts/entities/contacts. One evidence-backed remediation: PostHog `persistence: 'localStorage'` — the SDK default (`localStorage+cookie`) set the app's ONLY cookie (measured live); **DealerDOH now sets no cookies at all**, pinned in `tests/test_frontend_observability_config.py`. Suites 712/712 SQLite + 712/712 PostgreSQL on the branch; frontend build clean. **Owner decisions D1–D10 RESOLVED 2026-08-20** (D1 identity = "DealerDOH, operated by Kennett Ho," no entity implied; D2 real monitored dealerdoh.com contact to be created before publication, placeholders never published as real; D3 U.S.-only, initial controlled beta at an Arizona dealership; D4 raw uploads = temporary operational evidence — **7-day-accepted / 30-day-rejected-or-HOLD bounded retention RATIFIED 2026-08-21**, sweep design approved in principle (`DATA_RETENTION.md` §3); implementation pending, legacy production prune gated to the release/operator step (never at merge); D5 publication on dealerdoh.com — planned /privacy /terms /accessibility, /security if appropriate — before the v1.1 production cutover, never on current LotSync production; D6 notice-only acceptance for the employee beta, org-level contracts reassessed for v2; D7 customer-neutral public policies, drafts swept clean of the dealership name; D8 provider claims verified against actual plans pre-publication, tracked as manual release-readiness actions; **D9 recorded honestly: NO attorney review completed for the v1.1 controlled beta — documents are beta/evaluation readiness materials, qualified review recommended/required before commercial GA — this is the rail's owner-accepted-risk record**; D10 paid-Supabase = production-readiness decision, benefits verified before claimed). **Verified now gates on execution only: merge + merged-head CI, then D2's real mailbox + owner-approved final text + the D5 pre-cutover publication (§5.L exit 2)**; **D4's durations are ratified (2026-08-21); its tested cleanup implementation remains release-gating — before the v1.1 release train, checked at Sprint 18; the legacy production prune never runs at a merge**; the §5.L Sprint 17 delta rule stands untouched) | 15 | **Yes** (subset) | Data inventory accurate; internal-beta documents published; commercial items explicitly deferred with owner sign-off | Merged PR #25 ✓ (`608dcaf`) · CI green on merged head ✓ · Data-flow inventory ✓ · docs drafted, decisions D1–D10 resolved ✓ (publication pending D2/D5 execution before the v1.1 cutover) · deferral/risk record incl. the D9 owner-accepted-risk disposition ✓ (`LEGAL_READINESS.md` §5–§7) · deployed no-cookie proof ✓ (2026-08-25) · D4 implementation MERGED + DEV-verified ✓ (PR #27 → `b3c35e1`; review-window evidence in `SPRINT_HISTORY.md`) · publication ⏳ + D4 production activation via the §5.L Sprint 18 checklist ⏳ = the Verified/release gates |
| M — Human User Acceptance Testing | REQUIRED — **deferred from the v1.1 ship gate by explicit owner waiver 2026-08-25 (§11); required before v1.5 commercial pilot readiness** | **Human Verification Pending — deferred from v1.1 release gate by owner decision; required before v1.5 pilot readiness** — evidence state preserved: UAT package and DEV preflight complete (Sprint 16, 2026-08-25: methodology + moderator script + findings log canonical — `UAT_PLAN.md` / `UAT_SCRIPT.md` / `UAT_FINDINGS.md`, merged PR #29 → `dev` = `bd1e72a` = **the canonical session SHA**, both DEV services byte-verified serving it; **DEV preflight PASSED** (`UAT_PLAN.md` Appendix A) — no pre-UAT blocker; the findings log is deliberately empty. **Human sessions deliberately deferred by owner decision 2026-08-25** — representative Manager/Admin + Lot Staff participants are unavailable until the pre-pilot / pilot-readiness window; this is an owner scheduling decision, not a technical blocker. **Automated QA is not and will not be substituted for human evidence**; the exit conditions in §5.M stand unchanged and still require real sessions before any Verified disposition. Un-parked by: owner conducts sessions per the launch packet against `bd1e72a` — or re-preflight against the then-current candidate if `dev` has materially moved — and supplies raw observations for Phase 4 processing) | 16 (human window: pre-v1.5) | **Waived for v1.1 (owner, 2026-08-25 — §11); blocks v1.5 pilot readiness** | Manager + Lot Staff UAT complete; all release-blocker findings fixed and re-verified — criteria unchanged by the waiver | UAT session notes · blocker list dispositions · re-test evidence · package + preflight ✓ (PR #29, `bd1e72a`) · human sessions ⏳ (v1.5 readiness gate, §11) |
| Production migration (Releases A–C) | REQUIRED | **Rehearsed** (Sprint 07 PASS — not executed) | RC/cutover (18) | **Yes** | Runbook executes at cutover; Sprint 18 re-verification confirms rehearsal assumptions still hold | `PRODUCTION_MIGRATION_REHEARSAL.md` · refreshed rehearsal if drift · runbook completion record |
| Automated Report Ingestion — Keyper Scheduled All Vehicles | **CONDITIONAL — TRIGGERED / owner-opted into v1.1** (§6.2, 2026-08-18) | Planned | 17 | **Yes — now that the rail has entered v1.1** | Configured dealership receives, deduplicates, validates, HOLDs or safely processes Keyper Full evidence through the Rail D boundary | Vendor evidence · merged PR · dual-engine CI · DEV acquisition/replay/HOLD smoke · observability evidence · H/I/J/L/M delta-gate evidence |

Register statuses used: Planned · Discovery · In Progress ·
Implementation Complete — Awaiting Merge · Verified · Deferred · N/A.
Rows move to Verified only with the evidence in §4. The migration rail
remains deliberately "Rehearsed," not Verified, because rehearsal ≠
production execution.

---

## 2. Classification Summary

**REQUIRED (blocks v1.1.0-beta.1):** A, B, C, D, F, G, H, I, J,
K (blocking subset), L (internal-beta subset), M, and the production
migration itself.

**CONDITIONAL (§6):** E (Notifications) remains untriggered pending
the Sprint 17/18 checkpoint in §6.1. Automated Report Ingestion began
as conditional; its Keyper scheduled-report trigger is now satisfied
and the owner explicitly opted the bounded Keyper adapter into v1.1
as planned Sprint 17 scope. Once entered, its exit conditions block
release.

**POST-v1.1 (explicitly out, cannot silently re-enter — §7):** MFA,
enterprise SSO, advanced user administration, SMS/push/Slack/digest
notifications, notification preferences, session replay (pending
privacy review), RLS, full per-row store scoping (Store #2 trigger),
generic webhooks beyond Sprint 17's inbound-email provider callback,
AI-assistant tooling, GLBA-regulated data handling, public
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
  `report_baseline` comparisons, migration 0010). **Thresholds
  OWNER-RATIFIED 2026-08-16 as the initial beta policy, subject to
  tuning from real operational evidence:** warn on decrease >15% AND
  ≥10 rows; warn on increase >50% AND ≥25 rows (grounding:
  `INGESTION_ARCHITECTURE.md` §8). Warning/review thresholds, never
  hard rejection; explicit Manager/Admin acknowledgement required;
  future unattended ingestion HOLDs on them.
- *Exit 4 (wrong type / Keyper) — evidence status corrected by the
  owner 2026-08-16:* the known **Keyper Full Inventory contract:
  PASS.** **Unsupported/nonmatching Keyper-shaped evidence fails
  safely: PASS** (rejected explicitly, never a snapshot; synthetic
  stand-in — no real Event sample exists and none was invented).
  **The actual Keyper Event-vs-Full structural distinction: PENDING
  VENDOR EVIDENCE** — a real Event report could plausibly satisfy
  the current Full signature, and that cannot be proven or disproven
  without the vendor format (`INGESTION_ARCHITECTURE.md` §6). Keyper
  Event ingestion: unsupported, not required for v1.1. This pending
  item is why the sprint's post-merge state is **Implementation
  Paused — Awaiting Vendor Evidence** rather than Complete.
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

**Current state: `Audit Clean`** (Sprint 13, 2026-08-19 — a full
read-only history scan of every reachable blob was performed and found
**no real secret ever committed**; the only credential-shaped strings
are the CI PostgreSQL container's throwaway DSN and documentation/test
placeholders. No historical exposure exists, so no credential requires
rotation and no Git-history rewrite is warranted or has been performed.
The current-tree checklist passes and CI secret/dependency scanning now
exists. This clears the **secret** blocker only — actual publication
remains a separate owner decision, the repository stays PRIVATE, and a
non-secret disclosure (the client dealership identity is present
throughout the repository) is an owner-awareness item to weigh before
any publication. Full record: `SECURITY_AUDIT.md`.)

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

**Sprint 17 delta rule:** because inbound email, a new provider,
attachments, routing metadata, retention/retry state, and additional
Keyper actor/context fields enter after Sprint 15, Sprint 17 must amend
the data-flow/subprocessor/retention inventory and any affected
internal-beta documents. Sprint 18 must verify the delta; Rail L
evidence cannot be treated as final while the new acquisition path is
missing from it.

**D4 production-activation checklist (owner-ratified 2026-08-25 —
a HARD Sprint 18 release-readiness item; `/release-readiness` cannot
pass while any step is unrecorded).** The D4 bounded-retention
implementation is merged and DEV-verified (PR #27), but production
activation is a distinct, operator-gated event because the first
enabled sweep in production would prune the accumulated legacy
upload backlog on its own. The release train must execute, in
order, with evidence for each step:
1. Production backup taken and verified (existing procedure,
   `PRODUCTION_BASELINE.md`).
2. `UPLOAD_RETENTION_SWEEP=disabled` present on the production
   service **before** the first deployment that contains the D4
   code.
3. Production deployment verified serving the release SHA **with
   the sweep disabled** (no `upload_retention_sweep` records).
4. Legacy upload population inspected (`/var/data/api_uploads`
   count/age/size) and recorded.
5. Explicit operator approval recorded for the one-time legacy
   prune.
6. The approved prune executed and verified (before/after
   population recorded).
7. The `UPLOAD_RETENTION_SWEEP` variable removed.
8. Steady-state retention verified active (an
   `upload_retention_sweep` record observed with expected counts).
Every mechanism in steps 2–3 and 7–8 was live-proven on DEV during
the PR #27 review window (set honored / unknown value fails closed /
removal restores the default) — see `DATA_RETENTION.md` §3 and
`SPRINT_HISTORY.md`.

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

**v1.1 ship-gate deferral (owner decision 2026-08-25 — §11):** this
rail is **deferred from the v1.1 ship gate by explicit owner
waiver**. Rationale: representative dealership participants are
unavailable until the pre-pilot window, and v1.1 is redefined as a
controlled technical/internal beta, not the commercial pilot
candidate. **Nothing above is weakened**: the exit conditions stand
verbatim, the rail cannot be marked Verified/Complete/Passed without
real human evidence, and it **blocks v1.5 Commercial Pilot Candidate
readiness** (§11). The Sprint 16 UAT package, launch packet,
preflight evidence, session criteria, and deliberately-empty
findings log remain canonical; the human window re-preflights
against the then-current candidate if `dev` has materially moved
since session SHA `bd1e72a`.

**Sprint 17 delta rule:** Sprint 16 remains the full uncoached product
UAT. Any new Sprint 17 human surface — especially HOLD review/resume,
freshness/staleness, or newly surfaced Keyper work — requires targeted
human re-verification or an explicitly approved real-world pilot, not
a silent assumption that earlier UAT covered it. **Timing amended with
the 2026-08-25 waiver:** this human re-verification joins the same
deferred window and gates **v1.5 pilot readiness** (§11) rather than
the compressed v1.1 Sprint 18 gate; the requirement itself is
unchanged.

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

**Owner scope amendment (2026-08-18):** Keyper scheduled-report
acquisition has entered v1.1 as planned Sprint 17 scope (§6.2). The
owner explicitly kept Notifications **CONDITIONAL** rather than
automatically promoting it. Sprint 17 implementation and Sprint 18
readiness must instead run a recorded checkpoint against the real
unattended failure/HOLD experience.

**Triggers (any one fires the rail into scope):**
1. After Sprint 17 implementation / during Sprint 18 readiness, real
   evidence shows that scheduled-report non-arrival, acquisition
   failure, validation ERROR, validation WARNING/HOLD, stale evidence,
   or repeated ingestion failure cannot reliably reach a responsible
   human through the implemented operational surfaces → REQUIRED,
   scoped minimal: in-app center, unread/read, timestamp, deep link,
   mark-read, retention.
2. Rail M UAT demonstrates users miss operationally significant
   conditions the existing surfaces don't carry → REQUIRED at the
   UAT-blocker level.
3. Owner explicitly opts it in (Scope Discipline rule 5).

If triggered, scope and scheduling must be explicitly added before
Sprint 18 can pass; it is not silently absorbed into Sprint 17. The
POST-v1.1 exclusions stay excluded (no SMS/push/Slack/digests/
preferences). Sprint 12.5 remains the historical placeholder for an
earlier trigger; the Sprint 17/18 checkpoint is the operative one now.

### 6.2 Automated Report Ingestion (**CONDITIONAL TRIGGER SATISFIED — Planned Sprint 17**)

**Owner scope decision (2026-08-18):** dealership discovery confirmed
that Keyper supports scheduled delivery of the **All Vehicles / Full
Inventory** snapshot; the implementation is bounded to that one
high-value source; and the owner opted it into v1.1. The rail therefore
retains its conditional origin but is now **Planned**, assigned to
Sprint 17, and blocks release once entered. The detailed plan of record
is [`KEYPER_AUTOMATED_INTEGRATION_PLAN.md`](KEYPER_AUTOMATED_INTEGRATION_PLAN.md).

**Sprint 17 exit conditions:**

1. A configured dealership can receive a scheduled Keyper All
   Vehicles attachment through an authenticated inbound-email
   provider callback and resolve the expected dealership/source
   without treating recipient, sender, subject, or filename as
   evidence truth.
2. Provider message ID plus SHA-256 attachment fingerprint provide
   replay-safe deduplication and idempotency.
3. Attachment type/size and recipient/source rules fail safely;
   unknown recipients are acknowledged and recorded as unsupported,
   not assumed malicious.
4. Every attachment passes through the existing Rail D classifier,
   validator, fingerprint, baseline, and reconciliation safeguards —
   no second ingestion path.
5. Unattended ERROR rejects with no operational mutation; WARNING
   always HOLDs for human review and is never auto-acknowledged; clean
   evidence is eligible for automated processing under the final
   v1.1 policy.
6. Keyper Full contract v1 retains the grounded custody, location,
   registration/removal, actor, and display context defined in the
   Sprint 17 plan without making Keyper globally authoritative over
   Tekion.
7. Cross-system exceptions produce explainable work while reusing the
   existing checked-out-key workflow wherever it already represents
   the condition.
8. Acquisition/processing states are covered by Sprint 11 structured
   logs, correlation, Sentry, PostHog, and the telemetry census with
   the existing redaction boundary intact.
9. Source freshness distinguishes Fresh / Aging / Stale /
   Missing-never-received; stale evidence is never treated as current.
10. Dual-engine tests, adversarial webhook/replay tests, real deployed
    DEV verification, and any explicitly approved Mark Kia pilot pass.
11. Targeted security/supply-chain, privacy/legal, performance/
    resilience, and human-workflow delta reviews re-open and refresh
    the affected earlier-rail evidence before Sprint 18.

**Activation dependency:** the scheduled Full snapshot is the v1.1
target; Keyper Event ingestion remains out of scope. Sprint 17 may be
designed and built while Rail D awaits evidence, but unattended Keyper
processing cannot be activated or this rail marked Verified until a
real Event sample proves the Full-vs-Event structural distinction (or
the classifier is corrected from that evidence). Rail D remains
**Merged — NOT Verified; Awaiting Vendor Evidence** until its own exit
condition is satisfied.

**Remaining discovery checklist (owner/vendor evidence, not guessed
code):**
- **Tekion:** scheduled email capability? which report types?
  snapshot vs delta? frequency? attachment format? sender/subject/
  filename stability? export completeness behavior?
- **Keyper:** scheduled All Vehicles / Full Inventory delivery is
  confirmed. Obtain representative delivered-message + attachment
  evidence, exact cadence, sender/provider details, and the real Key
  Event sample needed for Full-vs-Event discrimination.
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
| Generic webhooks beyond Sprint 17 | First additional inbound/outbound third-party webhook | Dedicated scope with authentication/signature verification, replay protection, idempotency; Sprint 17's email-provider callback is governed by §6.2 |
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
| `CHANGELOG.md` stale (ends v0.7.4) | Open — documentation debt | No | Release-notes work at RC freeze (Sprint 18); full backfill POST-v1.1 |
| Keyper scheduled-report acquisition | **Planned — conditional trigger satisfied / owner opted into v1.1** | **Yes, once entered** | Sprint 17 (§6.2; `KEYPER_AUTOMATED_INTEGRATION_PLAN.md`) |
| Keyper Event-vs-Full structural evidence | **PENDING VENDOR EVIDENCE** | **Yes — blocks Rail D verification and unattended Keyper activation** | Real Event sample; resolve through Sprint 10/Rail D evidence path before Sprint 17 verification |
| Privacy/legal docs don't exist yet | Planned | **Yes, via Rail L** subset | Sprint 15 |
| Migration-tool schema drift | Standing guard | Contextual | Any sprint that adds migration 0010+ must update `tools/migrate_sqlite_to_postgres.py`'s expectations (`EXPECTED_SCHEMA_VERSION`, tables/order) and its tests, and note it for the RC-freeze rehearsal refresh |
| `SPRINT_HISTORY.md` canonicalization | Resolved this sprint | — | Landed in-repo (Sprint 08); rolling-update procedure applies from here |

---

## 9. Current Sprint Order (Sprint 08 base; owner-amended 2026-08-18)

**Current release train — 10 sprints to RC, then cutover:**

| # | Sprint | Rails | Why here |
|---|---|---|---|
| 09 | Account Lifecycle & Settings | A (incl. the REQUIRED `vercel.json` SPA rewrite — owner decision 2026-08-16) | Identity is the foundation every later rail's testing logs in through; smallest-dependency start |
| 10 | Inventory Ingestion Safety | D | **Kept early on purpose:** bad input silently corrupting operational truth outranks UX polish; also defines the seam §6.2 would reuse |
| 11 | Observability & Structured Logging | F + G | **Moved up from the provisional 13 (ratified by owner 2026-08-16):** instrument *before* building the big UX surfaces so the tutorial/help/sync flows ship with events built in (not retrofitted), Sentry watches the UX sprint's own QA, the security audit (13) can audit real telemetry redaction, and UAT (16) runs fully observed |
| 12 | Role-Aware UX + Onboarding/Help | C + B (+ §8 UX findings) | The two UX rails are one coherent build; lands instrumented (11) and validated against safe ingestion (10) |
| 12.5 | *Notifications — only if triggered* | E | §6.1 |
| 13 | Security Hardening + Supply Chain | H + I + Repository Public-Release Sanitation audit (§5.H.1 — gates repo visibility, not v1.1) | Audits the finished auth/ingestion/UX/telemetry surface once, not twice; folds I and the history audit into the same evidence pass |
| 14 | Performance + Accessibility | J + K | After features stabilize so measurements and audits hit the real product; shared browser-audit tooling |
| 15 | Privacy / Legal Readiness | L | Establishes the pre-acquisition data-flow/legal baseline; Sprint 17 must add its provider/attachment/retention delta before Sprint 18 |
| 16 | Human UAT | M | Full uncoached core-product UAT; Sprint 17 must target-reverify any new HOLD/freshness/Keyper-work surface it adds. **2026-08-25: parked at the human-testing gate (package + preflight complete) and deferred from the v1.1 ship gate by owner waiver — human window moves to v1.5 pilot readiness (§11)** |
| 17 | Vendor Integration & Automated Evidence Acquisition | Automated Report Ingestion (§6.2; conditional trigger satisfied) | Keyper Scheduled All Vehicles is the first bounded unattended source; it reuses the Sprint 10 safety boundary and Sprint 11 observability, then refreshes the affected security/privacy/performance/UAT evidence because it lands after those sprints |
| 18 | **v1.1 Release Gate / Production Cutover Readiness (compressed — owner redefinition 2026-08-25, §11)** | Migration rail + `/release-readiness` | **A release gate, not a feature sprint**: only the minimum evidence-backed checks and operator actions to ship v1.1 as a controlled beta — the §11 A–I gate (exact RC SHA + scope freeze; production backup/rollback; production architecture/provider verification; Rail L D2/D5 execution; the §5.L D4 8-step production activation; proportional auth/security/privacy production smoke; migration/data integrity; explicit known-limitations register; final owner GO/NO-GO). No new feature development unless required to resolve a true release blocker. Supersedes the broader RC-hardening description for v1.1 |

**Changes from the provisional Sprint 09–18 plan, with reasons:**
1. **Observability moved from 13 → 11** (rationale above — the
   single highest-leverage reorder).
2. **Notifications removed from the required path** (provisional 12)
   → conditional slot 12.5 (§6.1 decision).
3. **Dependency/supply-chain folded into the security sprint**
   (was implicit) — one security evidence pass.
4. Sprint 08's original net was **10 sprints → 9** to RC freeze
   without dropping any REQUIRED rail.
5. `SPRINT_HISTORY.md`'s older draft order (10=UX, 11=Ingestion) is
   superseded by ingestion-first — matching the Sprint 08
   specification's own reasoning ("bad input can silently create
   false operational truth").
6. **Owner amendment 2026-08-18:** Keyper scheduled All Vehicles
   satisfied the bounded automated-ingestion trigger. A dedicated
   planned Sprint 17 was added; RC Freeze moved 17 → 18. No unrelated
   vendor automation entered scope.
7. **Owner amendment 2026-08-25 (§11):** v1.1 redefined as a
   controlled technical/internal beta; Rail M deferred from the v1.1
   ship gate by explicit owner waiver (required before v1.5 pilot
   readiness, unweakened); Sprint 18 redefined as the compressed
   v1.1 release gate. Sequencing change only — no evidence rule
   weakened, nothing marked Verified without evidence.

Sequencing rule: a sprint may start only when the rails it depends
on are Verified or the dependency is explicitly waived by the owner.
Sprint 17 planning/implementation may begin with Rail D still open, but
it cannot activate unattended Keyper processing or become Verified
until the real Event-vs-Full evidence closes that dependency. Because
Sprint 17 follows H/I, L, and M, it must perform targeted delta review
instead of assuming those earlier results cover its new surface.
**Under the 2026-08-25 amendment, Rail M may remain Human
Verification Pending for the v1.1 controlled beta release under the
explicit owner waiver, but must be completed before v1.5 commercial
pilot readiness (§11); Sprint 17's human-surface delta joins that
same v1.5 window.**

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
   fixed and re-verified (5.M). **Deferred from the v1.1 gate by
   owner waiver 2026-08-25 (§11): ships as Human Verification
   Pending in the controlled beta; blocks v1.5 pilot readiness,
   criteria unweakened.**
9. **Automated Keyper evidence** — configured acquisition is
   authenticated, deduplicated, observable, freshness-aware, and
   still governed by the Rail D Accept/HOLD/Reject boundary (§6.2).
10. **Final `/release-readiness`** — all in-scope register rows
   Verified **or carrying an explicit, dated owner-waived deferral
   recorded in this register (§11 known-limitations register — no
   limitation is silently converted to Verified)**, the
   Notifications checkpoint recorded, scope frozen, migration
   assumptions re-confirmed → the Sprint 06/07 runbook executes as
   Releases A–C at the owner-approved window.

---

## 11. v1.1 Release Posture Amendment, Version Staging & the v1.5 Pilot Readiness Gate (owner decision 2026-08-25)

**Owner decision, recorded per the header amendment rule:** v1.1 is
**a controlled technical/internal beta release — not the commercial
pilot candidate and not the human-validated commercial release.**
Human UAT remains required for commercial pilot readiness but is no
longer a hard blocker to shipping v1.1 as a controlled beta. This is
a sequencing change only: no UAT requirement is weakened, Rail M is
never marked Verified/Complete/Passed without real human evidence,
and nothing is fabricated.

**v1.1 release posture:** `Controlled Beta — Human Validation
Deferred to v1.5 Readiness`.

### 11.1 Compressed Sprint 18 — the v1.1 release gate (A–I)

Sprint 18 is a **release gate, not a feature sprint**: only the
minimum evidence-backed checks and operator actions required to
safely ship v1.1 as a controlled beta. No new feature development
unless required to resolve a true release blocker.

- **A. Exact release candidate** — identify the exact `dev` SHA to
  ship; freeze meaningful scope; merged-head CI green; no unresolved
  release-blocking regression; clean branch/repository state.
- **B. Production backup and rollback** — fresh verified production
  backup; rollback procedure confirmed; migration/rollback steps
  reconciled to the exact RC; no reliance on stale rehearsal
  evidence where the runtime path changed.
- **C. Production architecture / provider verification** — verify
  the actual production configuration being activated: frontend,
  backend, database, auth, provider plans, regions where relevant,
  account ownership/access, 2FA where intended, backups where relied
  upon, monitoring/telemetry configuration, production environment
  variables/secrets, production origins/domains. No unsupported
  provider claims (owner D8 discipline).
- **D. Rail L execution items** — complete or explicitly gate the
  remaining Sprint 15 execution items before cutover: **D2** create
  and verify the real monitored `@dealerdoh.com` support/privacy
  contact; **D5** publish the approved legal/privacy materials on
  `dealerdoh.com` as applicable — final text reconciled to actual
  production behavior first; never publish stale or inaccurate
  drafts.
- **E. D4 production activation** — execute the hard owner-approved
  8-step sequence exactly as recorded in §5.L (backup →
  `UPLOAD_RETENTION_SWEEP=disabled` before the first D4 deployment →
  verify disabled → inspect legacy population → explicit operator
  approval → execute + verify the one-time prune → remove the
  kill-switch → verify steady-state retention). Never weakened,
  never silently bypassed.
- **F. Auth / security / privacy production smoke** — proportional:
  authentication; role/membership enforcement; signup/invite posture
  matches intent; deactivation; role-gated UI/API; no-cookie posture
  where applicable; telemetry/redaction posture; production docs
  disabled; security headers/origin behavior; no sensitive-logging
  regression; D4 steady state after activation.
- **G. Migration / data integrity** — migration from the current
  production shape; row/entity-count or equivalent integrity
  evidence; representative vehicle/task/event histories; no silent
  loss; no accidental duplication; production source files/disk
  assets protected; rollback remains possible.
- **H. Known limitations / accepted risks** — an explicit register:
  unresolved vendor-evidence limitations; Rail D state; the Rail M
  human-verification deferral; non-commercial beta limitations;
  provider/backup/support limitations; operational caveats. **No
  limitation may be silently converted into "Verified."**
- **I. Final owner GO/NO-GO** — before any merge/release to
  `master`, stop at an explicit owner approval gate reporting: exact
  RC SHA; rails Verified / deferred / blocked-limited; accepted
  risks; production steps; rollback plan; legal/privacy publication
  state; D4 activation state; and a recommendation of GO / GO WITH
  ACCEPTED LIMITATIONS / NO-GO. **No merge to `master` without
  owner approval.**

### 11.2 Version staging (roadmap semantics)

| Version | Stage |
|---|---|
| **v1.1** | Controlled technical/internal beta — move the DealerDOH foundation into production safely, prove production architecture, continue internal/controlled operational use; **not presented as commercially validated** |
| **v1.2** | Multi-rooftop / tenant foundation |
| **v1.3** | Organization/customer identity and configuration |
| **v1.4** | Sales Operations expansion |
| **v1.4.5** | Commercial pilot preparation |
| **v1.5** | **Commercial Pilot Candidate — human UAT / commercial pilot readiness mandatory by this point** |

### 11.3 v1.5 Commercial Pilot Readiness Gate (the deferred human validation — NOT waived)

Before v1.5 may be called `Commercial Pilot Candidate`, all of the
following must occur. This requirement is moved from *v1.1 ship
blocker* to *v1.5 commercial pilot blocker* — it is not waived and
may not erode:

1. Representative **Manager/Admin** human UAT conducted.
2. Representative **Lot Staff** human UAT conducted.
3. Any new material Sales-facing workflows tested with appropriate
   users.
4. Sprint 17 / new acquisition human surfaces (HOLD review/resume,
   freshness, Keyper work) included in the re-preflight/UAT where
   applicable.
5. No unresolved human blocker.
6. Severe UAT issues resolved or explicitly accepted by the owner
   with rationale.
7. `UAT_EXIT_REPORT.md` completed.
8. **Rail M receives its real, evidence-backed final disposition**
   (§5.M criteria verbatim; the Sprint 16 package/launch
   packet/preflight remain the canonical starting point, re-run
   against the actual v1.5 candidate).
9. The pilot environment is re-preflighted against the actual v1.5
   candidate.

---

*This register supersedes all prior informal v1.1 scope lists.
`SPRINT_HISTORY.md` §"Proposed v1.1.0-beta Sprint Roadmap" remains as
historical context; scope and order are governed here. Amendments
follow §3 only.*
