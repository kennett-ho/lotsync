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

- One internal dealership deployment (Mark Kia — an Arizona
  dealership; **D3 resolved 2026-08-20: DealerDOH v1.1 is U.S.-only,
  with the initial controlled beta at an Arizona dealership; no
  international availability/compliance is claimed**), operated by
  the product owner ("DealerDOH, operated by Kennett Ho" — D1);
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
| 3 | Arizona comprehensive consumer privacy law | **None enacted** — watch item | Arizona currently has **no enacted comprehensive consumer privacy law**; the state-law surface for this assessment is the breach statute (row 2) plus the Consumer Fraud Act. Disposition note: SB 1815 ("personal data; consumers; controllers; requirements," 57th Leg. 2nd Reg. Session) was **introduced in the 2026 session and not enacted** — last recorded action a Senate second reading 2026-02-10; tracked status "introduced–dead" [research: legislative tracking (LegiScan), 2026-08-20; the operative fact is the absence of an enacted statute — re-check each session] |
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

**Current-scope assessment (careful, deliberately non-categorical,
no compliance claim — owner-refined 2026-08-20):** DealerDOH's
**intended and validated data flows** — the governed report
contracts, importer columns, and persist paths — do not process
financing or customer financial information and **do not appear to
involve "customer information" in the Safeguards Rule's sense**
[`PRIVACY_ARCHITECTURE.md` §2.3, verified at the data-model level].
On those flows, DealerDOH **does not currently appear to be acting
as a Safeguards Rule service provider** for such information,
because the Rule's service-provider perimeter is defined by access
to customer information. Mark Kia's own Safeguards obligations for
its own systems (its DMS, its F&I tools) are the dealership's, and
DealerDOH neither discharges nor interferes with them.

**Why this is not stated categorically:** the same audit established
that `POST /inventory-sync/run` retains entire raw uploaded files
verbatim — including any unexpected extra columns an operator's
export happens to carry (`PRIVACY_ARCHITECTURE.md` §2.3 caveat).
Nothing reads such columns, but the bytes would be *maintained*.
**Incidental receipt of customer information through a
broader-than-expected raw vendor export therefore remains a live
data-minimization risk**, and it drives two consequences:
- the reassessment trigger below is phrased around **receiving,
  maintaining, processing, or being permitted access to** customer
  information — not only around deliberately ingesting it; and
- owner decision **D4** — **ratified 2026-08-21**: raw uploads are
  temporary operational evidence with bounded retention and deletion
  (**7 days accepted / 30 days rejected-or-HOLD**, never an
  indefinite default). The tested implementation is still to land
  as the bounded retention remediation **before the v1.1 release**
  (§5 D4; `DATA_RETENTION.md` §3); once live, the incidental-receipt
  window shrinks to those bounds — until then the verbatim files
  persist and this caveat stands at full strength.

**What must never be claimed:** "DealerDOH is GLBA compliant"
(meaningless and false — the Rule's program obligations attach to
the financial institution, and no assessment has been performed) and
"GLBA can never apply" (false — one scope change flips the
analysis).

**Recorded trigger:** if DealerDOH ever **receives, retains,
maintains, processes, or is permitted access to** GLBA customer
information —
by deliberate ingestion (financing applications, deal jackets,
consumer credit data, consumer contact/CRM records, payment data,
or any consumer NPI), by DMS connectivity that grants such access,
**or by discovering such content in retained raw uploads** — then
reassess Safeguards service-provider status **before**
implementation (or immediately upon discovery, for the incidental
case), expect contractual safeguards obligations from the
dealership under § 314.4(f), and take the question to counsel
[counsel: C4]. The same trigger is recorded in
`PRIVACY_ARCHITECTURE.md` §2.3 and the back-burner register
(`V1_1_RELEASE_READINESS.md` §7 "Formal GLBA posture").

## 5. Owner decision register — **ALL TEN RESOLVED 2026-08-20**

Every decision below was resolved by the owner on 2026-08-20; the
register now records each resolution plus its remaining
**execution** items. Post-resolution gate framing: no undecided
question remains — Rail L **Verified** waits on *execution* of
D2 + D5 (create the real monitored contact, then publish the
owner-approved final texts on `dealerdoh.com` before the v1.1
production cutover, per §5.L exit 2). **D4's retention durations and
cleanup design were ratified 2026-08-21** (`DATA_RETENTION.md` §3);
the tested implementation — the bounded retention remediation —
must still land **before the v1.1 release** (Sprint 18 readiness
checks it), and the legacy production prune waits for its
production release/operator gate, never a branch merge.

