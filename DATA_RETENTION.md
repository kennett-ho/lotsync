# DealerDOH Data Retention

**Established:** Sprint 15 (Rail L — Privacy / Legal Readiness).
The canonical retention record: for every class of data DealerDOH
touches, what happens today, what the approved v1.1 policy is, and
what only becomes required later. Factual grounding:
[`PRIVACY_ARCHITECTURE.md`](PRIVACY_ARCHITECTURE.md). Amend in the
same PR as any change to retention-relevant behavior.

**Reading discipline — three different kinds of statement:**
- **Current behavior** — what the code/platforms actually do
  (verified; nothing here is aspirational).
- **v1.1 policy** — the deliberate posture for the internal beta.
  Items marked **[OWNER DECISION]** during Sprint 15 were all
  resolved by the owner (2026-08-20) and D4 ratified (2026-08-21) —
  see `LEGAL_READINESS.md` §5; a policy listed here is adopted unless
  its entry says implementation is pending.
- **Future requirement** — commercial/v2 obligations recorded so
  they are planned, not rediscovered.

Sprint 15 changed **no deletion or retention behavior**. Nothing in
this document destroys data; it records policy and implementation status.

---

## 1. Operational database records

Vehicles, events, tasks, task-execution history, recommendations,
sync runs, report baselines, event freshness, pending identities.

- **Current behavior:** retained indefinitely. History is
  append-only by doctrine (`DECISION_FRAMEWORK.md`); nothing prunes.
- **v1.1 policy (adopted — this is the product working as
  designed):** retain for the life of the dealership relationship.
  The operational history IS the product — evidence aggregation,
  explanation, and audit ("preserve history" is a core doctrine
  commitment). No time-based purge for v1.1. Scale check: years of
  production history measure in single-digit MiB (4.02 MiB at
  4,672 vehicles / 8,876 events) — indefinite retention is not a
  cost or performance problem at this scale (Sprint 14 measured the
  sync-history growth path and bounded its queries).
- **Future requirement:** a commercial offering needs a contractual
  answer for history when the relationship ends — see §9.

## 2. Access-model records (memberships)

- **Current behavior:** `user_membership` rows are deactivated,
  never deleted (`active=false`); reactivation restores with history
  intact [`ACCOUNT_LIFECYCLE.md`].
- **v1.1 policy (adopted, Sprint 09 decision reaffirmed here):**
  deactivation IS offboarding. Retaining the inactive membership row
  preserves operational accountability (who had access, in what
  role, when) while access itself is revoked on the very next
  request. This is deliberate retention with a stated purpose, not
  neglect.
- **Future requirement:** §9 (organization offboarding) and §10
  (identity-deletion requests).

## 3. Raw uploaded report files (`/run`) — **the retention finding: policy ratified, implementation landed 2026-08-25 (production rollout waits for the release gate)**

- **Current behavior (bounded retention implemented 2026-08-25, the
  dedicated D4 remediation):** every `POST /inventory-sync/run`
  writes its uploaded files to a per-request timestamped directory
  under `LOTSYNC_API_UPLOADS_DIR`; the request end stamps an
  `outcome.json` marker (accepted / rejected /
  warnings_unacknowledged), and an opportunistic sweep at the start
  of `/run` and `/validate` deletes batches older than their
  outcome's ratified window (`api/upload_retention.py`;
  `UPLOAD_RETENTION_SWEEP=disabled` is the operator kill-switch).
  Rejected evidence stays inspectable for its full 30-day window.
  `/validate` uploads are still deleted pre-response (test-pinned);
  crash-orphaned `validate-*` directories age out after 24 h.
  **Production still runs the pre-remediation build until the v1.1
  release train** — `/var/data/api_uploads` on the 1 GB persistent
  disk keeps accumulating there until the release/operator gate
  (below). DEV: ephemeral (free tier, wiped on redeploy).
- **Why it matters:** raw vendor exports are the least-minimized
  artifact in the system — verbatim vendor bytes, including free-
  text cells and any extra columns an operator's export happens to
  carry (`PRIVACY_ARCHITECTURE.md` §2.3 caveat). They also consume
  the production disk without bound.
