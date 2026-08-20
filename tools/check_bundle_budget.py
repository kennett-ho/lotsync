"""
Sprint 14 (Rail J) -- the frontend bundle budget gate.

Run AFTER `npm run build` against frontend/dist. Reads index.html to
discover the INITIAL-load JavaScript graph (the entry <script> plus
every modulepreload chunk the entry statically imports -- lazy chunks
load on demand and are budgeted separately as part of the total),
gzips the real build artifacts, and fails the build when a ceiling is
exceeded.

The ceilings are regression alarms derived from measured reality, not
aspirations (PERFORMANCE.md records the derivation):

    Sprint 13 baseline:  single chunk, 885.1 kB raw / 256.1 kB gzip
    Sprint 14 result:    initial 167.2 kB gzip (entry + supabase),
                         total ~264 kB gzip across all chunks,
                         CSS 11.3 kB gzip

Each ceiling carries ~15-20% headroom over the Sprint 14 measurement
so ordinary feature work never fights the gate, while a regression of
the class this sprint fixed (an SDK landing back in the initial
chunk: PostHog alone is ~80 kB gzip) trips it immediately.

Usage:
    python tools/check_bundle_budget.py [--dist frontend/dist]

Exit codes: 0 within budget · 1 over budget · 2 missing/unreadable build.
"""

import argparse
import gzip
import os
import re
import sys

INITIAL_JS_GZIP_BUDGET_KB = 200
TOTAL_JS_GZIP_BUDGET_KB = 320
CSS_GZIP_BUDGET_KB = 25


def gzip_kb(path: str) -> float:
    with open(path, "rb") as handle:
        return len(gzip.compress(handle.read(), 6)) / 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", default=os.path.join("frontend", "dist"))
    args = parser.parse_args()

    index_path = os.path.join(args.dist, "index.html")
    assets_dir = os.path.join(args.dist, "assets")
    if not os.path.isfile(index_path) or not os.path.isdir(assets_dir):
        print(f"bundle budget: no build at {args.dist} (run `npm run build` first)")
        return 2

    with open(index_path, encoding="utf-8") as handle:
        html = handle.read()

    # The initial JS graph: the module entry plus modulepreload chunks
    # (statically imported, fetched before first paint). Lazy chunks
    # appear in neither and stay out of the initial figure.
    initial_js = re.findall(r'<script[^>]+src="/(assets/[^"]+\.js)"', html)
    initial_js += re.findall(r'<link rel="modulepreload"[^>]+href="/(assets/[^"]+\.js)"', html)
    if not initial_js:
        print("bundle budget: no entry script found in index.html")
        return 2

    all_js = [f for f in os.listdir(assets_dir) if f.endswith(".js")]
    all_css = [f for f in os.listdir(assets_dir) if f.endswith(".css")]

    initial_total = 0.0
    print("initial-load JS:")
    for rel in initial_js:
        kb = gzip_kb(os.path.join(args.dist, rel))
        initial_total += kb
        print(f"  {kb:8.1f} kB gz  {rel}")

    total_js = 0.0
    for name in sorted(all_js):
        total_js += gzip_kb(os.path.join(assets_dir, name))
    css_total = sum(gzip_kb(os.path.join(assets_dir, name)) for name in all_css)

    print(f"initial JS gzip: {initial_total:7.1f} kB  (budget {INITIAL_JS_GZIP_BUDGET_KB} kB)")
    print(f"total   JS gzip: {total_js:7.1f} kB  (budget {TOTAL_JS_GZIP_BUDGET_KB} kB)")
    print(f"total  CSS gzip: {css_total:7.1f} kB  (budget {CSS_GZIP_BUDGET_KB} kB)")

    failures = []
    if initial_total > INITIAL_JS_GZIP_BUDGET_KB:
        failures.append(
            f"initial-load JS {initial_total:.1f} kB gzip exceeds the "
            f"{INITIAL_JS_GZIP_BUDGET_KB} kB budget -- did a deferred SDK or a "
            "role-gated surface land back in the entry chunk?")
    if total_js > TOTAL_JS_GZIP_BUDGET_KB:
        failures.append(
            f"total JS {total_js:.1f} kB gzip exceeds the {TOTAL_JS_GZIP_BUDGET_KB} kB budget")
    if css_total > CSS_GZIP_BUDGET_KB:
        failures.append(
            f"CSS {css_total:.1f} kB gzip exceeds the {CSS_GZIP_BUDGET_KB} kB budget")

    if failures:
        for failure in failures:
            print(f"BUDGET EXCEEDED: {failure}")
        print("If the growth is a deliberate, owner-visible decision, raise the "
              "ceiling here IN THE SAME PR and record the reasoning in PERFORMANCE.md.")
        return 1

    print("bundle budget: within budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