| # | Decision (resolved 2026-08-20) | Resolution | Remaining execution / follow-through |
|---|---|---|---|
| D1 | **Operating identity in published documents** | For the v1.1 beta: **"DealerDOH, operated by Kennett Ho."** No separate corporation/LLC is invented or implied; a future legal entity may replace this identity before commercial GA if one is formed | Drafts updated in place (Privacy Policy "Who we are", Beta Terms §1). Entity formation remains a pre-commercial-GA consideration alongside C1 |
| D2 | **Support / privacy contact** | A **real, monitored `dealerdoh.com` contact will be created before policies are published**; one address may initially serve both support and privacy. Placeholder addresses are never published as real contact information | **Execution pending (publication blocker):** create the mailbox, verify it is monitored, fill every draft's contact section. Feeds the D5 publication step |
| D3 | **Jurisdiction / audience** | **DealerDOH v1.1 is U.S.-only**, with the initial controlled beta operating at an Arizona dealership. International availability/compliance is **not claimed** | Beta Terms governing law = Arizona; Privacy Policy states U.S.-only scope; §1 of this document updated. §3's GDPR/state rows keep their triggers |
| D4 | **Raw-upload retention** | Raw vendor uploads are **temporary operational evidence, not permanent archives**; indefinite retention is **not** the v1.1 policy. **Ratified 2026-08-21 as proposed:** accepted/successfully processed batches → **7 days**; rejected/unacknowledged batches → **30 days**; future HOLD batches → **no longer than 30 days** unless a later explicitly governed policy supersedes it; normalized operational evidence, fingerprints, SyncRuns, and other governed records follow their own retention policies (§1); initial-beta durations subject to tuning from operational evidence. Cleanup architecture **approved in principle**: `outcome.json` disposition markers + opportunistic cleanup during `/validate` and `/run`, conservative legacy handling, kill switch, boundary tests, explicit operator-approved one-time legacy prune | **Release-gating execution pending:** the tested implementation lands as the bounded retention remediation (dedicated PR with a DEV review window) **before the v1.1 release** — Sprint 18 readiness checks it. **The destructive legacy prune of existing production raw files is NOT performed at the PR #25 merge; it waits for the appropriate production release/operator gate.** Sprint 17 must still design acquisition-path retention within the ratified HOLD bound. Also conditions §4 (the incidental-receipt path) |
| D5 | **Policy publication** | Privacy/legal documents remain **internal drafts during development**; approved versions are **published on `dealerdoh.com` before the DealerDOH v1.1 production cutover**. Planned public surfaces: `/privacy`, `/terms`, `/accessibility`, `/security` if appropriate. **Never added to current LotSync production** | **Execution pending — the remaining Rail L Verified gate** (with §5.L exit 2): needs D2's mailbox + owner approval of final text, then the pre-cutover publication step |
| D6 | **Acceptance model** | **Notice-only for the controlled v1.1 employee beta** — individual dealership employees are not required to complete clickwrap merely to use their authorized workplace account. Contractual acceptance is reassessed for commercial v2, likely primarily at the organization/admin/customer-contract level | Beta Terms §12 updated to the decided text; the v2 reassessment stays in §7 / C1 |
| D7 | **Customer naming in public policies** | Public privacy/legal documents are **customer-neutral** — "customer organization," "participating dealership," or equivalent accurate language; **Mark Kia is not named in the standard policies**. Mark Kia may still appear in separately approved case-study/pilot/marketing material | Drafts verified clean of the dealership name (sweep 2026-08-20). Internal engineering docs are unaffected by D7 |
| D8 | **Provider-plan verification** | Provider statements must be **verified against actual current plans/configuration before publication**. No unsupported claims about retention, data residency, backups, availability, security guarantees, or support for Supabase, Render, Vercel, Sentry, PostHog, or future providers | **Tracked as manual release-readiness actions:** verify Sentry org plan/retention · PostHog plan/retention · Supabase plan, backup capability, log retention · Render plan/log retention · Vercel plan/log retention · regions for all — then finalize the figures in `SUBPROCESSORS.md` and `DATA_RETENTION.md` §5 at publication |
| D9 | **Attorney review** | **Not required to continue the controlled v1.1 beta.** Recorded honestly: **no attorney review has been completed for the v1.1 controlled beta; current documents are beta/evaluation readiness materials; qualified legal review is recommended/required before commercial GA / v2 contractual deployment.** No document may imply counsel reviewed or approved it | This row **is** the rail contract's owner-accepted-risk record (§5.L). Every draft banner carries the disposition; C1/C2/C7 remain the pre-GA review vehicles |
| D10 | **Production data platform (paid Supabase tier)** | A **production/commercial-readiness decision, not a compliance claim**. Direction: likely adopt an appropriate paid Supabase tier before commercial production use **if its verified backup, retention, operational, or support benefits justify it**. The exact paid-tier benefits must be verified before being relied on in security/privacy language; **no benefit is claimed until the actual plan/configuration is confirmed** | Folded into D8's release-readiness verifications and the migration plan's §22 register; `SECURITY_OVERVIEW.md` / `DATA_RETENTION.md` phrased accordingly (verify-then-rely) |

