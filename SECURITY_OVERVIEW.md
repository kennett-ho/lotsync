# DealerDOH Security Overview

> **DRAFT — NOT PUBLISHED.**
> A customer-facing summary of security practices, written strictly
> from the verified internal records (`SECURITY_ARCHITECTURE.md`,
> `SECURITY_AUDIT.md`, `OBSERVABILITY.md`) — it deliberately
> publishes practices and posture, not internal threat-model detail.
> Describes the **v1.1 stack**. Owner decisions resolved 2026-08-20
> (`LEGAL_READINESS.md` §5): publication on `dealerdoh.com`
> (`/security` if appropriate) before the v1.1 production cutover
> (D5), once the monitored contact exists (D2), with provider
> statements re-verified against actual plans first (D8). D9
> disposition: beta/evaluation readiness material; no attorney
> review has been completed for the v1.1 controlled beta.

**Last reviewed:** 2026-08-20 · **Version:** draft-1

---

## What this covers

How DealerDOH protects the dealership operational data and staff
account information it processes. Scope of that data — deliberately
narrow, with **no customer/consumer personal or financial
information** — is described in the
[Privacy Policy](PRIVACY_POLICY.md).

## Access and identity

- Sign-in is by **administrator invitation only** — no public
  signup. Passwords and sign-in are handled by a dedicated identity
  provider (Supabase Auth); DealerDOH never stores passwords.
- Every request is **authorized on the server**: cryptographic
  token verification plus a live membership check (role and
  dealership) on each request. Removing someone's access takes
  effect on their very next request.
- Role-based authorization is enforced server-side (for example,
  only managers/admins can run inventory syncs or administer
  users); UI visibility is never the security boundary.
- Each deployment serves **one dealership**; a member of another
  store is denied by the server regardless of what their request
  claims.

## Data in transit and at rest

- All traffic is encrypted in transit (**HTTPS/TLS**) between
  browser, application, identity provider, and database.
- Data at rest lives on managed infrastructure providers
  (see [`SUBPROCESSORS.md`](SUBPROCESSORS.md)); at-rest protections
  are those providers' platform controls. DealerDOH does not add
  application-layer encryption at rest and does not claim
  otherwise.

## Application protections

- **Ingestion safety:** uploaded reports pass a validation boundary
  before anything can change — content-based file identification,
  size/format/structure checks, and suspicious-change detection
  that requires explicit human acknowledgement. Invalid files
  change nothing.
- **Hardened web surface:** strict Content-Security-Policy and
  security headers on the frontend; security headers, an explicit
  CORS allowlist, and no-store caching on the API; no cookies used
  for authentication (which structurally removes CSRF risk).
- **Least data in telemetry:** error monitoring and analytics are
  configured to exclude personal identity, credentials, and report
  contents — enforced by automated tests, with layered redaction on
  the server (details: the Privacy Policy's telemetry section).

## Engineering practice

- **Security review with evidence:** a structured audit (read-only
  audit → remediation → re-audit) was completed in August 2026 with
  **zero critical and zero reachable-high findings open**;
  accepted/deferred items are tracked with rationale internally.
- **Continuous checks in CI:** secret scanning and
  production-dependency vulnerability audits run as hard gates on
  every change; the full test suite (both database engines) and
  frontend build must pass.
- **Secret handling:** real credentials exist only in deployment
  environments and the operator's password manager — never in
  source control (verified across the repository's full history).

## Backups and continuity

Current beta posture, stated honestly: the production database has a
**verified manual backup procedure** (integrity-checked, stored off
the production host); backups are not yet on an automated schedule.
Moving production to a paid managed-database tier is a planned,
recorded step of the v1.1 release plan; its specific backup and
retention capabilities will be verified against the actual plan
before this document relies on them. There is **no uptime SLA**
during the beta.

## Incident response

Failures and anomalies surface through error monitoring and
structured, request-correlated logs with a named responsible
operator. A documented internal procedure covers triage, scoping,
evidence preservation, provider coordination, and case-specific
assessment of any notification duties.

## What we do not claim

No SOC 2, ISO 27001, HIPAA, PCI DSS, or GLBA certification or
attestation; no formal WCAG conformance (see the
[Accessibility Statement](ACCESSIBILITY_STATEMENT.md)); no uptime,
encryption-at-rest, or data-residency guarantees. If a claim is not
on this page, DealerDOH is not making it.

## Reporting a security concern

Please report suspected vulnerabilities or security concerns to
[AT PUBLICATION — D2 (resolved 2026-08-20): the monitored
`dealerdoh.com` contact address, created before publication].
Good-faith reports are welcome; we will acknowledge, investigate,
and fix verified issues.