- **v1.1 policy — RESOLVED DIRECTION (owner D4, 2026-08-20):** raw
  vendor uploads are **temporary operational evidence, not permanent
  archives** — indefinite raw-file retention is **not** the intended
  v1.1 policy. Successful validated reports get **short temporary
  retention, then deletion**; rejected/HOLD reports get a **longer
  bounded investigation window, then deletion**; the durable record
  remains the normalized operational evidence, fingerprints,
  SyncRuns, baselines, and history under their own rules (§1).
- **Concrete policy — OWNER-RATIFIED 2026-08-21, as proposed (the
  v1.1 beta policy):**
  - accepted / successfully processed raw upload batches → **retain
    7 days**, then delete;
  - rejected / unacknowledged-warning batches → **retain 30 days**,
    then delete;
  - future HOLD batches → **retain no longer than 30 days** unless a
    later explicitly governed policy supersedes it;
  - normalized operational evidence, fingerprints, SyncRuns, and
    other governed records follow their own retention policies (§1);
  - these are **initial-beta durations subject to tuning from
    operational evidence** (the same propose → ratify → pin pattern
    as the Sprint 10 suspicious-count thresholds).

  **Implementation status:** nothing was deleted or built in Sprint
  15. The cleanup architecture below is **approved in principle**;
  its tested implementation is authorized as the bounded retention
  remediation (item 5). **The destructive legacy prune of existing
  production raw files is NOT performed at the PR #25 merge — it
  waits for the appropriate production release/operator gate.**
  **Update 2026-08-25 — implemented as authorized:** the marker +
  sweep design below is built (`api/upload_retention.py`, wired into
  both endpoints) with boundary tests
  (`tests/test_upload_retention.py`) pinning both windows, the
  marker on every terminal `/run` outcome (the 500 path deliberately
  stays unmarked → conservative window), the
  never-delete-inside-window rule, conservative unmarked/malformed
  handling, the recognized-names-only deletion rule, the
  kill-switch, and the in-flight-batch safety property. The legacy
  production prune remains exactly as gated above — nothing about
  this landing performs it.
  Grounding for the durations (actual troubleshooting/recovery
  needs, not convention):
  - **Accepted batches (validated + successfully executed): retain
    7 days, then delete.** Grounding: the manual sync cadence is
    1–2×/day per source with same-day outcome review by the
    operator who ran it (the recorded Rail E rationale); the
    longest routine attention gap is a holiday-weekend span of
    ~3–4 days — 7 days covers it with margin. After a successful
    run the authoritative record is the database, and the vendor
    system remains the source of truth for any re-export.
  - **Rejected / unacknowledged-warning batches (zero-mutation):
    retain 30 days, then delete.** Grounding: for a rejected run
    the raw file is the *only* evidence of what was rejected;
    investigating one realistically spans a vendor
    re-export/support exchange (days to weeks), bounded by a
    monthly operational review cycle. These files are also
    precisely the ones most likely to carry unexpected content —
    a reason they must not live forever (`LEGAL_READINESS.md` §4).
  - **Future Sprint 17 HOLD state:** ratified bound = **no longer
    than 30 days** (the rejected window); Sprint 17's
    dead-letter/retention design
    (`KEYPER_AUTOMATED_INTEGRATION_PLAN.md` §12 item 4) may only
    shorten it, or supersede it with a later *explicitly governed*
    policy.