## 6. Counsel review register (future; organized so review is cheap)

| # | Question for counsel | When |
|---|---|---|
| C1 | Commercial SaaS agreement / ToS for external customers (Beta Terms are deliberately not that) | Before any paid/external customer |
| C2 | DPA / security addendum template (+ subprocessor flow-down terms) | Before any paid/external customer |
| C3 | State comprehensive-privacy applicability re-pass as the customer footprint expands (per-state thresholds, employee-data scope, contract requirements) | At multi-state expansion |
| C4 | GLBA/Safeguards service-provider posture the moment customer information is proposed **or discovered** (incidental receipt in retained raw uploads counts — §4): contract terms under 16 CFR § 314.4(f); FTC breach-notification interplay; AZ statute's GLBA carve-out | At the §4 trigger — before implementation, or immediately upon discovery |
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

| §5.L exit | State after Sprint 15 + the D1–D10 resolutions (2026-08-20) |
|---|---|
| 1. Accurate data-flow inventory (identity, workforce, vehicle, uploads, telemetry, IP/device metadata, logs, retention, subprocessors) | **SATISFIED** — `PRIVACY_ARCHITECTURE.md` §§2–8 (evidence-tagged), `SUBPROCESSORS.md`. D8 adds a publication-time re-verification of provider figures (manual release-readiness actions) |
| 2. Published accurate internal-beta documents (Privacy Policy, ToS, support/security contact, incident procedure, retention statement consistent with migration plan) | **Content complete; PUBLICATION EXECUTION PENDING.** Drafts now carry the resolved D1 identity, D3 scope, D6 acceptance model, D7 neutrality, and the D9 disposition; incident procedure done (`PRIVACY_ARCHITECTURE.md` §10); retention statement accurate and migration-plan-consistent (`DATA_RETENTION.md` — current behavior + the **ratified D4 policy (7-day accepted / 30-day rejected-or-HOLD)**, implementation pending). Remaining: **D2 execution** (create the monitored mailbox, fill contacts) → owner approval of final text → **D5 execution** (publish on `dealerdoh.com` before the v1.1 production cutover) |
| 3. Accessibility Statement from Rail K's real results | **Drafted** — `ACCESSIBILITY_STATEMENT.md`, strictly from `ACCESSIBILITY.md`; needs only the D2 contact at publication |
| 4. Every claim traceable to something real | **SATISFIED** — the [repo]/[measured]/[provider]/[research] tagging; no unverifiable claim ships in any draft |

Post-resolution summary: **no owner decision remains open.** Rail L
stays **Implementation Complete — Awaiting Merge**; after merge +
merged-head CI, **Verified turns on execution only** — D2's real
mailbox, owner-approved final text, and the D5 pre-cutover
publication. Separately, **D4 is ratified (2026-08-21); its tested
implementation remains release-gating** — before the v1.1 release
train (Sprint 18 checks it), with the legacy production prune gated
to the production release/operator step, never a merge; D4 also
conditions the §4 GLBA/Safeguards analysis.

Sprint 17 delta rule stands: this assessment must be amended when
the inbound-email acquisition path exists (new subprocessor, message
metadata, Keyper workforce fields) — `V1_1_RELEASE_READINESS.md`
§5.L.
