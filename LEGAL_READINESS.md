# DealerDOH Legal Readiness — v1.1 Assessment

**Point-in-time.** Sprint 15 (Rail L) assessment performed
2026-08-20 against the verified product reality in
[`PRIVACY_ARCHITECTURE.md`](PRIVACY_ARCHITECTURE.md). This document
organizes facts and questions so that owner decisions are explicit
and future counsel review is efficient. **It is not legal advice,
makes no legal-sufficiency claim, and creates no compliance
representation** — exactly per the rail contract
(`V1_1_RELEASE_READINESS.md` §5.L: "this register makes no
legal-sufficiency claims").

**Source discipline.** Each statement is labeled: **[repo]**
repository fact · **[provider]** provider documentation ·
**[research]** legal research from the cited authority (as-of
2026-08-20) · **[decision]** owner policy decision ·
**[counsel]** question reserved for qualified counsel.

---

## 1. Product reality the law is being assessed against

- One internal dealership deployment (Mark Kia, Arizona-based
  operation — confirm under D3), operated by the product owner;
  users are dealership staff, onboarded by invite only [repo].
- Data processed: vehicle operational data; workforce *app
  identities* (email/password at Supabase Auth, display name,
  role/store membership); incidental vendor free-text; bounded
  product telemetry. **No consumer/customer personal information of
  any kind** — verified, with the raw-upload caveat recorded
  [`PRIVACY_ARCHITECTURE.md` §2.3] [repo].
- No sale of data, no advertising use, no cross-context behavioral
  advertising, no data monetization of any kind [repo: telemetry
  posture + no such code path exists].
- Not directed to children; a workforce operations tool [repo].
- US-only operation; providers currently configured in US regions
  (Render Oregon, Supabase us-west-2, PostHog US cloud) [repo/
  provider] — configuration fact, not a contractual residency
  guarantee.

## 2. The universal baseline that already applies

**FTC Act §5 (unfair or deceptive acts or practices) —
APPLICABLE.** [research: FTC] The one obligation no threshold
gates: whatever DealerDOH publishes about its privacy and security
must be true, and material omissions can be deceptive. This is the
legal reason for this sprint's entire method — every claim in every
draft traces to a verified fact, and the drafts promise nothing the
product does not do. It is also why the drafts avoid: certification
claims, uptime promises, encryption guarantees, deletion timelines
without operational backing, and "we never collect IP addresses"
(false at the platform layer).

## 3. Applicability assessment by area

| # | Legal area | Classification | Grounding |
|---|---|---|---|
| 1 | FTC Act §5 — truthful privacy/security claims | **Applicable** | §2 above [research: ftc.gov] |
| 2 | Arizona breach notification, A.R.S. §§ 18-551/18-552 | **Applicable** (as the frame for a future incident) | AZ residents' "personal information" includes first-initial/name + specified elements AND **email/username + password** permitting online-account access — the Supabase Auth identity set is exactly that shape once real staff onboard. 45 days to notify individuals after determination; >1,000 individuals adds AZ AG, AZ DHS, and the three CRAs. GLBA-regulated entities and HIPAA entities follow their federal regimes instead — whether that carve-out reaches a given DealerDOH incident is case-specific [research: azleg.gov/ars/18/00552.htm; azag.gov breach FAQ, 2026-08-20]. Incident procedure: `PRIVACY_ARCHITECTURE.md` §10. No statutory timeline is pre-promised in any draft |
| 3 | Arizona comprehensive consumer privacy law | **Not currently enacted** — watch item | No comprehensive AZ privacy statute as of 2026-08; SB 1815 (2026 session) introduced but not passed [research: azleg tracking via legislative-status summaries, 2026-08-20]. Re-check each session |
| 4 | GLBA / FTC Safeguards Rule (16 CFR Part 314) | **Triggered Only If Scope Expands** | Full analysis in §4 below |
| 5 | CCPA/CPRA (California) | **Likely Not Applicable** | Thresholds (any one): >$26,625,000 annual gross revenue; buy/sell/share personal information of >100,000 CA consumers/households; >50% revenue from selling/sharing. None is met or approached; DealerDOH is not doing business in California, sells nothing, shares nothing for advertising [research: cppa.ca.gov threshold adjustment; statute summaries, 2026-08-20]. Note for the trigger: California's law covers workforce data, so a future CA-scale posture change would pull employee data in scope |
| 6 | Other state comprehensive privacy laws (~20 enacted) | **Triggered Only If Scope Expands** | Each has its own jurisdiction + volume thresholds far above current scale; most (unlike CA) also exempt B2B/employee data. A multi-state customer footprint is the trigger for a per-state pass [research: multistate tracking summaries, 2026-08-20] [counsel: C3] |
| 7 | GDPR / international regimes | **Likely Not Applicable** | No EU establishment, no offering to or monitoring of EU data subjects. Trigger: any EU/UK/CA-Canada customer or user. Do not design for it prematurely [research: Art. 3 territorial scope, general knowledge — re-verify at trigger] |
| 8 | COPPA | **Likely Not Applicable** | A dealership workforce operations tool is not directed to children and has no reason to collect data from anyone under 13. Scope stated accurately in drafts; no COPPA controls built [research: 16 CFR Part 312 scope] |
| 9 | Workforce/employee privacy (AZ + federal) | **Applicable as practice; thin statutory surface today** | No AZ comprehensive workforce-privacy statute; the operative duties are honesty (§2), the breach statute (row 2), and provider-account hygiene. The product's posture is already conservative: no monitoring features, no session replay, no keystroke/DOM capture, telemetry identity is an internal UUID [repo]. Trigger for counsel: any future monitoring-shaped feature (replay, productivity analytics) [counsel: C6] |
| 10 | DPPA (Driver's Privacy Protection Act) | **Likely Not Applicable** | DealerDOH ingests no DMV/motor-vehicle-record data; VINs come from the dealership's own inventory systems and are not linked to registered owners [repo] |
| 11 | CAN-SPAM / TCPA | **Likely Not Applicable** | Only transactional auth email exists (invites, password recovery, via Supabase); no marketing email, no SMS/calls [repo]. Trigger: any marketing communication feature |
| 12 | HIPAA | **Not Applicable** | No health data, no covered-entity relationship [repo] |
| 13 | PCI DSS | **Not Applicable** | No payment-card data anywhere [repo] |

## 4. GLBA / Safeguards Rule — the careful one

**Facts [research: ftc.gov "Automobile Dealers and the FTC's
Safeguards Rule" FAQ; ecfr.gov 16 CFR Part 314, 2026-08-20]:**
dealerships that arrange financing or leasing are "financial
institutions" under the Rule. A financial institution must, among
its program elements, oversee **service providers** — defined by
their **access to customer information** (nonpublic personal
information about *consumers*) — including contractual safeguards
requirements (16 CFR § 314.4(f)) and, since the 2023 amendment,
notify the FTC of qualifying breaches involving ≥500 consumers.

**Current-scope conclusion (precise, no compliance claim):**
DealerDOH today stores and accesses **no customer information** in
the Rule's sense — no consumer financial data, no financing/deal
records, no consumer identities at all
[`PRIVACY_ARCHITECTURE.md` §2.3, verified]. On these facts,
DealerDOH is **not currently within the dealership's
Safeguards-Rule service-provider-oversight perimeter**, because
that perimeter is defined by access to customer information. Mark
Kia's own Safeguards obligations for its own systems (its DMS, its
F&I tools) are the dealership's, and DealerDOH neither discharges
nor interferes with them.

**What must never be claimed:** "DealerDOH is GLBA compliant"
(meaningless and false — the Rule's program obligations attach to
the financial institution, and no assessment has been performed) and
"GLBA can never apply" (false — one scope change flips the
analysis).

**Recorded trigger:** if DealerDOH ever ingests financing
applications, deal jackets, consumer credit data, consumer contact
records, CRM data, payment data, or any consumer NPI — or connects
to a DMS in a way that grants such access — then **before**
implementation: reassess Safeguards service-provider status, expect
contractual safeguards obligations from the dealership under
§ 314.4(f), and take the question to counsel [counsel: C4]. The
same trigger is recorded in `PRIVACY_ARCHITECTURE.md` §2.3 and the
back-burner register (`V1_1_RELEASE_READINESS.md` §7 "Formal GLBA
posture").

## 5. Owner decision register (unresolved — blocking marked ✋)

| # | Decision | Why it matters | Recommendation (owner may differ) |
|---|---|---|---|
| D1 ✋ | **Operating identity in published documents** — what legal name/entity appears ("DealerDOH" is a product name; no entity is claimed anywhere). Is there an LLC/sole-proprietor identity to name? | Policies must name a responsible party truthfully; drafts carry `[OWNER: operating name]` | If no entity exists yet, publish under the owner's real operating identity; form an entity before commercial GA (C1) |
| D2 ✋ | **Support / privacy / security contact** — a real, monitored address (Rail L exit 2 requires a support/security contact). `dealerdoh.com` is owned; no mailbox exists | Every draft's contact section is a placeholder until this exists; publishing with a dead or fake address violates the sprint's own rules | One monitored address (e.g. on the owned domain) for all three roles at beta scale; set up before publication |
| D3 | **Jurisdiction statement** — confirm the operating state for the Beta Terms' governing-law line (drafts assume Arizona; not yet owner-confirmed) | Governing law/venue in Terms; which breach statute leads the incident frame | Arizona, per operating reality; confirm |
| D4 | **Raw-upload retention** — `DATA_RETENTION.md` §3 options A (status quo, revisit at Sprint 17) or B (bounded cleanup, N from evidence) | The one unbounded personal-data-adjacent store on the production disk | A for v1.1 (Sprint 17 must redesign acquisition retention anyway); schedule an operator prune pass |
| D5 ✋ | **Publication venue + timing** for the internal-beta set (in-app Help section? repo? dealerdoh.com pages?) — coupled to the v1.1 release train, since the docs describe the v1.1 stack | Rail L exit 2 says *published*; Phase 31 defers UI surfaces until approval state is clear | Publish in-app (Help → "Legal & Privacy") at the release train; no production copy changes before that train |
| D6 | **Acceptance mechanics** — notice-only vs. click-acceptance for Beta Terms | Phase 33 assessment: internal beta with employer-directed users does not need clickwrap; v2 commercial onboarding will need org-level contractual acceptance | Notice-only for v1.1 (links visible at sign-in/Help); record the v2 trigger |
| D7 | **Dealership name in published copy** — does "Mark Kia" appear, or generic "your dealership"? (Echoes security F8) | Customer-identity disclosure is an owner call | Generic wording in all published documents |
| D8 | **Provider plan verification at publication** — Sentry org plan (30 vs 90-day retention), PostHog plan, Vercel plan | Retention numbers in published copy must match the actual plans | Verify in dashboards when D5 executes; until then drafts say "provider-plan-dependent" |
| D9 ✋ | **Attorney review of the internal-beta set** — recommended by the rail contract; its absence is an owner-accepted risk that must be *explicitly* accepted | Rail L cannot be Verified with this ambiguous | Either commission a review of the five drafts, or record the documented risk acceptance |
| D10 | **Production data-platform funding** — Supabase Pro (daily backups) and an automated backup schedule (open since Sprint 01.5) | Real workforce+operational data deserves provider-managed backups; privacy angle of an existing migration-plan §22 decision | Adopt at the release train |

## 6. Counsel review register (future; organized so review is cheap)

| # | Question for counsel | When |
|---|---|---|
| C1 | Commercial SaaS agreement / ToS for external customers (Beta Terms are deliberately not that) | Before any paid/external customer |
| C2 | DPA / security addendum template (+ subprocessor flow-down terms) | Before any paid/external customer |
| C3 | State comprehensive-privacy applicability re-pass as the customer footprint expands (per-state thresholds, employee-data scope, contract requirements) | At multi-state expansion |
| C4 | GLBA/Safeguards service-provider posture the moment consumer data is proposed (contract terms under 16 CFR § 314.4(f); FTC breach-notification interplay; AZ statute's GLBA carve-out) | At the §4 trigger — before implementation |
| C5 | Breach-notification playbook (multi-state matrix, provider-vs-operator duties, notification content templates) | Before commercial GA; immediately if an incident occurs first |
| C6 | Workforce privacy review if any monitoring-shaped feature is proposed (replay, productivity analytics, location) | At feature proposal |
| C7 | Liability / warranty / indemnity language in `BETA_TERMS.md` if any user is ever outside the owner's own dealership relationship | Before external beta users |
| C8 | Rights in vendor-report data (Tekion/Keyper/etc. export terms-of-use vs. DealerDOH's aggregation) — likely fine as dealership-authorized use, unverified | Before commercial GA |

## 7. Commercial (v2) prerequisites — recorded, not started

Customer DPA · SaaS agreement · subprocessor terms + change
notification · organization offboarding/export/deletion process
(`DATA_RETENTION.md` §9) · named support/privacy contacts with SLAs
· enterprise security/privacy questionnaire pack · multi-rooftop
(Store #2) privacy boundary = the already-blocking per-row
scoping + RLS prerequisite (`SECURITY_ARCHITECTURE.md` §4) ·
consent/acceptance versioning for commercial onboarding (Phase 32:
for v1.1, Git-versioned documents + publication date suffice
[decision]) · incident-response program beyond §10.

## 8. Rail L exit-condition mapping (where this lands)

| §5.L exit | State after Sprint 15 |
|---|---|
| 1. Accurate data-flow inventory (identity, workforce, vehicle, uploads, telemetry, IP/device metadata, logs, retention, subprocessors) | **Done** — `PRIVACY_ARCHITECTURE.md` §§2–8 (evidence-tagged), `SUBPROCESSORS.md` |
| 2. Published accurate internal-beta documents (Privacy Policy, ToS, support/security contact, incident procedure, retention statement consistent with migration plan) | **Drafted, not published**: `PRIVACY_POLICY.md` + `BETA_TERMS.md` (drafts, placeholders where owner input is genuinely required); incident procedure done (`PRIVACY_ARCHITECTURE.md` §10); retention statement done and migration-plan-consistent (`DATA_RETENTION.md` §7). Publication blocks on **D1, D2, D5** (+D9 disposition) |
| 3. Accessibility Statement from Rail K's real results | **Drafted** — `ACCESSIBILITY_STATEMENT.md`, strictly from `ACCESSIBILITY.md` |
| 4. Every claim traceable to something real | **Method-enforced** — the [repo]/[measured]/[provider]/[research] tagging; no unverifiable claim ships in any draft |

Sprint 17 delta rule stands: this assessment must be amended when
the inbound-email acquisition path exists (new subprocessor, message
metadata, Keyper workforce fields) — `V1_1_RELEASE_READINESS.md`
§5.L.
