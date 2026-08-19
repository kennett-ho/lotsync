"""
Sprint 12 (Rails B + C) -- role-aware UX POSTURE assertions, following
the tests/test_frontend_config.py / test_frontend_observability_config.py
precedent: pin deployment-critical frontend facts from the backend
suite instead of standing up a frontend test framework for
configuration checks.

What these pin:
- the role -> navigation/landing model (roleNav.ts) including the
  AUTH_MODE=disabled production-safety invariant (generic shape is
  byte-identical to the pre-Sprint-12 shell, and role logic keys off
  the server-confirmed /me identity only);
- no client-side role selection of any kind;
- the audit's honesty fixes cannot regress (no emp-0142 placeholder,
  no permanently-disabled "Coming soon" controls, honest search
  placeholder, no local-only Dismiss);
- the sidebar-navigation-dismisses-Vehicle-Detail fix;
- onboarding storage = Supabase user_metadata (no API/schema surface),
  skip records completion, replay lives in Help;
- the Sold browse addition is the minimal include_sold mode;
- the six new analytics events exist at their seams, are documented
  in ROLE_AWARE_UX.md, and carry no unsafe properties (the Sprint 11
  posture suite already scans every track() call for forbidden
  property keys -- new events are inside that net automatically).

Server authorization is NOT tested here -- tests/test_auth.py and the
inventory-sync/user-management suites keep enforcing it; Sprint 12
changed no backend authorization code.
"""

import os
import re
import unittest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FRONTEND_SRC = os.path.join(_REPO, "frontend", "src")


def read(relative: str) -> str:
    with open(os.path.join(_FRONTEND_SRC, relative), encoding="utf-8") as handle:
        return handle.read()


def read_repo(relative: str) -> str:
    with open(os.path.join(_REPO, relative), encoding="utf-8") as handle:
        return handle.read()