- **Technical cleanup design (approved in principle 2026-08-21 with
  the durations; additive, no schema change, no new infrastructure):**
  1. At request end, the router writes a small `outcome.json`
     marker (accepted / rejected / warnings-unacknowledged +
     timestamp) into the batch directory.
  2. An **opportunistic sweep** at the start of `/run` and
     `/validate` (no scheduler exists on the current hosting tier;
     files only accumulate when these endpoints are used) deletes
     batch directories older than their outcome's window.
     Unmarked/legacy directories (pre-feature, or crash-before-
     marker) age under the *longer* rejected window, conservatively;
     orphaned `validate-*` temp directories older than 24 h (crash
     leftovers) are also removed.
  3. Safety: the in-flight batch is never touched; deletion happens
     only under the uploads root; an environment kill-switch
     disables the sweep during investigations; one structured INFO
     record per sweep (counts and batch timestamps only — never
     filenames beyond the server-generated names, never contents);
     boundary tests pin both windows, the marker writing, and the
     never-delete-inside-window rule.
  4. Rollout includes a **one-time, operator-executed prune of the
     accumulated legacy production directories** — an explicit
     approved step in the deploy notes, never automatic, **never
     part of a branch merge (expressly not at the PR #25 merge)**:
     it runs only at the appropriate production release/operator
     gate.
  5. Implementation vehicle (**authorized 2026-08-21** as the
     bounded retention remediation): a small dedicated PR with its
     own DEV review window — the sweep is a runtime-visible change,
     so the deployed path is smoked before merge per the process —
     preferred so the behavior soaks before RC; folding into Sprint
     17's acquisition-retention design remains the owner's
     alternative. Either way it lands, tested, **before the v1.1
     release train** (Sprint 18 readiness checks it).
- Until the release train deploys the implementation to production,
  the **operator-side control available there** (no code change):
  periodic manual review/pruning of `/var/data/api_uploads` during
  maintenance, exactly like the existing backup procedure.
- **Production rollout note (keeps item 4's "never automatic"
  honest):** once this code reaches production, the first sweep
  would delete legacy directories older than 30 days on its own.
  The release-train deploy notes must therefore either (a) deploy
  with `UPLOAD_RETENTION_SWEEP=disabled` until the operator performs
  the approved one-time legacy prune, then enable it, or (b) record
  explicit operator approval that the first post-deploy sweep
  performs that prune. Either way the legacy deletion happens at the
  operator's gate, not as a merge side effect — Sprint 18 readiness
  carries this as a checklist item.
- **Why this cannot slip past the release:** beyond disk growth,
  the retained verbatim bytes are the stated reason
  `LEGAL_READINESS.md` §4's GLBA/Safeguards conclusion is
  deliberately non-categorical — indefinite raw-file retention
  creates a potential incidental-receipt path for unexpected
  sensitive columns, and time-bounding the store is the control
  DealerDOH itself owns.
- **Also unverified and worth one operator look:** the CLI-era
  `/var/data/uploads` folder's current production contents
  (pre-API workflow; repo cannot see the disk).

## 4. Generated outputs

- **Current behavior:** report CSVs are written to fixed filenames
  in `LOTSYNC_OUT_DIR` and **overwritten every sync** — only the
  latest generation exists. Work-order PDFs are built in memory and
  never touch disk.
- **v1.1 policy (adopted — current behavior is already right):**
  latest-only is the correct shape; the durable record is the
  database, not the CSVs.

## 5. Logs and telemetry (provider-bound)

| Signal | Where | Retention (current behavior) |
|---|---|---|
| Structured JSON logs + uvicorn access lines (incl. client IPs) | Render service logs | Platform-retained — 7 days on the current plan tier [provider docs, 2026-08-20] |
| Supabase project/auth logs | Supabase | 1 day on the Free plan [provider docs, 2026-08-20] |
| Sentry error events | Sentry (DEV projects) | Plan-dependent: 30 days (free/Developer) to 90 days (paid) [provider docs, 2026-08-20 — verify the org's plan before publishing a number] |
| PostHog product events | PostHog US cloud | ~1 year on the Free plan [provider docs, 2026-08-20] |
| Vercel platform logs | Vercel | Plan-dependent, short-horizon; verify at publication |

- **v1.1 policy (adopted):** accept provider defaults for the beta;
  no log export/archival pipeline (would be premature
  infrastructure). Per owner **D8** (2026-08-20): every provider
  figure in this section must be **re-verified against the actual
  plan/configuration before any published statement relies on it** —
  tracked as manual release-readiness actions
  (`LEGAL_READINESS.md` §5 D8). Consequence, stated honestly: diagnostic and
  incident evidence at the platform layer is short-lived — the
  incident procedure (`PRIVACY_ARCHITECTURE.md` §10) therefore says
  to export relevant provider logs immediately when an incident is
  suspected.
- **Future requirement:** production observability activation (the
  release train) re-decides plans/retention with real budgets.

## 6. Supabase Auth identities

- **Current behavior:** Auth users persist until an operator
  deletes them in the Supabase dashboard. DealerDOH deliberately
  does not delete or ban Auth identities as part of offboarding
  (Sprint 09 decision: membership deactivation fully revokes
  access; identity deletion destroys history for no access-control
  gain) [`ACCOUNT_LIFECYCLE.md`].
- **v1.1 policy (adopted):** unchanged. Identity deletion remains a
  deliberate operator action for the cases that genuinely require
  it (e.g. a person's explicit removal request — §10), performed in
  the provider dashboard, recorded when done.

## 7. Backups

- **Current behavior:** production SQLite — manual verified backups
  (Render `/var/data/backups/` + operator machine
  `C:\Users\demon\LotSync-Backups\`); no automated schedule; the
  2026-08-15 backup is SHA-256-verified in `PRODUCTION_BASELINE.md`.
  DEV Supabase: Free plan, no provider backups (synthetic data —
  acceptable, recorded).
- **v1.1 / migration policy (already governed —
  `PRODUCTION_MIGRATION_PLAN.md` §17–§18, §22):** at cutover, the
  frozen legacy SQLite file is renamed ~day 7 and deleted ~day 90
  with explicit owner approval (G9); the off-host final backup is
  kept ≥ 1 year; the migration-epoch artifact is retained as the
  long-term record. Adopting an appropriate **paid Supabase tier**
  is the recorded direction for production (migration plan §22;
  owner **D10**, 2026-08-20: a production/commercial-readiness
  decision, not a compliance claim — the tier's actual
  backup/retention/operational benefits must be **verified before
  being relied on** in any security/privacy language, and no
  benefit is claimed until confirmed). Any retention/deletion
  statement in customer-facing copy must stay consistent with these
  decisions (Rail L exit condition 2).
- **Backups contain what the database contains** — vehicle
  operational data and (post-migration) membership rows; Supabase
  Auth identities are backed up by the provider, not by DealerDOH.
  Backup copies inherit the owner's machine/account security and are
  covered by the incident procedure.

## 8. Browser-side state

- **Current behavior:** the Supabase session in localStorage
  persists until sign-out (supabase-js clears it) or provider
  session expiry; PostHog persistence keys persist per SDK defaults
  and are severed/reset at sign-out (`posthog.reset()`). Sprint 15
  removed the one first-party cookie (PostHog persistence is now
  localStorage-only).
- **v1.1 policy (adopted):** nothing further — there is no app-side
  browser cache of operational data to retain or expire
  (`Cache-Control: no-store` from the API).

## 9. Organization / relationship termination — future requirement

DealerDOH is not yet commercial SaaS; there is no self-service
"delete organization," deliberately (a destructive control with no
current customer to need it). Recorded as a **commercial
prerequisite** (also in `LEGAL_READINESS.md` §6): before any paid
external customer, DealerDOH needs a contractual data-disposition
answer — export format (the dual-engine tooling and CSV writers are
a real head start), deletion scope (operational rows, memberships,
Auth identities, backups' expiry), timeline, and a certificate/record
of disposition. Until then, the honest statement is: "data
disposition at end of relationship is handled by agreement with the
dealership" — nothing stronger may be promised.

## 10. Individual access / correction / deletion requests — manual process (v1.1)

No DSAR portal exists and none is warranted at internal-beta scale
(the data subjects are a handful of dealership colleagues, no
comprehensive privacy statute currently obligates a portal — see
`LEGAL_READINESS.md` §3). The honest, capability-true process:

- **Locate:** an admin/manager can see a person's roster entry
  (email, display name, role, active state); the operator can
  locate the Supabase Auth record and the `user_membership` row by
  email/UUID; operational references to a person are limited to
  incidental vendor free-text (`PRIVACY_ARCHITECTURE.md` §2.1) —
  searchable in `event.detail_fields` if ever needed.
- **Correct:** display name is self-service (Settings); email is a
  provider-side operator action; role/store are admin actions.
- **Delete:** membership deactivation on request is immediate
  (admin action). Full Auth-identity deletion is the §6 operator
  action. Vendor-reported operational history is evidence and is
  **not** deleted on individual request by default — assess
  case-by-case with the purpose test (accountability) and, if the
  situation is contested, counsel.
- **Do not promise** response timelines or statutory rights in
  customer-facing copy that current law does not require and current
  staffing cannot guarantee — the drafts say "contact the operator"
  ([OWNER: contact address — decision D2]) and no more.
