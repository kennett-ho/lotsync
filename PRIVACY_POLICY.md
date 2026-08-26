# DealerDOH Privacy Policy

> **DRAFT — NOT IN EFFECT, NOT PUBLISHED.**
> Describes the **DealerDOH v1.1 internal-beta stack**
> (authenticated, Supabase/Render/Vercel architecture) — never the
> current unauthenticated LotSync beta. Owner decisions D1–D10 are
> **resolved** (2026-08-20, `LEGAL_READINESS.md` §5): this draft now
> carries the decided operating identity (D1), U.S.-only scope
> (D3), notice-only acceptance model (D6), and customer-neutral
> naming (D7). Publication happens on `dealerdoh.com` (planned
> `/privacy`) **before the DealerDOH v1.1 production cutover** (D5)
> — never on current LotSync production — and only after the
> monitored `dealerdoh.com` contact exists (D2) and the owner
> approves the final text. **Attorney-review disposition (D9),
> recorded honestly: no attorney review has been completed for the
> v1.1 controlled beta; this is a beta/evaluation readiness
> document; qualified legal review is recommended/required before
> commercial GA / v2 contractual deployment. Nothing here has been
> reviewed or approved by counsel.** Grounding for every statement:
> `PRIVACY_ARCHITECTURE.md`.

**Effective date:** [OWNER: actual publication date — do not
backdate] · **Version:** draft-1 (Git-versioned; see § "Changes")

---

## Who we are

DealerDOH ("we") is a dealership operations product **operated by
Kennett Ho** (per resolved decision D1, no separate corporate
entity exists or is implied; a future legal entity may replace this
identity before commercial availability). It is currently offered
as an **internal beta** to authorized staff of a participating
dealership — access is by administrator invitation only; there is
no public signup. DealerDOH v1.1 is offered in the **United States
only**; no international availability or compliance is claimed.

This policy covers the DealerDOH application (web app and its API).
It is written for the people who use it: dealership staff.

## What DealerDOH is for

DealerDOH aggregates the dealership's own operational evidence about
its **vehicle inventory** — inventory reports, key-cabinet state,
tracking-device state, reconditioning state — and turns it into
history, tasks, and recommendations for dealership staff. It is an
operations tool about vehicles and work, not about people, and not
about the dealership's customers.

## Information we process

**Account information (about you).** When your administrator invites
you, DealerDOH's sign-in provider (Supabase) processes your **work
email address and the password you choose** (DealerDOH itself never
stores your password), plus sign-in/session state. You may set an
optional **display name**. DealerDOH's own database stores only your
account's internal identifier together with your **role and
dealership assignment**, which control what you can do. Your email
and display name are visible to your dealership's
administrators/managers on the user-management screen.

**Vehicle and operational data (about the dealership's work).**
Vehicle identifiers (VIN, stock number, year/make/model text),
per-system status, event history, tasks, and recommendations —
derived from reports your dealership's authorized staff upload from
its own vendor systems. This data is about vehicles and dealership
operations. **DealerDOH does not collect or store customer/consumer
personal information: no customer names, contact details,
driver's-license data, financing, credit, or payment information.**
One honest nuance: uploaded vendor report files are kept as files
exactly as exported (see Retention below), and vendor-entered
free-text fields (for example a reconditioning note) can incidentally mention a staff
member's name; such text is shown as operational history and is
never used for analytics.

**Product telemetry.** To operate and improve DealerDOH we collect:
- **Error reports** (Sentry): what broke, technical context, and a
  request reference. Configured to exclude personal identity — no
  account identity is attached, and request bodies, cookies, and
  identifying URL segments are stripped or masked.
- **Usage analytics** (PostHog): a small set of named product events
  (for example "page viewed", "sync completed"). Your analytics
  identity is your internal account identifier — never your email or
  name. There is **no session recording, no keystroke or form
  capture, no automatic click harvesting**.
- **Server logs**: request records with internal identifiers, route
  patterns, timing, and outcomes — configured to exclude emails,
  names, vehicle identifiers, and report contents.

**Platform data.** Like essentially all web services, the
infrastructure providers that host and protect DealerDOH (see
"Service providers") process **IP addresses and standard
connection/browser metadata** in their access logs and ingestion
systems as part of operating the service. DealerDOH's own
application records do not store IP addresses.

## Where information comes from

From you (sign-in, your display name, your actions in the app); from
your dealership's administrators (your invitation, role, and
offboarding); and from the vendor reports your dealership's
authorized staff upload.

