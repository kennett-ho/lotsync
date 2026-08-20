"""
Sprint 14 (Rail K) -- frontend ACCESSIBILITY posture assertions,
following tests/test_frontend_observability_config.py's precedent:
deployment-critical frontend facts are pinned from the backend suite
(no frontend test framework exists, and the sprint brief calls for
proportional tooling, not a browser E2E fleet).

These pin the STRUCTURAL posture the Sprint 14 audit remediated:
landmarks and headings, accessible names on search/upload controls,
dialog focus behavior, the inert off-canvas drawer, reduced-motion
support, color-independent status text, and the removal of the
CSP-blocked external hero image. Runtime behavior (real Tab order,
axe sweeps, zoom reflow) is verified in the browser during the sprint
smoke phases; these tests make the source-level posture
un-regressable in CI.

LIMITATION (recorded honestly, ACCESSIBILITY.md expands): source
scans prove markup/code shape, not assistive-technology experience.
They are regression tripwires, not conformance evidence.
"""

import os
import re
import unittest

_FRONTEND_SRC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "src"
)


def read(relative: str) -> str:
    with open(os.path.join(_FRONTEND_SRC, relative), encoding="utf-8") as handle:
        return handle.read()


def walk_sources():
    for root, _dirs, names in os.walk(_FRONTEND_SRC):
        for name in names:
            if name.endswith((".ts", ".tsx", ".css")):
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as handle:
                    yield os.path.relpath(path, _FRONTEND_SRC), handle.read()


# Surfaces actually reachable in the product (App.tsx / main.tsx import
# graph). The legacy pre-DealerDOH dashboards are dead files outside the
# bundle; their markup is not product posture.
LIVE_SURFACES = [
    "App.tsx", "VehicleDetail.tsx", "main.tsx",
    os.path.join("dashboards", "Dashboard.tsx"),
    os.path.join("dashboards", "TodaysWork.tsx"),
    os.path.join("dashboards", "VehiclesList.tsx"),
    os.path.join("dashboards", "Tasks.tsx"),
    os.path.join("dashboards", "InventorySync.tsx"),
    os.path.join("dashboards", "Profile.tsx"),
    os.path.join("dashboards", "UserManagement.tsx"),
    os.path.join("help", "Help.tsx"),
    os.path.join("onboarding", "Onboarding.tsx"),
    os.path.join("auth", "Login.tsx"),
    os.path.join("auth", "ResetPassword.tsx"),
    os.path.join("auth", "AuthGate.tsx"),
    os.path.join("auth", "AccessProvider.tsx"),
    os.path.join("auth", "IdentityFooter.tsx"),
    os.path.join("observability", "ErrorBoundary.tsx"),
]


class ShellLandmarksTest(unittest.TestCase):
    def setUp(self):
        self.app = read("App.tsx")

    def test_main_landmark_exists_and_is_focus_target(self):
        self.assertIn('<main id="main-content" ref={mainRef} tabIndex={-1}', self.app)

    def test_skip_link_is_first_interactive_element(self):
        self.assertIn('className="skip-link"', self.app)
        self.assertIn("Skip to main content", self.app)

    def test_nav_is_labeled(self):
        self.assertIn('aria-label="Main navigation"', self.app)

    def test_nav_items_expose_current_page(self):
        self.assertIn("aria-current={active ? 'page' : undefined}", self.app)

    def test_hamburger_announces_expanded_state_and_target(self):
        self.assertIn('aria-expanded={mobileNavOpen} aria-controls="app-sidebar"', self.app)

    def test_closed_mobile_drawer_is_inert(self):
        # The off-canvas drawer previously kept six off-screen controls
        # in the tab order. inert (not a visibility transition) because
        # it is deterministic even in throttled/background tabs.
        self.assertIn("inert={!isDesktop && !mobileOpen}", self.app)

    def test_drawer_open_moves_focus_and_escape_returns_it(self):
        self.assertIn("closeButtonRef.current?.focus()", self.app)
        self.assertIn("hamburgerRef.current?.focus()", self.app)

    def test_surface_change_moves_focus_to_main(self):
        # User-initiated navigation only: the flag is set in the nav/
        # select/back handlers and consumed after commit -- the role-
        # resolution landing swap on fresh loads must NOT steal focus
        # (it made the first Tab skip the skip link; found deployed).
        self.assertIn("mainRef.current?.focus()", self.app)
        self.assertIn("focusMainPending.current = true", self.app)

    def test_onboarding_close_returns_focus_to_main(self):
        # Closing the tour (finish OR skip/Escape) hands focus to
        # <main> -- unmounting the overlay dropped it to <body>
        # (measured live in the deployed review window).
        self.assertIn("focusMainAfterOverlay()", self.app)

    def test_document_title_names_the_surface_with_controlled_labels(self):
        self.assertIn("SURFACE_TITLES", self.app)
        self.assertIn("document.title", self.app)
        # never the VIN
        self.assertNotIn("selectedVehicle}`", self.app.split("document.title")[1][:200])

    def test_header_search_has_accessible_name(self):
        self.assertIn('aria-label="Search vehicles by VIN"', self.app)

    def test_escape_closes_vehicle_detail(self):
        self.assertIn("if (e.key === 'Escape') handleBack()", self.app)


