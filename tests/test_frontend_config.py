"""
Sprint 09 -- configuration guards for the ratified SPA deep-link
requirement (V1_1_RELEASE_READINESS.md Rail A: emailed
recovery/invite links must survive fresh navigation, which needs
Vercel to serve index.html for application routes).

CI cannot exercise Vercel's edge, but it CAN pin the configuration
that makes the behavior possible -- so the rewrite can't be lost in a
refactor without a red build. The deployed behavior itself is part of
the DEV smoke checklist.
"""

import json
import os
import unittest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERCEL_JSON = os.path.join(_REPO, "frontend", "vercel.json")


class VercelSpaRewriteTest(unittest.TestCase):
    def test_vercel_config_has_spa_fallback_rewrite(self):
        with open(_VERCEL_JSON, encoding="utf-8") as fh:
            config = json.load(fh)
        rewrites = config.get("rewrites", [])
        self.assertTrue(rewrites, "vercel.json must define SPA rewrites "
                                  "(Rail A: recovery links need deep-link routing)")
        self.assertTrue(
            any(rule.get("destination") == "/index.html" for rule in rewrites),
            "at least one rewrite must fall back to /index.html")

    def test_reset_password_route_is_handled_outside_the_gate(self):
        # The route only helps if the app actually branches on it.
        main_tsx = os.path.join(_REPO, "frontend", "src", "main.tsx")
        with open(main_tsx, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("/auth/reset-password", source)
        self.assertIn("ResetPassword", source)


class SecurityHeadersConfigTest(unittest.TestCase):
    """Sprint 13 (Rail H): CI can't exercise Vercel's edge, but it pins
    the header configuration so the CSP and clickjacking/nosniff/referrer
    controls can't be lost in a refactor without a red build. The
    deployed headers themselves are on the DEV smoke checklist."""

    def _headers(self):
        with open(_VERCEL_JSON, encoding="utf-8") as fh:
            config = json.load(fh)
        rules = config.get("headers", [])
        self.assertTrue(rules, "vercel.json must define security headers")
        # Flatten every header from the catch-all rule into a dict.
        flat = {}
        for rule in rules:
            for header in rule.get("headers", []):
                flat[header["key"]] = header["value"]
        return flat

    def test_baseline_headers_present(self):
        headers = self._headers()
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertIn("Referrer-Policy", headers)
        self.assertIn("Permissions-Policy", headers)
        self.assertIn("Content-Security-Policy", headers)

    def test_csp_forbids_framing_and_locks_defaults(self):
        csp = self._headers()["Content-Security-Policy"]
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("base-uri 'self'", csp)
        # No script eval, and scripts are not wide open.
        self.assertNotIn("unsafe-eval", csp)

    def test_csp_allows_every_origin_the_app_actually_contacts(self):
        # Enumerated from the deployed bundle: the API, Supabase Auth,
        # Sentry ingest, PostHog. A missing origin would break the app;
        # this fails if one is dropped.
        csp = self._headers()["Content-Security-Policy"]
        connect = next(part for part in csp.split(";") if part.strip().startswith("connect-src"))
        for origin in ("'self'", "https://*.onrender.com", "https://*.supabase.co",
                       "https://*.posthog.com", "https://*.sentry.io"):
            self.assertIn(origin, connect, f"connect-src must allow {origin}")

    def test_csp_allows_google_fonts(self):
        # Found by the Sprint 13 merged-head deployed smoke: index.css
        # @imports Plus Jakarta Sans / JetBrains Mono from Google Fonts,
        # which the first CSP blocked (silent system-font fallback, a
        # console violation on every load). The stylesheet loads from
        # fonts.googleapis.com and pulls font files from
        # fonts.gstatic.com -- both must be allowed, in the right
        # directives.
        headers = self._headers()
        csp = headers["Content-Security-Policy"]
        style = next(part for part in csp.split(";") if part.strip().startswith("style-src"))
        font = next(part for part in csp.split(";") if part.strip().startswith("font-src"))
        self.assertIn("https://fonts.googleapis.com", style,
                      "style-src must allow the Google Fonts stylesheet host")
        self.assertIn("https://fonts.gstatic.com", font,
                      "font-src must allow the Google Fonts file host")


if __name__ == "__main__":
    unittest.main()
