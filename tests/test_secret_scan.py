"""
Sprint 13 (Rail H / §5.H.1) -- coverage for tools/secret_scan.py, the
CI secret-scanning gate and operator re-scan tool.

Two things are proven: the tracked tree is currently clean (a
regression guard against a future accidental commit), and the
classifier makes the right SECRET / PUBLIC / IGNORE call on each
credential shape -- including the documented non-secrets (the CI
PostgreSQL container DSN, publishable/anon identifiers).
"""

import importlib.util
import os
import unittest

# tools/ is a script directory, not an importable package -- load the
# scanner module directly by path (same tree the CI job invokes).
_SCAN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tools", "secret_scan.py",
)
_spec = importlib.util.spec_from_file_location("secret_scan", _SCAN_PATH)
secret_scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(secret_scan)


class SecretScanTreeTest(unittest.TestCase):
    def test_tracked_tree_is_clean(self):
        # The whole point of the gate: exit 0 on the real repository.
        self.assertEqual(secret_scan.scan(), 0,
                         "a real secret shape is present in the tracked tree")


class ClassifierTest(unittest.TestCase):
    def _match(self, name, text):
        rx = next(r for n, r, _ in secret_scan._PATTERNS if n == name)
        m = rx.search(text)
        self.assertIsNotNone(m, f"{name} pattern should match {text!r}")
        return m

    def test_supabase_secret_key_is_secret(self):
        _, _, cls = next(p for p in secret_scan._PATTERNS
                         if p[0] == "supabase-secret-key")
        self.assertEqual(cls, "SECRET")
        self._match("supabase-secret-key", "sb_secret_abcDEF1234567890xyz")

    def test_publishable_key_is_public(self):
        _, _, cls = next(p for p in secret_scan._PATTERNS
                         if p[0] == "supabase-publishable-key")
        self.assertEqual(cls, "PUBLIC")

    def test_service_role_jwt_is_secret(self):
        # A JWT whose payload role == service_role is the privileged key.
        import base64
        import json
        payload = base64.urlsafe_b64encode(
            json.dumps({"role": "service_role"}).encode()).decode().rstrip("=")
        token = f"eyJhbGciOiJIUzI1NiJ9.{payload}.c2lnbmF0dXJl"
        m = self._match("jwt", token)
        self.assertEqual(secret_scan._classify_match("jwt", m), "SECRET")

    def test_anon_jwt_is_public(self):
        import base64
        import json
        payload = base64.urlsafe_b64encode(
            json.dumps({"role": "anon"}).encode()).decode().rstrip("=")
        token = f"eyJhbGciOiJIUzI1NiJ9.{payload}.c2lnbmF0dXJl"
        m = self._match("jwt", token)
        self.assertEqual(secret_scan._classify_match("jwt", m), "PUBLIC")

    def test_ci_container_dsn_is_ignored(self):
        # The CI PostgreSQL service container's throwaway creds -- not a secret.
        m = self._match("postgres-dsn-with-password",
                        "postgresql://postgres:postgres@127.0.0.1:5432/postgres")
        self.assertEqual(secret_scan._classify_match("postgres-dsn-with-password", m),
                         "IGNORE")

    def test_doc_placeholder_dsn_is_ignored(self):
        # The documentation/test placeholder shape (user:pass@host) that
        # appears in test_observability.py -- matched, then classified
        # IGNORE by the placeholder-host rule.
        m = self._match("postgres-dsn-with-password", "postgresql://user:pass@host:5432/db")
        self.assertEqual(secret_scan._classify_match("postgres-dsn-with-password", m),
                         "IGNORE")

    def test_trivial_short_password_dsn_not_even_flagged(self):
        # A 1-char password (postgres://u:p@h/db) falls below the 3-char
        # floor and never matches at all -- also a safe non-flag.
        rx = next(r for n, r, _ in secret_scan._PATTERNS if n == "postgres-dsn-with-password")
        self.assertIsNone(rx.search("postgres://u:p@h/db"))

    def test_real_looking_dsn_is_secret(self):
        m = self._match(
            "postgres-dsn-with-password",
            "postgresql://admin:S3cr3tP4ssw0rd@db.prod.example.com:5432/app")
        self.assertEqual(secret_scan._classify_match("postgres-dsn-with-password", m),
                         "SECRET")

    def test_private_key_block_is_secret(self):
        _, rx, cls = next(p for p in secret_scan._PATTERNS
                          if p[0] == "private-key-block")
        self.assertEqual(cls, "SECRET")
        self.assertTrue(rx.search("-----BEGIN RSA PRIVATE KEY-----"))

    def test_mask_never_reveals_full_value(self):
        masked = secret_scan._mask("sb_secret_supersecretvalue123456")
        self.assertNotIn("supersecretvalue", masked)
        self.assertIn("len=", masked)


if __name__ == "__main__":
    unittest.main()
