# Sprint 17 — Keyper Automated Evidence Integration Plan

**Status:** Planned — not started

**Release:** DealerDOH `v1.1.0-beta.1`

**Sprint:** 17 — Vendor Integration & Automated Evidence Acquisition

**Primary adapter:** Keyper Scheduled All Vehicles / Full Inventory

**Owner scope decision:** 2026-08-18

This is the planning contract for Sprint 17. It does not describe
implemented code. The operative release status remains in
`V1_1_RELEASE_READINESS.md`; the implemented ingestion boundary remains
canonical in `INGESTION_ARCHITECTURE.md`.

Sprint 10 remains **Implementation Paused — Awaiting Vendor Evidence**
and Rail D remains **Merged — NOT Verified; Awaiting Vendor Evidence**.
Nothing in this plan changes that status or invents the Keyper Event
contract.

---

## 1. Goal and release position

Move DealerDOH from manual-only source acquisition toward automated
dealership evidence acquisition while preserving the Sprint 10 safety
boundary.

The release progression is:

- Sprint 10: safely understand dealership evidence.
- Sprint 11: observe what is happening.
- Sprints 12–16: make the system safe and effective for people.
- Sprint 17: receive trusted dealership evidence automatically.
- Sprint 18: freeze and release confidently.

Sprint 17 contains one v1.1 vendor adapter: **Keyper Scheduled All
Vehicles / Full Inventory**. No unrelated vendor automation belongs in
this sprint.

---

## 2. Canonical acquisition boundary

```text
Vendor / acquisition mechanism
        ↓
DealerDOH acquisition adapter
        ↓
Sprint 10 ingestion boundary
        ↓
Classification
        ↓
Validation
        ↓
Accept / HOLD / Reject
        ↓
Reconciliation
        ↓
Tasks / recommendations / history
```

Email is transport only. Recipient, sender, subject, filename, MIME
claim, and provider metadata are routing/screening hints; none can make
an attachment valid evidence. Content classification and validation
remain authoritative.

Automated acquisition must reuse `validate_report_set()` and the
existing fingerprint, baseline, warning, and reconciliation contracts.
A second validation path is an architecture violation.

---

## 3. Dealership and source routing

Preferred addressing model:

```text
source@dealership.dealerdoh.com
```

Examples:

- `keyper@markkia.dealerdoh.com`
- `rapidrecon@markkia.dealerdoh.com`
- `keyper@markhyundai.dealerdoh.com`

Rules:

- Subdomain is a dealership routing hint.
- Local part is an expected source/integration hint.
- Backend dealership configuration is authoritative for the serving
  store.
- Sprint 10 classification/validation is authoritative for evidence
  identity.
- Mark Kia-specific routing must not be hardcoded into product
  architecture.
- Full per-row store scoping remains mandatory before Store #2 becomes
  live; address parsing does not satisfy that boundary.

---

## 4. Keyper Full Inventory contract v1 — planned extension

The initial scheduled-report adapter targets Keyper **All Vehicles /
Full Inventory**. The owner-provided dealership discovery uses the
following current Keyper terminology. Sprint 17 must pin the delivered
attachment against representative vendor evidence before declaring the
contract verified.

### Core evidence fields

| Keyper field | DealerDOH meaning | Planned requirement |
|---|---|---|
| `Name` | Stock number / dealer inventory reference | Required |
| `Attribute 7` | VIN / primary vehicle correlation | Required |
| `Status` | Current key state (`In` / `Out`) | Required |
| `Checkout Date` | Key aging / outstanding duration | Required |
| `User` | Current or last-known key user | Required |
| `System` | Sister dealership/store represented by the record | Required |
| `Cabinet` | Physical key-storage location | Required; context only |

`Cabinet` may vary within one dealership. It is location context, not
vehicle identity.

### Operational enrichment

| Field | Grounded interpretation | Permitted use |
|---|---|---|
| `Registration Type` | `Registered` / `Unregistered Asset` | Human-review candidate `Verify Key Registration`; never assert why registration is missing |
| `Removal Type` | `Legal` / `Illegal` as recorded by Keyper | Human-review candidate `Review Key Removal Activity`; preserve vendor evidence without inferring intent or misconduct |
| `Issue Comment` | Context may distinguish checkout actor from return actor | Timeline/accountability context; preserve both actors when source evidence does |
| `User Description` | Department/role context such as Kia Sales, Mazda Lot, Detail | Help staff locate/follow up; no department-specific workflow rules without separate grounding |

Checkout-user and return-user evidence must not be collapsed into one
ambiguous actor.

### Display-only context

Retain `Description`, `Year`, `Make`, and `Model` for human context.
They must not overwrite canonical vehicle identity or lifecycle evidence
without a separately governed rule.

### Intentionally excluded

`Type` is excluded from the initial workflow contract because it is
often missing, inconsistently entered, not operationally required, and
not workflow-breaking.

---

## 5. Evidence authority

Keyper is a strong source for **physical key custody**, not the entire
vehicle lifecycle.