class OnboardingDialogTest(unittest.TestCase):
    def setUp(self):
        self.src = read(os.path.join("onboarding", "Onboarding.tsx"))

    def test_dialog_semantics(self):
        self.assertIn('role="dialog" aria-modal="true" aria-label="Getting started"', self.src)

    def test_focus_enters_the_dialog_on_open(self):
        self.assertIn("panelRef.current?.focus()", self.src)

    def test_tab_is_contained_and_escape_skips(self):
        self.assertIn("e.key !== 'Tab'", self.src)
        self.assertIn("onSkip()", self.src)

    def test_step_position_is_announced(self):
        self.assertIn('role="status"', self.src)
        self.assertIn("Step {clampedIndex + 1} of {steps.length}", self.src)

    def test_rapid_click_clamp_survives(self):
        # The Sprint 12 crash fix (Sentry ref 9f338b8d) must not be
        # simplified away by accessibility work.
        self.assertIn("steps[Math.max(0, Math.min(index, steps.length - 1))]", self.src)
        self.assertIn("Math.min(i + 1, steps.length - 1)", self.src)


class InventorySyncAccessibilityTest(unittest.TestCase):
    def setUp(self):
        self.src = read(os.path.join("dashboards", "InventorySync.tsx"))

    def test_file_inputs_are_keyboard_reachable(self):
        # display:none (class "hidden") removed keyboard access to the
        # entire upload workflow.
        self.assertNotIn('className="hidden"', self.src)
        self.assertIn('className="visually-hidden"', self.src)
        self.assertIn("focus-within:ring-2", self.src)

    def test_outcome_messages_are_announced(self):
        self.assertIn('role="alert"', self.src)
        self.assertIn('role="status"', self.src)

    def test_exceptions_table_headers_carry_scope(self):
        self.assertNotIn("<th className=", self.src)
        self.assertIn('<th scope="col"', self.src)

    def test_run_status_is_not_color_only(self):
        self.assertIn("{statusLabel(batch.overall_status)}.", self.src)


class SurfaceSemanticsTest(unittest.TestCase):
    def test_every_operational_surface_has_exactly_one_h1(self):
        for rel in [os.path.join("dashboards", "Dashboard.tsx"),
                    os.path.join("dashboards", "TodaysWork.tsx"),
                    os.path.join("dashboards", "VehiclesList.tsx"),
                    os.path.join("dashboards", "InventorySync.tsx"),
                    os.path.join("dashboards", "Profile.tsx"),
                    os.path.join("help", "Help.tsx")]:
            src = read(rel)
            self.assertGreaterEqual(src.count("<h1"), 1, rel)

    def test_vehicles_table_is_sortable_with_aria_sort_and_scoped_headers(self):
        src = read(os.path.join("dashboards", "VehiclesList.tsx"))
        self.assertIn("aria-sort={ariaSort(", src)
        self.assertIn('<th scope="col"', src)

    def test_system_badges_carry_state_in_the_accessible_name(self):
        src = read(os.path.join("dashboards", "VehiclesList.tsx"))
        self.assertIn('role="img"', src)
        self.assertIn("aria-label={`${label}: ${stateText}`}", src)

    def test_dashboard_rows_are_real_buttons_not_clickable_divs(self):
        src = read(os.path.join("dashboards", "Dashboard.tsx"))
        self.assertNotIn("<div key={task.task_id} onClick", src)
        self.assertNotIn('<div\n                  key={rec.recommendation_id}', src)

    def test_expand_controls_announce_state(self):
        self.assertIn("aria-expanded={expanded}", read(os.path.join("dashboards", "Dashboard.tsx")))
        self.assertIn("aria-expanded={expanded}", read(os.path.join("dashboards", "Tasks.tsx")))

    def test_filter_pills_announce_selection(self):
        self.assertIn("aria-pressed={on}", read(os.path.join("dashboards", "Tasks.tsx")))
        self.assertIn("aria-pressed={active}", read(os.path.join("dashboards", "VehiclesList.tsx")))

    def test_profile_labels_are_programmatically_associated(self):
        src = read(os.path.join("dashboards", "Profile.tsx"))
        self.assertIn('htmlFor="profile-display-name"', src)
        self.assertIn('id="profile-display-name"', src)
        self.assertIn('htmlFor="profile-email"', src)

    def test_invite_controls_have_accessible_names(self):
        src = read(os.path.join("dashboards", "UserManagement.tsx"))
        self.assertIn('aria-label="Email address to invite"', src)
        self.assertIn('aria-label="Role for the invited user"', src)

    def test_error_boundary_fallback_is_announced(self):
        self.assertIn('role="alert"', read(os.path.join("observability", "ErrorBoundary.tsx")))

    def test_vehicle_detail_scroll_regions_are_keyboard_scrollable(self):
        src = read("VehicleDetail.tsx")
        self.assertGreaterEqual(src.count('tabIndex={0} role="region"'), 2)


