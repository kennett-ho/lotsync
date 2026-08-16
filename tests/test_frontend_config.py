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


if __name__ == "__main__":
    unittest.main()