- Tekion = inventory/business lifecycle evidence.
- Keyper = physical key-custody evidence.
- DealerDOH = reconciliation across both.

Grounded operational assumptions:

- A key physically in Keyper supports dealership custody of that
  vehicle/key record.
- A sold vehicle should not keep a key in the Keyper cabinet.
- A vehicle that has not arrived generally cannot yet have its
  dealership key entered into Keyper.

DealerDOH must not document either vendor as globally authoritative
over the other.

---

## 6. Planned cross-system scenarios

| Evidence relationship | Interpretation | Planned operational result |
|---|---|---|
| Tekion active + Keyper record | Strong support for physical dealership presence/custody | No task from this relationship alone |
| Tekion active + no Keyper record in a fresh, accepted Full snapshot | Key programming/registration/onboarding may be incomplete | Human-review candidate `Verify Missing Keyper Record` |
| Keyper record + no matching active Tekion vehicle | Sold/transfer/trade cleanup or lifecycle discrepancy may exist | Human-review candidate `Review Unmatched Keyper Record`; never decide which system is wrong automatically |
| Tekion sold + Keyper record remains | Strong cross-system exception | Human-review candidate `Review Sold Vehicle Key` |
| Keyper `Status = Out` beyond governed threshold | Existing checked-out-key evidence | Reuse the existing `investigate_checked_out_key` workflow; do not create a parallel task type |

The first three candidate task labels are planning language, not yet
controlled-vocabulary decisions. Sprint 17 must inspect existing task
generation/deduplication and add only the smallest non-duplicative set.
In particular, map them first against the existing
`incoming_or_missing_investigate_report.csv`,
`flag_to_controller_report.csv`, `sold_vehicles_report.csv`, and
`investigate_checked_out_key` paths. A new Task is justified only when
those existing outputs do not already carry the operational work.

Any missing-Keyper conclusion must come from a fresh, accepted,
authoritative Full snapshot evaluated with current positive Tekion
evidence. A missing/stale Keyper delivery or an incomplete/rejected
snapshot can never create the task.

---

## 7. Keyper Event Report boundary

Keyper Event ingestion is not Sprint 17 scope unless a real vendor
sample/contract is obtained and separately validated.

Current evidence truth remains:

- Known Keyper Full Inventory contract passes.
- Unsupported/nonmatching Keyper-shaped reports fail safely.
- Real Keyper Event-vs-Full structural distinction is **PENDING VENDOR
  EVIDENCE**.
- Keyper Event ingestion is unsupported and not required for v1.1.

The scheduled All Vehicles snapshot is Sprint 17's target. However,
unattended Keyper processing cannot be activated and Sprint 17 cannot
be Verified while a real Event export could still satisfy the Full
signature. The real sample must prove discrimination or drive a
contract/classifier correction through the Sprint 10/Rail D evidence
path. Transport allowlists do not replace that evidence check.

---

## 8. Inbound-email architecture

The provider may use a domain catch-all plus authenticated webhook:

```text
DNS / inbound email provider
        ↓
email.received webhook
        ↓
recipient resolver
        ↓
dealership + expected-source lookup
        ↓
sender/message screening
        ↓
attachment extraction
        ↓
message-ID + attachment-fingerprint deduplication
        ↓
Sprint 10 classifier/validator
        ↓
Accept / HOLD / Reject
        ↓
sync/reconciliation
```

The webhook should acknowledge the provider quickly. If provider
timeouts or retry semantics make synchronous reconciliation unsafe,
use the lightest durable acquisition-job/worker boundary that meets
v1.1 reliability. Do not introduce a distributed queue or
microservice architecture without evidence it is needed.

### Required message safety

- Provider webhook signature/authentication verification.
- Configured dealership/source allowlist.
- Safe unknown-recipient handling.
- Grounded sender rules; no trust in sender alone.
- Attachment type validation and size limits.
- Provider message-ID deduplication.
- SHA-256 attachment fingerprinting.
- Replay/idempotency protection.
- No trust in filename, recipient, sender, or subject alone.
- Sprint 10 validation before mutation.
- HOLD on every unattended warning.
- Sprint 11 structured/correlated observability.
- Safe failure and retry behavior.
- No raw email body, attachment contents, transport headers, provider
  credentials/signatures, VINs, filenames, or Keyper comments in logs,
  Sentry, or product analytics; use configured IDs, safe state/error
  codes, counts, and non-secret fingerprints only.

Unknown or unsupported recipients should be acknowledged safely and
recorded as unsupported, not treated as malicious by default.

---

## 9. Automated processing policy

```text
ERROR   → Reject; no operational mutation
WARNING → HOLD for human review; never auto-acknowledge
INFO / clean validation → Eligible for automated processing under the final v1.1 policy
```

The owner-ratified suspicious-count policy remains unchanged:

- Decrease greater than 15% **and** at least 10 rows lost → WARNING.
- Increase greater than 50% **and** at least 25 rows added → WARNING.
- Warnings require human acknowledgement.
- Unattended ingestion HOLDs on warnings.

