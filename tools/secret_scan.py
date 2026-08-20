"""
tools/secret_scan.py -- Sprint 13 (Rail H / §5.H.1): current-tree secret scan.

A dependency-free, self-contained scanner for credential-shaped material
in the tracked working tree. It is BOTH the CI secret-scanning gate (see
.github/workflows/ci.yml) and the operator's re-scan tool for the
Repository Public-Release Sanitation checklist.

Design:
- Scans git-tracked files only (git ls-files) -- never .venv, node_modules,
  build output, or local scratch.
- Fails (exit 1) on a REAL secret shape; passes (exit 0) otherwise.
- NEVER prints a matched secret value -- only a pattern name, the file,
  and a masked fingerprint (first 4 chars + length + a sha256 prefix).
- Distinguishes intentionally-public identifiers (Supabase
  publishable/anon keys, PostHog project tokens, browser Sentry DSNs)
  from actual secrets -- the former are reported as INFO, never failures.
- Excludes documented non-secrets: .env.example placeholders, test
  fixtures, this scanner's own pattern table, and the CI PostgreSQL
  service container's throwaway `postgres:postgres@localhost` DSN.

This scans the CURRENT TREE only. Full Git-history scanning (all commits,
branches, tags, deleted files) is a separate, heavier audit performed
with dedicated tooling during the sanitation gate -- see SECURITY_AUDIT.md.

Usage:
    python tools/secret_scan.py            # scan the tracked tree
    python tools/secret_scan.py --verbose  # also list INFO (public ids)
Exit code 1 means a real secret shape was found and must be triaged.
"""

import base64
import hashlib
import json
import re
import subprocess
import sys

# (name, compiled regex, classification). SECRET => build fails.
# PUBLIC => intentional browser identifier, reported as INFO only.
# CLASSIFY => decode/inspect to decide (see _classify_match).
_PATTERNS = [
    ("supabase-secret-key", re.compile(r"sb_secret_[A-Za-z0-9_-]{8,}"), "SECRET"),
    ("supabase-publishable-key", re.compile(r"sb_publishable_[A-Za-z0-9_-]{8,}"), "PUBLIC"),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,}"), "CLASSIFY"),
    ("postgres-dsn-with-password", re.compile(r"postgres(?:ql)?://[^:/\s\"']{1,64}:([^@\s\"']{3,})@[^\s\"']+"), "CLASSIFY"),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"), "SECRET"),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}"), "SECRET"),
    ("render-token", re.compile(r"\brnd_[A-Za-z0-9]{16,}"), "SECRET"),
    ("sentry-auth-token", re.compile(r"\bsntry[su]_[A-Za-z0-9=_+/.\-]{16,}"), "SECRET"),
    ("posthog-personal-key", re.compile(r"\bphx_[A-Za-z0-9]{16,}"), "SECRET"),
    ("posthog-project-token", re.compile(r"\bphc_[A-Za-z0-9]{16,}"), "PUBLIC"),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "SECRET"),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "SECRET"),
    ("stripe-secret-key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}"), "SECRET"),
]

# Files/paths whose credential-shaped strings are documented non-secrets:
# the env template (placeholders), synthetic test fixtures, this
# scanner's own pattern table, the scanner's own unit test (which holds
# synthetic secret shapes as deliberate test vectors), and the audit
# report (which quotes masked fingerprints, never live values).
_ALLOW_PATHS = re.compile(
    r"(^|/)\.env\.example$|(^|/)tests/fixtures/|(^|/)tools/secret_scan\.py$|"
    r"(^|/)tests/test_secret_scan\.py$|(^|/)SECURITY_AUDIT\.md$",
)

# Known throwaway / placeholder DSNs that are NOT secrets:
#  - the CI PostgreSQL service container (postgres:postgres@127.0.0.1/localhost)
#  - documentation/test placeholders (u:p@h, user:pass@host, <...> tokens)
_DSN_NONSECRET = re.compile(
    r"^(postgres|postgresql)$|^p$|^pass$|^password$|^<[^>]+>$|^\$\{?[A-Za-z_]|^:memory:$",
)
_DSN_NONSECRET_HOST = re.compile(r"^(127\.0\.0\.1|localhost|host|h|<[^>]+>)\b")


def _git_tracked_files() -> list:
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def _mask(value: str) -> str:
    digest = hashlib.sha256(value.encode()).hexdigest()[:8]
    return f"{value[:4]}…(len={len(value)},sha256:{digest})"


def _jwt_role(token: str) -> str:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return str(claims.get("role", "")).lower()
    except Exception:
        return ""


def _classify_match(name: str, match: re.Match) -> str:
    """For CLASSIFY patterns, decide SECRET vs PUBLIC vs IGNORE."""
    if name == "jwt":
        role = _jwt_role(match.group(0))
        if role == "service_role":
            return "SECRET"          # the privileged Supabase key
        if role == "anon":
            return "PUBLIC"          # the browser anon key
        return "IGNORE"             # a user access token / unrelated JWT shape
    if name == "postgres-dsn-with-password":
        password = match.group(1)
        host_tail = match.group(0).split("@", 1)[1]
        if _DSN_NONSECRET.match(password) or _DSN_NONSECRET_HOST.match(host_tail):
            return "IGNORE"          # CI container / documentation placeholder
        return "SECRET"
    return "SECRET"


def scan(verbose: bool = False) -> int:
    secrets_found = []
    public_found = []

    for path in _git_tracked_files():
        if _ALLOW_PATHS.search(path.replace("\\", "/")):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except (OSError, UnicodeError):
            continue
        for name, rx, base_class in _PATTERNS:
            for match in rx.finditer(text):
                cls = base_class if base_class != "CLASSIFY" else _classify_match(name, match)
                if cls == "IGNORE":
                    continue
                record = (name, path, _mask(match.group(0)))
                (secrets_found if cls == "SECRET" else public_found).append(record)

    if verbose and public_found:
        print("INFO -- intentionally-public identifiers (not secrets):")
        for name, path, fp in sorted(set(public_found)):
            print(f"  [{name}] {path}: {fp}")

    if secrets_found:
        print("SECRET SCAN FAILED -- credential-shaped material in the tracked tree:")
        for name, path, fp in sorted(set(secrets_found)):
            print(f"  [{name}] {path}: {fp}")
        print("\nEach must be triaged: rotate/revoke if real, or add a documented "
              "exclusion if a confirmed non-secret. See SECURITY_AUDIT.md.")
        return 1

    print(f"Secret scan clean: {len(_git_tracked_files())} tracked files, "
          f"0 secrets, {len(set(public_found))} public identifier(s).")
    return 0


if __name__ == "__main__":
    sys.exit(scan(verbose="--verbose" in sys.argv))
