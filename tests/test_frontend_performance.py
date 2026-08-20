"""
Sprint 14 (Rail J) -- frontend PERFORMANCE posture assertions, same
source-scan convention as tests/test_frontend_accessibility.py.

These pin the structural decisions the measurements justified (full
evidence: PERFORMANCE.md): one shared /dashboard fetch per view,
bounded list/timeline rendering with explicit escape hatches, the
deferred PostHog SDK, route-level code splitting for role-gated
surfaces, and the request timeout. Timing itself is never asserted
here (CI machines vary); the bundle-size budget runs as its own CI
step (tools/check_bundle_budget.py) against the real build output.
"""

import os
import unittest

_FRONTEND_SRC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "src"
)


def read(relative: str) -> str:
    with open(os.path.join(_FRONTEND_SRC, relative), encoding="utf-8") as handle:
        return handle.read()


class SharedDashboardFetchTest(unittest.TestCase):
    """GET /dashboard was measured twice per landing (live, deployed
    DEV) because the header and each landing surface fetched their own
    copy. One provider now dedupes in-flight fetches."""

    def test_provider_exists_with_inflight_dedup(self):
        provider = read(os.path.join("api", "dashboardData.tsx"))
        self.assertIn("DashboardDataProvider", provider)
        self.assertIn("if (statusRef.current === 'loading') return", provider)

    def test_consumers_share_the_provider_instead_of_fetching(self):
        for rel in ("App.tsx",
                    os.path.join("dashboards", "Dashboard.tsx"),
                    os.path.join("dashboards", "TodaysWork.tsx"),
                    os.path.join("dashboards", "InventorySync.tsx")):
            src = read(rel)
            self.assertIn("useDashboardData", src, rel)
            self.assertNotIn("getDashboard()", src, rel)

    def test_app_mounts_the_provider(self):
        self.assertIn("<DashboardDataProvider>", read("App.tsx"))


class BoundedRenderingTest(unittest.TestCase):
    """1,197 active rows measured 755 ms to paint with 400-850 ms
    main-thread blocks per widening keystroke; 602 timeline events
    measured 1.4 s. Rendering is bounded with truthful escape hatches;
    filtering/sorting still runs on the complete dataset."""

    def test_vehicles_list_render_cap(self):
        src = read(os.path.join("dashboards", "VehiclesList.tsx"))
        self.assertIn("const RENDER_CAP = 100", src)
        self.assertIn("filtered.slice(0, RENDER_CAP)", src)
        self.assertIn("Show all {filtered.length}", src)
        # a new query resets to the bounded view
        self.assertIn("setShowAll(false) }, [search, filter]", src)

    def test_vehicle_timeline_render_cap(self):
        src = read("VehicleDetail.tsx")
        self.assertIn("const TIMELINE_RENDER_CAP = 150", src)
        self.assertIn("sorted.slice(0, TIMELINE_RENDER_CAP)", src)
        self.assertIn("Show older history", src)


class DeferredTelemetryTest(unittest.TestCase):
    """posthog-js was the single largest bundle contributor (234.6 kB
    minified, 27% of the bundle). Telemetry is secondary by doctrine
    (OBSERVABILITY.md) -- the SDK now loads via dynamic import off the
    critical path, with pre-ready calls queued IN ORDER so identity
    sequencing (identify before its events, reset severing identity)
    is preserved. Unconfigured builds never fetch the chunk at all."""

    def test_posthog_is_dynamically_imported(self):
        analytics = read(os.path.join("observability", "analytics.ts"))
        self.assertIn("import('posthog-js')", analytics)
        self.assertNotIn("import posthog from 'posthog-js'", analytics)
        # type-only import is fine (erased at build)
        self.assertIn("import type { PostHog } from 'posthog-js'", analytics)

    def test_pre_ready_calls_are_queued_in_order(self):
        analytics = read(os.path.join("observability", "analytics.ts"))
        self.assertIn("pending.push(call)", analytics)
        self.assertIn("for (const call of queued)", analytics)

    def test_sentry_stays_synchronous(self):
        # Deliberate asymmetry: Sentry keeps early-error capture, so it
        # is NOT deferred (documented in PERFORMANCE.md).
        main = read("main.tsx")
        self.assertIn("import { initSentry } from './observability/sentry'", main)


class CodeSplittingTest(unittest.TestCase):
    """Role-gated / rarely-first surfaces load as their own chunks; the
    landing surfaces (Overview, Today's Work, Vehicles, Tasks, Vehicle
    Detail) deliberately stay in the initial bundle."""

    def test_role_gated_surfaces_are_lazy(self):
        app = read("App.tsx")
        for chunk in ("./dashboards/InventorySync", "./dashboards/Profile",
                      "./help/Help", "./onboarding/Onboarding"):
            self.assertIn(f"lazy(() => import('{chunk}'))", app)

    def test_landing_surfaces_stay_eager(self):
        app = read("App.tsx")
        for eager in ("import Dashboard from './dashboards/Dashboard'",
                      "import VehiclesList from './dashboards/VehiclesList'",
                      "import Tasks from './dashboards/Tasks'",
                      "import TodaysWork from './dashboards/TodaysWork'",
                      "import VehicleDetailPage from './VehicleDetail'"):
            self.assertIn(eager, app)

    def test_auth_screens_are_lazy(self):
        self.assertIn("lazy(() => import('./Login'))", read(os.path.join("auth", "AuthGate.tsx")))
        self.assertIn("lazy(() => import('./auth/ResetPassword'))", read("main.tsx"))


class RequestTimeoutTest(unittest.TestCase):
    """Slow-network resilience: no fetch may hang forever."""

    def test_every_fetch_carries_the_timeout_signal(self):
        client = read(os.path.join("api", "client.ts"))
        self.assertIn("REQUEST_TIMEOUT_MS = 30_000", client)
        self.assertEqual(client.count("signal: requestTimeoutSignal()"), 4)


if __name__ == "__main__":
    unittest.main()
