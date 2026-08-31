# DealerDOH Service Providers / Subprocessors

> **DRAFT — NOT PUBLISHED.**
> The provider inventory behind the Privacy Policy's "Service
> providers" section. Environment-honest: it distinguishes what
> processes dealership data **today** from the **v1.1 target stack**
> that activates at the release train. Regions are current
> configuration facts, not contractual residency guarantees. Owner
> decisions resolved 2026-08-20 (`LEGAL_READINESS.md` §5):
> publication with the policy set on `dealerdoh.com` before the
> v1.1 production cutover (D5). Per **D8**, every plan-dependent
> figure here must be verified against the actual provider
> plans/configuration before publication — tracked as manual
> release-readiness actions — and no unsupported claim about
> retention, residency, backups, availability, security guarantees,
> or support may survive that pass. D9 disposition:
> beta/evaluation readiness material; no attorney review has been
> completed for the v1.1 controlled beta.

**Last reviewed:** 2026-08-30 (reconciled against v1.1 release
candidate `680272a` and the Sprint 18 Gate D provider verification —
plans, regions, and account posture checked in the actual provider
dashboards) · **Version:** draft-2

---

## Runtime providers — v1.1 stack

| Provider | Role | Data it processes | Region (current config) | In use today |
|---|---|---|---|---|
| **Vercel** | Frontend hosting/CDN | Serves the app to browsers; platform edge/request logs (connection metadata incl. IP) | US/global edge | **Yes** — production (LotSync) and DEV |
| **Render** | API hosting | All application traffic; service logs (request lines incl. client IP, structured app logs); production service disk (database file, uploaded report files, generated reports) | Oregon, US | **Yes** — production (LotSync) and DEV |
| **Supabase** | Sign-in (Auth) + PostgreSQL database | Staff account identities (email, password credentials, session state, display name), authorization/membership rows, all operational business data; provider auth/audit logs | us-west-2 (Oregon, US) — verified for both the DEV and the provisioned production project | **DEV today; planned for v1.1 activation.** A dedicated production project exists but is empty and not connected to anything; it begins processing real data only at the v1.1 release train (current production uses SQLite on Render, no Supabase) |
| **Sentry** | Error monitoring | Error/exception events — configured to exclude user identity, request bodies, cookies; masked URLs; request references. Retention ~30 days on the current plan | US (SaaS) | **DEV today; planned for v1.1 activation.** Dedicated production projects exist but are empty and not connected; activation is a deliberate release-train step |
| **PostHog** | Product analytics | Named product events under an internal account identifier (never email/name); role/store identifiers; ingest-side connection metadata. Event retention ~1 year on the current plan | US cloud (`us.i.posthog.com`) | **DEV today; planned for v1.1 activation.** A dedicated production organization/project exists but is empty and not connected; activation is a deliberate release-train step |
| **Northwest Registered Agent** (domain registrar + email service for `dealerdoh.com`) | Support/privacy mailbox (`support@dealerdoh.com`; `privacy@dealerdoh.com` forwards to it) and the domain's DNS | Emails sent to the support/privacy address (which may include staff names/addresses and whatever senders include); DNS records | US | **Activates at publication** — the mailbox is created and verified before this policy set goes live |

**Today's actual production processors** (unauthenticated LotSync
beta): **Vercel and Render only.** Supabase, Sentry, and PostHog
currently process synthetic development data. Their production
projects have been **provisioned in advance but are empty and wired
to nothing**; they begin processing real dealership/staff data only
when v1.1 ships through its approved release train, at which point
this inventory's status entries are updated (planned → active) after
runtime verification.

## Development infrastructure (not a customer-data subprocessor)

| Provider | Role | Determination |
|---|---|---|
| **GitHub** | Private source-code repository + CI | Processes source code and **synthetic** test fixtures only. No real dealership operational data, no customer data, and no secrets are in the repository (full-history audit clean, 2026-08-19; real exports and databases are exclusion-listed and verified absent). CI runs against synthetic data and disposable containers. GitHub is therefore listed as development infrastructure, **not** as a subprocessor of dealership data — the deliberate determination Rail L asked for |

## Planned — not currently active

| Provider | Role | Status |
|---|---|---|
| Inbound-email provider (e.g. Resend or equivalent) | Scheduled vendor-report delivery (automated acquisition plan) | **Deferred / not active.** The automated vendor-report acquisition this would serve is deferred by owner decision pending pilot/contract authorization and required vendor evidence — no such provider processes anything today, and none activates in v1.1. When adopted, this inventory, the Privacy Policy, and the retention record must be amended first (the recorded Rail L delta rule) |

## Change process

Provider additions or changes that affect dealership data will be
reflected here before they take effect, with the document's
version/date updated. [OWNER/v2: a customer-notification commitment
for subprocessor changes is a commercial (v2) obligation — recorded
in `LEGAL_READINESS.md` §7, deliberately not promised for the
internal beta.]
