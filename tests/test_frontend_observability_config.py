"""
Sprint 11 -- frontend observability POSTURE assertions, following
tests/test_frontend_config.py's precedent (pin deployment-critical
frontend facts from the backend suite rather than building a
frontend test framework for configuration checks -- the sprint brief
explicitly calls for proportionality here).

These pin the PRIVACY POSTURE: autocapture off, session replay off
and never imported, PII defaults off, identity = internal id, the
sign-out reset, and the absence of any privileged secret reference
in frontend source. Runtime behavior is proven live in the DEV
verification phases; these tests make the posture un-regressable in
CI.
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


def strip_comments(source: str) -> str:
    """Crude but sufficient: drop /* */ blocks and // line tails so
    posture scans judge CODE, not the comments explaining the posture."""
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$|(?<=[\s;{(])//[^\n]*$", "", source)


def walk_sources(code_only: bool = False):
    for root, _dirs, names in os.walk(_FRONTEND_SRC):
        for name in names:
            if name.endswith((".ts", ".tsx")):
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as handle:
                    content = handle.read()
                yield (os.path.relpath(path, _FRONTEND_SRC),
                       strip_comments(content) if code_only else content)


class PostHogPostureTest(unittest.TestCase):
    def test_privacy_defaults_are_explicitly_off(self):
        analytics = read(os.path.join("observability", "analytics.ts"))
        for required in ("autocapture: false",
                        "capture_pageview: false",
                        "capture_pageleave: false",
                        "disable_session_recording: true",
                        "disable_surveys: true",
                        # Sprint 15 (Rail L): localStorage-only
                        # persistence -- the SDK's default
                        # 'localStorage+cookie' mode set the app's ONLY
                        # cookie; DealerDOH sets no cookies at all.
                        "persistence: 'localStorage'",
                        "person_profiles: 'identified_only'"):
            self.assertIn(required, analytics, required)

    def test_identity_is_internal_id_with_safe_properties_only(self):
        analytics = read(os.path.join("observability", "analytics.ts"))
        identify = analytics[analytics.index("export function identifyAnalyticsUser"):]
        identify = identify[:identify.index("export function", 10)]
        for forbidden in ("email", "display_name", "name:"):
            self.assertNotIn(forbidden, identify, forbidden)

    def test_identify_uses_the_server_confirmed_internal_id(self):
        provider = read(os.path.join("auth", "AccessProvider.tsx"))
        self.assertIn("identifyAnalyticsUser(me.auth_user_id", provider)

    def test_sign_out_resets_analytics_identity(self):
        gate = read(os.path.join("auth", "AuthGate.tsx"))
        sign_out = gate[gate.index("export async function signOut"):]
        self.assertIn("resetAnalyticsIdentity()", sign_out)

    def test_no_event_sends_email_or_vin_properties(self):
        # Every track() call site: no property KEY named email/vin/
        # filename/display_name (event NAMES like
        # profile_display_name_updated are fine -- the rule guards the
        # payload, and key syntax always carries the colon).
        for rel, source in walk_sources(code_only=True):
            for call in re.findall(r"track\((.{0,400}?)\)\n", source, re.DOTALL):
                lowered = call.lower()
                for forbidden in ("email:", "vin:", "filename:", "display_name:"):
                    self.assertNotIn(forbidden, lowered, (rel, call[:120]))


class SentryFrontendPostureTest(unittest.TestCase):
    def test_conservative_init(self):
        sentry = read(os.path.join("observability", "sentry.ts"))
        self.assertIn("sendDefaultPii: false", sentry)
        self.assertIn("tracesSampleRate: 0", sentry)
        self.assertIn("/replay/i.test(i.name)", sentry)  # defensive replay filter

    def test_replay_is_never_imported_anywhere(self):
        # Code only -- sentry.ts's comment EXPLAINING that replay is
        # never used may name it; the code may not.
        for rel, source in walk_sources(code_only=True):
            self.assertNotIn("replayIntegration", source, rel)
            self.assertNotIn("Replay(", source, rel)

    def test_breadcrumb_urls_are_masked(self):
        sentry = read(os.path.join("observability", "sentry.ts"))
        self.assertIn("beforeBreadcrumb", sentry)
        self.assertIn("maskUrl", sentry)

    def test_error_boundary_wraps_the_whole_tree(self):
        main = read("main.tsx")
        self.assertIn("<ErrorBoundary>", main)
        self.assertIn("initSentry()", main)
        self.assertIn("initAnalytics()", main)
        boundary = read(os.path.join("observability", "ErrorBoundary.tsx"))
        self.assertIn("componentDidCatch", boundary)
        self.assertIn("window.location.reload()", boundary)


class FrontendSecretHygieneTest(unittest.TestCase):
    def test_no_privileged_secret_references_in_frontend_source(self):
        # Browser-public identifiers (VITE_SENTRY_DSN, VITE_POSTHOG_KEY)
        # are intentional; privileged material must never be referenced
        # from frontend source at all.
        forbidden = ("SENTRY_AUTH_TOKEN", "sb_secret_", "DATABASE_URL",
                     "SUPABASE_SECRET_KEY", "service_role")
        for rel, source in walk_sources():
            for marker in forbidden:
                self.assertNotIn(marker, source, (rel, marker))

    def test_release_constant_is_build_time_not_secret(self):
        config = read(os.path.join("observability", "config.ts"))
        self.assertIn("__DEALERDOH_RELEASE__", config)
        vite = read(os.path.join("..", "vite.config.ts"))
        self.assertIn("VERCEL_GIT_COMMIT_SHA", vite)
        self.assertIn("GITHUB_SHA", vite)


if __name__ == "__main__":
    unittest.main()
