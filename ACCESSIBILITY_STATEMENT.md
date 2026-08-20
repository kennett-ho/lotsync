# DealerDOH Accessibility Statement

> **DRAFT — OWNER REVIEW REQUIRED — NOT PUBLISHED.**
> Derived strictly from the Sprint 14 (Rail K) audit record in
> [`ACCESSIBILITY.md`](ACCESSIBILITY.md) — every sentence below is
> backed by that document's evidence. Publication blocks on owner
> decisions D2 (feedback contact) and D5 (venue/timing) in
> `LEGAL_READINESS.md` §5.

**Last reviewed:** 2026-08-20 (against the Sprint 14 audit,
completed 2026-08-20) · **Version:** draft-1

---

## Our commitment

DealerDOH is a working tool for dealership staff, and it should be
operable by everyone on that staff. Accessibility is treated as an
engineering requirement with evidence, not a marketing statement.

## Current status — stated precisely

DealerDOH has been **audited and remediated toward WCAG 2.2
AA-quality behavior across the tested v1.1 workflows**.

DealerDOH does **not** claim formal WCAG 2.2 AA conformance or any
certification. Automated checks, structural tests, and manual
keyboard/contrast verification are evidence of quality; they are not
a conformance assessment, and no assistive-technology user study has
been completed yet.

## What has been verified

On the core workflows (sign-in, dashboard, vehicles and vehicle
detail, tasks, inventory sync, work-order generation, profile and
user management):

- **Full keyboard operability** — skip link first, visible focus
  throughout, no keyboard traps; modal dialogs contain focus and
  close with Escape; the mobile navigation drawer manages focus
  correctly.
- **Screen-reader-relevant structure** — landmarks, one h1 per
  surface, labeled form controls, status/error announcements via
  live regions, meaningful accessible names on controls and status
  badges; status is never conveyed by color alone.
- **Contrast** — text and essential UI measured against WCAG AA,
  including production-scale data states and error/empty states
  (measured directly; automated tooling under-reports the app's
  color space, so direct measurement is the authority).
- **Zoom and mobile** — core flows reflow without horizontal
  scrolling at phone width and at 200%-zoom-equivalent viewports;
  touch targets meet the WCAG 2.2 minimum on those flows.
- **Reduced motion** — the interface honors
  `prefers-reduced-motion`.
- Automated scanning (axe-core) reports **zero violations** on all
  five audited surfaces, at desktop and phone viewports, at
  production data scale — supporting evidence, not a conformance
  claim.

## Known limitations (honest list)

- **No assistive-technology user study yet** — structural and
  accessibility-tree evidence only; a human screen-reader pass is
  planned as part of user acceptance testing.
- **The generated work-order PDF** prints cleanly with readable,
  logically-ordered text but is **not** a tagged/PDF-UA document.
- **Windows High Contrast / forced-colors mode** has not been
  specifically audited.
- **Voice control** has the naming prerequisite in place (accessible
  names match visible labels) but no dedicated verification pass
  yet.
- Legacy screens outside the current application are not audited
  (they are unreachable in the product).

## Feedback

If you hit an accessibility barrier in DealerDOH, please tell us —
it will be treated as a defect, not a request:
[OWNER: monitored contact address — decision D2].