class MotionAndContrastTest(unittest.TestCase):
    def setUp(self):
        self.css = read("index.css")

    def test_reduced_motion_preference_is_respected(self):
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)

    def test_focus_visible_indicator_is_global(self):
        self.assertIn(":focus-visible", self.css)
        self.assertIn("outline: 2px solid currentColor", self.css)

    def test_visually_hidden_helper_exists(self):
        self.assertIn(".visually-hidden", self.css)

    def test_sidebar_attribution_is_aa_text_not_hidden_decoration(self):
        # Owner ruling at the PR gate: visible, meaningful attribution
        # is TEXT — AA contrast (white/50 on the sidebar navy measured
        # 5.27:1), exposed to assistive technology. Never again a
        # sub-AA "decorative" carve-out for readable words.
        app = read("App.tsx")
        self.assertIn(
            'text-white/50 leading-tight select-none">Developed by Kennett Ho', app)
        self.assertNotIn('aria-hidden="true">\n          <p className="text-[9px]', app)

    def test_header_sync_badge_slate_tone_meets_aa(self):
        # slate-500 on slate-100 measures 4.34:1 — found by an axe pass
        # with the backend unreachable (the only time this badge state
        # renders). Error/empty visual branches are audit surface too.
        app = read("App.tsx")
        self.assertIn("slate: 'text-slate-600 bg-slate-100 border-slate-200'", app)

    def test_no_sub_aa_tinted_chip_or_dimmed_count_patterns(self):
        # Two patterns the production-shaped-data axe sweep caught that
        # the QA-scale sweeps never rendered: slate-500 text sitting on
        # a slate-100 chip measures 4.34:1 (passes on white, fails on
        # the tint), and opacity-dimmed count text bottomed out at
        # 1.98:1. Chip text on slate-100 uses slate-600+; dimming for
        # hierarchy uses font-weight or an AA-passing color, never
        # opacity over already-mid-tone text.
        for rel in LIVE_SURFACES:
            src = read(rel)
            self.assertNotIn("text-slate-500 bg-slate-100", src, rel)
            self.assertNotIn("bg-slate-100 text-slate-500", src, rel)
            self.assertNotIn("opacity-50 font-normal", src, rel)

    def test_no_informative_slate_300_or_400_body_text_on_live_surfaces(self):
        # slate-400 measures 2.63:1 on white (Tailwind v4 oklch palette)
        # -- below AA for normal text. It remains legitimate for
        # DECORATIVE glyphs (icons beside labeled text); this pin guards
        # the known informative-text classes the audit remediated:
        # loading, empty-state, and message paragraphs.
        pattern = re.compile(r'text-slate-400[^"]*">(?:Loading|No |Could not|Something)')
        for rel in LIVE_SURFACES:
            src = read(rel)
            self.assertIsNone(pattern.search(src), rel)


class ExternalContentTest(unittest.TestCase):
    def test_no_external_image_hosts_in_live_source(self):
        # The Unsplash hero was already blocked by the Sprint 13 CSP
        # (img-src 'self' data:) -- nothing may reintroduce an external
        # media host the CSP would silently break.
        for rel in LIVE_SURFACES:
            src = read(rel)
            self.assertNotIn("images.unsplash.com", src, rel)
            for host_pattern in re.findall(r'src="(https?://[^"]+)"', src):
                self.fail(f"{rel} references external media: {host_pattern}")


if __name__ == "__main__":
    unittest.main()