Human acknowledgement must remain bound to the exact report
fingerprint; automation cannot manufacture or persist it.

---

## 10. Source freshness

Sprint 17 introduces an explicit freshness model:

- Fresh
- Aging
- Stale
- Missing / never received

> **Stale evidence ≠ current evidence.**

Freshness must use the configured expected cadence and the last
accepted source evidence; stale or missing delivery cannot be treated
as a current negative observation. Realtime integration is not
required.

Planning cadence context, not hardcoded policy:

- Keyper: scheduled automatically.
- Tekion: manual 1–2× daily until scheduling/access is grounded.
- RecovR: manual/API/browser acquisition 1–2× daily pending discovery.
- MDD: manual 1–2× daily.
- RapidRecon: event-email or digest behavior pending discovery.

Sprint 17 must establish the actual Keyper schedule and owner-approved
Fresh/Aging/Stale thresholds before implementation marks freshness
complete. It must not automate the other vendors.

---

## 11. Sprint scope boundary

### Required

- Keyper scheduled All Vehicles acquisition.
- Configurable dealership/source inbound routing architecture.
- Message and attachment deduplication.
- Existing Sprint 10 classifier/validator integration.
- Unattended ERROR/WARNING behavior.
- Keyper operational enrichment from §4.
- Relevant non-duplicative cross-system reconciliation/task rules.
- Acquisition/processing observability through Sprint 11 controls.
- Source freshness where appropriate.
- Documentation and tests.
- Real DEV verification.
- Safe real-world Mark Kia pilot only with explicit owner approval.

### Not required

- Keyper Event ingestion.
- Tekion automation.
- RecovR API/browser automation.
- RapidRecon email adapter.
- MDD automation.
- Realtime streaming.
- Generic workflow builder.
- Full queue/microservice architecture.
- Object storage unless provider/retention evidence proves it necessary
  and the owner explicitly promotes that POST-v1.1 trigger.
- Notifications unless separately promoted by the release checkpoint.
- Replacing vendor systems.

---

## 12. Verification and release dependencies

Sprint 17 evidence must include:

- Real representative Keyper scheduled-message and attachment evidence.
- Real Keyper Event evidence sufficient to resolve Full-vs-Event
  discrimination before unattended activation/verification.
- Signature/authentication, recipient/source, attachment, deduplication,
  replay, retry, ERROR, WARNING/HOLD, clean-processing, and freshness
  tests.
- Existing Rail D adversarial/bypass coverage unchanged.
- Dual-engine regression and migration-governance checks for any schema
  change.
- Deployed DEV proof with Sprint 11 request correlation and redacted
  acquisition-state telemetry.
- Targeted Rail H/I delta review for the new authenticated webhook,
  replay surface, provider SDK/dependencies, retry path, and
  attachment-handling attack surface.
- Targeted Rail J resilience evidence for provider retries,
  duplicate/concurrent delivery, expected Keyper report scale, and a
  provider outage that cannot break manual ingestion.
- Targeted Rail L update covering the inbound-email provider as a
  subprocessor, report/attachment and message-metadata retention,
  Keyper user/comment context, deletion, and affected policy text.
- Targeted post-Rail-M human verification of every new HOLD review,
  freshness/staleness, and Keyper work surface; the full Sprint 16 UAT
  cannot silently stand in for workflows added afterward.
- No production changes or real dealership pilot without explicit
  approval.

Before Sprint 18 readiness can pass, record decisions for:

1. Inbound-email provider and verified callback contract.
2. Actual Keyper cadence and Fresh/Aging/Stale thresholds.
3. Human review/resume surface for fingerprint-bound HOLDs.
4. Retry/dead-letter retention and operator ownership.
5. Whether the real unattended failure/HOLD experience triggers the
   still-CONDITIONAL Notifications rail.

---

## 13. Success definition

Sprint 17 succeeds when:

> DealerDOH can automatically receive the scheduled Keyper All Vehicles
> report for a configured dealership, resolve the expected source/store,
> extract and deduplicate the report, pass it through the existing
> Sprint 10 classification and validation boundary, HOLD suspicious
> evidence for human review, safely process valid evidence, reconcile
> Keyper physical-key state against DealerDOH inventory evidence, and
> surface explainable operational work without trusting email transport
> as truth.

Success requires merged and verified evidence. This document's status
remains **Planned** until Sprint 17 is explicitly started.

---

## 14. Notifications checkpoint

Notifications remains **CONDITIONAL**. Sprint 17 does not silently add
a notification center.

After Sprint 17 implementation / during Sprint 18 readiness, evaluate
whether existing operational surfaces reliably bring these states to a
responsible human:

- Scheduled report did not arrive.
- Acquisition failed.
- Validation ERROR.
- Validation WARNING / HOLD.
- Source became stale.
- Ingestion failed repeatedly.

If real evidence shows a gap, promote only the minimal in-app
notification surface through an explicit release-contract amendment
before Sprint 18 can pass.
