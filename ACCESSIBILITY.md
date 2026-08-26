# DealerDOH Accessibility (Sprint 14 — Rail K)

**Status: canonical.** DealerDOH's accessibility target, the Sprint 14
audit and remediation record, the interaction model every future
surface must follow, and the honest limits of what has been verified.
Amend in the same PR as any behavior change it describes. Rail
contract: `V1_1_RELEASE_READINESS.md` §5.K.

**Target and claim discipline:** the engineering target is
**WCAG 2.2 AA-quality behavior** on the real dealership workflows.
DealerDOH does **not** claim formal WCAG 2.2 AA conformance —
automated checks and structural tests are evidence, not
certification, and no assistive-technology user study has run yet
(that risk is carried into Rail M UAT). The accurate sentence is:
*DealerDOH has been audited and remediated toward WCAG 2.2 AA-quality
behavior across the tested v1.1 workflows.*

Sprint 15 (Rail L) derived a draft public
[`ACCESSIBILITY_STATEMENT.md`](ACCESSIBILITY_STATEMENT.md) strictly
from this record — keep the two in sync; the statement must never
claim more than this document proves.

---

## 1. Audit methodology (Sprint 14)

Four passes over the integrated product (not just Sprint 12's files),
on the Sprint 14 branch from `dev` = `73dee99`:

1. **Semantic source review** of every live surface (the App/main
   import graph; the legacy pre-DealerDOH dashboards are dead files
   outside the bundle and were excluded).
2. **Automated scans** — axe-core 4.10.2 against the running app on
   Dashboard/Overview, Vehicles, Tasks, Vehicle Detail, Inventory
   Sync, Profile, at desktop and phone viewports, at QA and
   production-shaped data scale.
3. **Browser accessibility-tree and computed-style inspection** —
   landmark/name verification, and canvas-resolved contrast
   measurement of the Tailwind v4 oklch palette (axe under-reports
   oklch contrast — a recorded tooling limitation; the direct
   measurements are the authority).
4. **Keyboard walkthroughs** — real Tab-key traversal on the local
   app; deployed authenticated walkthroughs are part of the sprint's
   DEV smoke phases.

Findings were classified Critical / Serious / Moderate / Minor.
Complete remediation landed in the same sprint; the table in §3 maps
finding → fix → guard.

### Automated results

| | Before | After |
|---|---|---|
| axe, five audited surfaces | `button-name` (critical) ×5 · `scrollable-region-focusable` (serious) ×2 · `region` ×20–116/surface · `landmark-one-main`, `page-has-heading-one`, `landmark-unique`, `heading-order`, `aria-prohibited-attr` ×300, `color-contrast` | **0 violations** on every audited surface |

Follow-up findings closed at the PR gate and in the deployed
feature-branch review window — each one a render branch the original
QA-scale sweeps never painted, which is itself the lesson:

- **Owner ruling — attribution is text.** The sidebar's "Developed by
  Kennett Ho" signature was initially carried as an `aria-hidden`
  decorative exemption; the ruling is that **visible, meaningful
  attribution is text**. It now meets AA (white/50 on the sidebar
  navy, canvas-measured **5.27:1** — re-confirmed on the deployed
  build) and is exposed to assistive technology; subtlety comes from
  its 9px size and placement, never sub-AA contrast.
- **No-backend states:** the header sync badge's slate tone ("Sync
  Status Unavailable" / "No Syncs Yet") measured 4.34:1 — it only
  renders with the backend unreachable/empty. Fixed to slate-600
  (deployed stylesheet measures **6.92:1**).
- **Production-shaped-data states:** re-running axe against the
  production-shaped dataset surfaced tones the 34-vehicle QA set
  never triggers: slate-500 text on slate-100 chips (count pills,
  ratification/"Sold"/"N open" badges — 4.34:1 on the tint despite
  passing on white), opacity-dimmed filter-chip counts (**1.98:1**),
  the active-chip count on a lightened blue (3.75:1), the "· done/
  total" fraction (2.4:1), one missed timeline date at slate-400,
  and emerald/amber-600 status text (3.2–3.69:1) on system-status
  rows and pills. All fixed to AA-passing tones (slate-600 on tints,
  700-series status text, weight-based dimming instead of opacity);
  large bold stat values (22–28px) legitimately pass at the 3:1
  large-text threshold and were deliberately left.

Final axe including every one of these: **0 violations** on all five
audited surfaces, at the production data shape.

---

## 2. The interaction model (what future surfaces must follow)

- **Native elements first.** Buttons are `<button>`, tables are
  `<table>` with `scope`d headers, labels are `<label>` (wrapped or
  `htmlFor`). ARIA states what native HTML cannot: `aria-current` on
  nav, `aria-expanded` on disclosure toggles, `aria-pressed` on
  filter pills, `aria-sort` on sortable headers, `role="img"` +
  name on glyph-like status badges. No ARIA where native semantics
  already say it.
- **Landmarks & structure.** One `<main id="main-content">` per view;
  the nav is a labeled `<nav>`; secondary `<aside>`s carry their own
  labels; every surface has exactly one h1 and h2 sections beneath
  it; the document title names the surface (controlled labels only —
  never a VIN).
- **Keyboard.** A skip link is the first tabbable element. State
  navigation focuses `<main>` (the SPA page-load equivalent). Escape
  closes the overlay-like Vehicle Detail. Scroll regions without
  interactive children are focusable, labeled regions. Nothing
  focusable is ever visually hidden: the closed mobile drawer is
  `inert` (chosen over a visibility transition because inert is
  deterministic even in throttled background tabs).
- **Modals.** The onboarding tour is the reference implementation:
  `role="dialog" aria-modal`, focus moves into the panel on open, Tab
  is contained, Escape dismisses with the same never-nag semantics as
  Skip, the step position is announced (`role="status"`), and closing
  hands focus back through the app's surface-focus seam. The Sprint
  12 rapid-click clamp is load-bearing and test-pinned.
- **Status & errors.** Outcomes users must notice announce
  themselves: `role="alert"` for failures/warnings (validation
  rejected, run failed, work-order failed, boundary fallback),
  `role="status"` for quiet confirmations (validation finished, sync
  complete, loading states). Not every repaint is an announcement —
  live regions are reserved for outcomes.
- **Color is never the only channel.** Status text accompanies every
  status dot (visually or via visually-hidden text); system badges
  carry their state in the accessible name; priorities/severities
  show text labels.
- **Contrast.** Informative text uses slate-500+ on light surfaces
  (slate-400 measures 2.63:1 in the v4 oklch palette — below AA;
  it remains legitimate only for decorative glyphs beside labeled
  text). Status text uses the 700-series tones on tinted chips.
  Focus visibility is a global `:focus-visible` 2px `currentColor`
  outline — legible on the dark sidebar, white cards, and active-blue
  controls alike (custom input rings keep their own treatment).
- **Motion.** `prefers-reduced-motion: reduce` collapses all
  animation/transition time app-wide; meaning never rides on motion
  (spinners always have text).
- **Touch.** Interactive targets meet the WCAG 2.2 minimum
  pragmatically (24px+); the app reflows to card layouts below `lg`
  with no horizontal page scroll at 375 px or the 200%-zoom-
  equivalent 640 px viewport.

## 3. Sprint 14 finding → remediation map (abridged; severity at audit)

| Finding (severity) | Fix | Guard |
|---|---|---|
| Closed mobile drawer kept 6 invisible controls tabbable; no focus handling, no Escape, no `aria-expanded` (Serious) | `inert` when closed below `lg`; open focuses Close, Escape closes and refocuses the hamburger; `aria-expanded`/`aria-controls` | `test_frontend_accessibility.py` (ShellLandmarks) |
| Onboarding dialog: no focus entry/containment/Escape; step invisible to AT (Serious) | Real modal behavior; Escape = Skip; step announced; clamp preserved | OnboardingDialog tests |
| Dashboard recommendation rows + expanded task rows were clickable `<div>`s (Serious) | Real buttons | SurfaceSemantics tests |
| File upload inputs `display:none` — keyboard-unreachable (Serious) | Visually-hidden focusable inputs + focus-within ring | InventorySync tests |
| Vehicle Detail: no focus management, no h1, 5 dead unnamed icon buttons, unscrollable-by-keyboard panels (Serious/Critical per axe) | Surface-focus seam + Escape; identity h1; dead buttons removed; labeled focusable regions | Shell + SurfaceSemantics tests |
| Searches (header/vehicles/exceptions) placeholder-only; unnamed clear button (Serious) | `aria-label`s; labeled 24px clear button | Shell + surface tests |
| Informative text at slate-400/300, status text at amber-600/emerald-600/red-500 on white — below AA (Serious, widespread) | Palette-preserving shade bumps (500/700-series); measured | MotionAndContrast test |
| Async outcomes not announced (Serious) | `role="alert"`/`role="status"` per §2 | InventorySync + surface tests |
| No main/skip link/titles/`aria-current`; heading gaps; landmark collisions (Moderate) | Full shell semantics per §2 | Shell tests |
| Status by dot color alone in sync history rows; sortable/sort state color-only; filter selection color-only (Moderate) | Visually-hidden status text; `aria-sort`; `aria-pressed` | surface tests |
| No reduced-motion handling (Moderate) | Global reduce block | MotionAndContrast test |
| Profile/User-Management label association gaps (Moderate) | `htmlFor`/`id`; named invite controls | SurfaceSemantics tests |
| Unsplash hero image — external host, already CSP-blocked, not the actual vehicle (cross-cutting) | Removed; badge moved to identity card; external-media scan added | ExternalContent test |
| PR-gate follow-ups (owner review): visible attribution carried as decorative exemption; slate sync-badge tone 4.34:1 in error/empty states (Minor) | Signature → AA text at white/50 (5.27:1 measured), AT-exposed; badge slate tone → slate-600; no-backend axe pass added to the playbook | MotionAndContrast test (signature AA + badge tone) |

Already good and deliberately untouched: Login/Reset/Profile's
wrapped-label + `role="alert"` patterns (Sprint 09), honest empty
states, pending-state buttons with double-submit guards, enumeration-
safe auth copy, the Error Boundary (now announced).

## 4. Verified workflows & evidence

- **Automated:** axe zero-violation sweeps (§1) at desktop + mobile
  viewports, QA + production data scale; 47 structural posture tests
  (`tests/test_frontend_accessibility.py`,
  `tests/test_frontend_performance.py`) in CI on both engines.
- **Manual, local:** real Tab-key walkthroughs (skip link first,
  visible focus, drawer open/close/Escape focus cycle, dialog
  containment); 375 px and 640 px (200%-zoom-equivalent) reflow with
  zero horizontal scroll on Overview/Vehicles/Tasks/Detail;
  contrast measurements canvas-resolved from the live palette.
- **Deployed (feature-branch review window, authenticated Lot
  Staff):** zero console/CSP violations on a fresh tab with the lazy
  chunk graph live; Vehicle Detail open/Escape focus cycle; truthful
  breadcrumb; drawer inert-closed → focus-on-Close → Escape →
  hamburger cycle; onboarding replay with real-key Tab containment
  both directions, Back/Next operation, live step announcements, and
  Escape-close (which exposed and fixed the focus-to-body gap);
  Sold filter via `aria-pressed`; keyboard-operated work-order
  generation; phone-width Today's Work → Detail → back with zero
  horizontal scroll and zero sub-24px targets; 640 px
  zoom-equivalent pass; signature (5.27:1) and badge (6.92:1) tones
  measured from the deployed stylesheet.
- **Deployed (review window, authenticated Manager, final head):**
  fresh authenticated load keeps document-start focus and the FIRST
  real Tab reveals the skip link (the seam fix live); Enter on it
  lands focus in `<main>`; Overview h1/landing with real-button
  recommendation rows and `aria-expanded` groups; lazy Inventory
  Sync chunk on nav; the visually-hidden file input takes keyboard
  focus with the label's focus-within ring; a zero-mutation
  validate-only pass announced its outcome live (`role="status"`
  "Validated … nothing has been changed yet", Rejected verdict
  rendered, Run stayed disabled); lazy Profile chunk with the
  `htmlFor`/`id` display-name pair, labeled invite email/role
  controls, roster loaded; onboarding replay Escape-close returned
  focus to `<main>` (the overlay fix live); Vehicle Detail
  open/Escape cycle with the truthful "Vehicles" breadcrumb.

## 5. Known limitations (tracked, honest)

| Item | State |
|---|---|
| Screen-reader user study | Not performed — structural + tree evidence only; carried as a Rail M UAT risk |
| Work-order PDF | Readable text, logical order, sufficient contrast, prints cleanly (reviewed proportionally); **not** a tagged/PDF-UA document and no such claim is made — formal PDF accessibility exceeds v1.1 scope |
| axe + oklch | axe 4.10 under-reports contrast on oklch colors; contrast evidence here comes from direct measurement (recorded tooling limitation) |
| Error/empty-state and data-shape visual branches | Audit sweeps must include unreachable-backend states AND production-shaped data — the slate sync-badge, tinted-chip, and dimmed-count contrast gaps all hid in branches the happy-path QA-scale sweeps never painted (§1); the playbook now requires both passes, and structural pins forbid the two failing patterns |
| axe on the deployed origin | The Sprint 13 CSP (`script-src 'self' https://*.posthog.com`, no `unsafe-eval`/`blob:`) blocks injecting axe into the deployed pages — the security control working as designed. Deployed axe evidence is therefore the SAME final build run locally (identical app code; only baked env differs) plus accessibility-tree/computed-style checks performed directly on the deployed origin |
| Legacy dead dashboards | Unaudited by design — outside the bundle graph, unreachable |
| Windows High Contrast / forced-colors | Not specifically audited this sprint |
| Voice control | Accessible names now match visible labels (the prerequisite); no dedicated voice-control pass yet |

## 6. QA expectations

Keyboard-only operation of login → landing → vehicles/detail → tasks
→ (manager) sync validation/run → profile must succeed with visible
focus at every step; the drawer and onboarding must contain and
return focus as §2 describes. `DEV_QA_GUIDE.md` carries the
per-role click-path expectations; any regression here is
release-blocking under §5.K's blocking subset.