## How we use information

To operate the service (authentication, authorization, the
product's core evidence/task features); to keep it working and
secure (error monitoring, logs, incident response); and to
understand product usage so we can improve it (the bounded analytics
above). **We do not sell personal information. We do not share it
for advertising. There is no advertising, profiling, or data
monetization of any kind in DealerDOH.**

## Cookies and similar technologies

DealerDOH **sets no cookies**. Your login session and analytics
state are kept in your browser's local storage: a session entry
(so you stay signed in across refreshes; removed at sign-out) and
analytics entries (internal identifiers only; severed at sign-out).
There is no cross-site tracking and nothing here is used for
advertising.

## Service providers

DealerDOH runs on a small set of infrastructure providers — hosting
(Vercel, Render), sign-in and database (Supabase), error monitoring
(Sentry), and product analytics (PostHog) — each processing only
what its role requires. The current list, with what each one
processes, is maintained in [`SUBPROCESSORS.md`](SUBPROCESSORS.md).
All are currently configured in United States regions; this reflects
current configuration rather than a contractual residency guarantee.

## Security

Access requires sign-in and an active membership granted by your
dealership's administrator; every request is re-authorized on the
server. Traffic is encrypted in transit (HTTPS). Uploads pass a
validation boundary before they can affect anything. A summary of
security practices is published in
[`SECURITY_OVERVIEW.md`](SECURITY_OVERVIEW.md). No security is
perfect, and we make no certification claims — see that document
for what is and is not in place.

## Retention

- **Account/membership records** are kept while your dealership uses
  DealerDOH. Offboarding **deactivates** access immediately; the
  membership record is retained for operational accountability.
- **Operational history** (vehicles, events, tasks) is the product's
  purpose and is retained for the life of the dealership
  relationship.
- **Uploaded report files** are temporary operational evidence, not
  archives. The adopted policy keeps an uploaded file for up to
  **7 days** after it is successfully processed and up to **30
  days** when it was rejected or held for review, then deletes it.
  *[Editorial gate — publish this bullet only once the
  bounded-retention implementation is live; until then the accurate
  statement is that uploaded files are retained pending that
  implementation — `DATA_RETENTION.md` §3.]*
- **Telemetry** is retained on the providers' schedules (error
  events on the order of weeks to months; product events on the
  order of a year on current plans).
- The full, honest retention record — including the implementation
  status of each policy — is [`DATA_RETENTION.md`](DATA_RETENTION.md).

## Your choices

You can set or change your display name in Settings, and use the
password-reset flow at any time. To access, correct, or ask about
information connected to your account — or to request offboarding —
contact [AT PUBLICATION — D2: the monitored `dealerdoh.com`
contact address, created before this policy is published; one
address may serve both support and privacy] or your dealership
administrator. We will handle requests honestly and
manually; this is a small internal beta and we do not promise
statutory response timelines that do not apply to it.

## Children

DealerDOH is a workplace operations tool for dealership staff. It is
not directed to children and we do not knowingly collect information
from anyone under 13.

## Changes to this policy

Policies are version-controlled. Material changes will be dated and
announced to the dealership before they take effect; the change
history is preserved in the document repository.

## Contact

[AT PUBLICATION — D2 (resolved 2026-08-20): a real, monitored
`dealerdoh.com` contact address will be created **before** this
policy is published; one address may initially serve both support
and privacy functions. **This document must not be published while
this placeholder remains — placeholder addresses are never
published as real contact information.**]