def strip_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$|(?<=[\s;{(])//[^\n]*$", "", source)


# Mockup-era dashboards that App.tsx does NOT import -- unreachable,
# never user-facing, their disposition is governed by
# FRONTEND_BACKEND_RECONCILIATION.md (owner decisions pending), so
# Sprint 12's live-app honesty assertions deliberately skip them.
_DEAD_MOCKUPS = {
    os.path.join("dashboards", name + ".tsx")
    for name in ("Activity", "Controller", "DealerTrades",
                 "IncomingInventory", "LotStaff", "Placeholder",
                 "Requests", "Staging", "TradeIns", "Transportation",
                 "VehicleMovement")
}


def walk_sources(code_only: bool = False, live_only: bool = False):
    for root, _dirs, names in os.walk(_FRONTEND_SRC):
        for name in names:
            if name.endswith((".ts", ".tsx")):
                path = os.path.join(root, name)
                rel = os.path.relpath(path, _FRONTEND_SRC)
                if live_only and (rel.startswith("imports") or rel in _DEAD_MOCKUPS):
                    continue
                with open(path, encoding="utf-8") as handle:
                    content = handle.read()
                yield (rel, strip_comments(content) if code_only else content)


# The pre-Sprint-12 shell these ids/labels must keep reproducing in
# the generic (auth-disabled / role-unresolved) shape.
_LEGACY_NAV = [
    ("dashboard", "Dashboard"),
    ("vehicles", "Vehicles"),
    ("tasks", "Tasks"),
    ("inventory-sync", "Inventory Sync"),
]


class RoleNavigationModelTest(unittest.TestCase):
    def setUp(self):
        self.src = read("roleNav.ts")
        self.code = strip_comments(self.src)

    def test_generic_shape_is_the_legacy_shell(self):
        generic = self.code[self.code.index("GENERIC_NAV"):self.code.index("GENERIC_LANDING")]
        for expected_id, expected_label in _LEGACY_NAV:
            self.assertIn(f"id: '{expected_id}', label: '{expected_label}'", generic)
        # Order preserved exactly.
        positions = [generic.index(f"'{i}'") for i, _ in _LEGACY_NAV]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("GENERIC_LANDING: NavId = 'dashboard'", self.code)

    def test_unknown_or_missing_role_falls_back_to_generic(self):
        self.assertIn("default:\n      return GENERIC_NAV", self.code)
        self.assertIn("role === 'lot_staff' ? 'today' : GENERIC_LANDING", self.code)

    def test_lot_staff_nav_omits_inventory_sync_and_lands_on_today(self):
        lot = self.code[self.code.index("LOT_STAFF_NAV"):self.code.index("SALES_MANAGER_NAV")]
        self.assertNotIn("inventory-sync", lot)
        self.assertIn("'today'", lot)
        self.assertEqual(lot.index("'today'") < lot.index("'vehicles'"), True)

    def test_manager_and_admin_share_the_overview_first_nav(self):
        self.assertIn("case 'admin':\n    case 'manager':\n      return MANAGER_NAV", self.code)
        manager = self.code[self.code.index("MANAGER_NAV"):self.code.index("LOT_STAFF_NAV")]
        self.assertIn("label: 'Overview'", manager)
        self.assertIn("inventory-sync", manager)

    def test_sales_manager_gets_shared_surfaces_without_sync_control(self):
        sales = self.code[self.code.index("SALES_MANAGER_NAV"):self.code.index("SYNC_CONTROL_ROLES")]
        self.assertNotIn("inventory-sync", sales)
        self.assertNotIn("'today'", sales)


class RoleSourceTest(unittest.TestCase):
    """The role can only come from the server-confirmed identity."""

    def test_app_reads_role_from_me_and_requires_authenticated(self):
        app = strip_comments(read("App.tsx"))
        self.assertIn("me?.authenticated ? me.role : undefined", app)

    def test_no_client_side_role_selection_exists(self):
        # No component ever writes a role: no setRole state, no role
        # picker control, no localStorage role.
        for path, code in walk_sources(code_only=True):
            if path.startswith("imports"):
                continue
            self.assertNotRegex(code, r"setRole\(", path)
            self.assertNotRegex(code, r"localStorage\.[gs]etItem\(\s*['\"]role", path)

    def test_disabled_mode_never_mounts_the_identity_provider(self):
        gate = strip_comments(read(os.path.join("auth", "AuthGate.tsx")))
        self.assertIn("if (!isAuthEnabled) return <>{children}</>", gate)


class AuditHonestyRegressionTest(unittest.TestCase):
    """The Phase 1 audit's dead/fake controls stay dead."""

    def test_no_preauth_placeholder_employee_id_anywhere(self):
        for path, content in walk_sources(live_only=True):
            self.assertNotIn("emp-0142", content, path)
            self.assertNotIn("CURRENT_EMPLOYEE_ID", content, path)

    def test_no_permanently_disabled_coming_soon_controls_in_live_surfaces(self):
        for rel in ("App.tsx", "VehicleDetail.tsx",
                    os.path.join("dashboards", "Tasks.tsx"),
                    os.path.join("dashboards", "VehiclesList.tsx"),
                    os.path.join("dashboards", "TodaysWork.tsx"),
                    os.path.join("dashboards", "Dashboard.tsx")):
            code = strip_comments(read(rel))
            self.assertNotIn("Coming soon", code, rel)

    def test_search_placeholder_promises_only_what_exists(self):
        app = read("App.tsx")
        self.assertIn('placeholder="Search by VIN…"', app)
        self.assertNotIn("Customer…", app)

    def test_local_only_dismiss_is_gone(self):
        detail = strip_comments(read("VehicleDetail.tsx"))
        self.assertNotIn("dismissedLocally", detail)

    def test_exception_reasons_are_translated_with_raw_code_preserved(self):
        sync = read(os.path.join("dashboards", "InventorySync.tsx"))
        self.assertIn("EXCEPTION_REASON_LABELS", sync)
        for code in ("unrecognized", "tekion_auto_generated_stock_number",
                     "last6_vin", "ambiguous_last6_vin_multiple_matches",
                     "stock_number", "non_vehicle"):
            self.assertIn(f"{code}:", sync.replace('"', "'"), code)
        # Raw code kept for debugging on the rendered element.
        self.assertIn("title={e.identifier_type}", sync)


class NavigationDismissalTest(unittest.TestCase):
    """Audit §1.6: sidebar navigation must dismiss an open Vehicle
    Detail and the breadcrumb must name the true origin surface."""

    def setUp(self):
        self.app = strip_comments(read("App.tsx"))

    def test_nav_clears_the_open_vehicle(self):
        # App's navigation handler specifically (the Sidebar component
        # has its own local handleNav for the drawer).
        handler = self.app[self.app.index("const handleNav = useCallback"):]
        handler = handler[:handler.index("}, [")]
        self.assertIn("setSelectedVehicle(null)", handler)

    def test_breadcrumb_uses_the_recorded_origin(self):
        self.assertIn("vehicleOrigin", self.app)
        self.assertIn("setVehicleOrigin(activeNav)", self.app)
        self.assertNotIn("activeNav === 'vehicles' ? 'Vehicles' : 'Dashboard'", self.app)


class TodaysWorkTest(unittest.TestCase):
    """Rail C: the Lot Staff surface reuses the existing task engine."""

    def setUp(self):
        self.src = read(os.path.join("dashboards", "TodaysWork.tsx"))
        self.code = strip_comments(self.src)

    def test_reuses_existing_apis_and_vocabulary(self):
        self.assertIn("getTasks({ commitment_standing: 'outstanding' })", self.code)
        self.assertIn("getWorkOrderPdf", self.code)
        self.assertIn("describeTask", self.code)
        # No new endpoints, no write calls.
        self.assertNotIn("apiPost", self.code)
        self.assertNotIn("fetch(", self.code)

    def test_no_duplicate_task_semantics(self):
        # It renders shared display helpers -- it does not re-derive
        # lifecycle states or invent status vocabulary.
        for forbidden in ("commitment_standing ===", "execution_status ==="):
            self.assertNotIn(forbidden, self.code)

    def test_empty_state_is_operational_language(self):
        self.assertIn("No outstanding work", self.src)

    def test_tracks_its_product_question_once(self):
        self.assertIn("track('today_work_opened')", self.code)


class OnboardingTest(unittest.TestCase):
    def setUp(self):
        self.state = strip_comments(read(os.path.join("onboarding", "state.ts")))
        self.modal = read(os.path.join("onboarding", "Onboarding.tsx"))
        self.app = strip_comments(read("App.tsx"))

    def test_storage_is_supabase_user_metadata_only(self):
        self.assertIn("supabase.auth.updateUser", self.state)
        self.assertIn("dealerdoh_onboarding", self.state)
        # No DealerDOH API surface, no schema, no localStorage.
        self.assertNotIn("apiGet", self.state)
        self.assertNotIn("apiPost", self.state)
        self.assertNotIn("localStorage", self.state)

    def test_never_throws_and_noop_without_auth(self):
        self.assertIn("if (!supabase) return null", self.state)
        self.assertIn("if (!supabase) return false", self.state)

    def test_skip_records_completion(self):
        skip = self.app[self.app.index("const skipOnboarding"):]
        skip = skip[:skip.index("}, [")]
        self.assertIn("recordOnboardingComplete(true)", skip)
        self.assertIn("track('onboarding_skipped')", skip)

    def test_finish_records_completion(self):
        finish = self.app[self.app.index("const finishOnboarding"):]
        finish = finish[:finish.index("}, [")]
        self.assertIn("recordOnboardingComplete(false)", finish)
        self.assertIn("track('onboarding_completed')", finish)

    def test_first_run_gated_on_server_confirmed_authentication(self):
        effect = self.app[self.app.index("getOnboardingRecord()") - 400:self.app.index("getOnboardingRecord()")]
        self.assertIn("me?.authenticated", effect)

    def test_replay_never_rewrites_the_record(self):
        replay = self.app[self.app.index("const replayOnboarding"):]
        replay = replay[:replay.index("}, [")]
        self.assertNotIn("recordOnboardingComplete", replay)
        self.assertIn("track('onboarding_replayed')", replay)

    def test_role_aware_steps_do_not_leak_privileged_surfaces(self):
        code = strip_comments(self.modal)
        lot = code[code.index("LOT_STAFF_STEPS"):code.index("SHARED_STEPS")]
        self.assertNotIn("Inventory Sync", lot)
        self.assertNotIn("User Management", lot)

    def test_skippable_and_replay_ui_exist(self):
        self.assertIn("Skip for now", self.modal)
        help_src = read(os.path.join("help", "Help.tsx"))
        self.assertIn("Replay the Getting Started tour", help_src)


class HelpTest(unittest.TestCase):
    def setUp(self):
        self.src = read(os.path.join("help", "Help.tsx"))
        self.code = strip_comments(self.src)

    def test_sync_section_is_role_gated_presentationally(self):
        self.assertIn("SYNC_CONTROL_ROLES.includes(role)", self.code)

    def test_tracks_help_opened(self):
        self.assertIn("track('help_opened')", self.code)

    def test_documents_only_real_features(self):
        # Things that do not exist must not be documented.
        for absent in ("notification", "Notification", "SMS", "commission",
                       "automated ingestion", "scheduled email"):
            self.assertNotIn(absent, self.src, absent)


class SoldBrowseTest(unittest.TestCase):
    def test_minimal_include_sold_mode(self):
        api = strip_comments(read(os.path.join("api", "vehicles.ts")))
        self.assertIn("include_sold=true", api)
        lst = strip_comments(read(os.path.join("dashboards", "VehiclesList.tsx")))
        self.assertIn("const includeSold = filter === 'sold'", lst)
        self.assertIn("tekion_status === 'Sold'", lst)

    def test_default_view_stays_active_only(self):
        lst = strip_comments(read(os.path.join("dashboards", "VehiclesList.tsx")))
        self.assertIn("getVehicles({ includeSold })", lst)
        # 'all' explicitly excludes sold rows even in the wider dataset.
        self.assertIn("key: 'all',            label: 'All',            test: v => v.tekion_status !== 'Sold'", lst)


class AnalyticsTaxonomyTest(unittest.TestCase):
    """The six planned events exist at their seams, and each is
    documented with its product question in ROLE_AWARE_UX.md. Property
    safety rides the Sprint 11 posture suite's repo-wide track() scan."""

    EVENTS = ("onboarding_started", "onboarding_completed",
              "onboarding_skipped", "onboarding_replayed",
              "help_opened", "today_work_opened")

    def test_events_fire_exactly_where_designed(self):
        app = strip_comments(read("App.tsx"))
        for event in ("onboarding_started", "onboarding_completed",
                      "onboarding_skipped", "onboarding_replayed"):
            self.assertIn(f"track('{event}')", app, event)
        self.assertIn("track('help_opened')",
                      strip_comments(read(os.path.join("help", "Help.tsx"))))
        self.assertIn("track('today_work_opened')",
                      strip_comments(read(os.path.join("dashboards", "TodaysWork.tsx"))))

    def test_every_event_is_documented_with_its_question(self):
        doc = read_repo("ROLE_AWARE_UX.md")
        for event in self.EVENTS:
            self.assertIn(event, doc, event)

    def test_new_page_ids_ride_the_existing_page_viewed_seam(self):
        app = strip_comments(read("App.tsx"))
        self.assertIn("track('page_viewed', { page: selectedVehicle ? 'vehicle-detail' : activeNav })", app)


if __name__ == "__main__":
    unittest.main()
