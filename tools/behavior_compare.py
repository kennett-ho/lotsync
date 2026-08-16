"""
Cross-engine behavioral validation (Sprint 07).

Runs the application's own read-model query layer against BOTH a
SQLite database file and the migrated PostgreSQL database, and
requires identical results. This is the "behavioral" arm of the
Release B validation plan (PRODUCTION_MIGRATION_PLAN.md section 6):
row counts can match while behavior diverges -- this proves the
projections the app actually serves are identical.

Covers: active-inventory filtering, sold preservation, vehicle detail
(event ordering, task lifecycle), task projections (the work-order's
input), recommendations, pending identities (missing-source
safeguard), sync history, dashboard aggregates, and work-order PDF
generation (input data + page count; PDF bytes embed timestamps so
byte-equality is deliberately not asserted).

Read-only by design: only SELECT-shaped query functions are invoked.
The SQLite side should be pointed at a disposable COPY of the backup,
not the canonical artifact (connect() opens read-write by contract).

Usage (repo root):
    MIGRATE_DEST_DSN=... PYTHONPATH=.. python tools/behavior_compare.py \
        --sqlite <copy-of-backup.db> [--dest-dsn-env MIGRATE_DEST_DSN] \
        [--sample-vins 10]
Exit 0 = identical; 2 = divergence (listed); 3 = precondition failure.
"""

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.dirname(_REPO))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True,
                    help="Path to a disposable COPY of the SQLite backup")
    ap.add_argument("--dest-dsn-env", default="MIGRATE_DEST_DSN")
    ap.add_argument("--sample-vins", type=int, default=10)
    args = ap.parse_args(argv)

    if not os.path.isfile(args.sqlite):
        print(f"REFUSED: {args.sqlite} is not a file")
        return 3
    if not os.environ.get(args.dest_dsn_env, "").strip():
        print(f"REFUSED: {args.dest_dsn_env} is not set")
        return 3

    from lotsync.database import repository
    from lotsync.queries.vehicles import list_vehicles, get_vehicle_detail
    from lotsync.queries.tasks import list_tasks
    from lotsync.queries.recommendations import list_recommendations
    from lotsync.queries.inventory_sync import (
        list_pending_identities, sync_run_history)
    from lotsync.queries.dashboard import (
        connected_systems_status, recent_activity_feed,
        task_counts_by_department, inventory_health_percentage)

    # SQLite side first (engine env must be sqlite for a path connect).
    os.environ["DATABASE_ENGINE"] = "sqlite"
    lite = repository.connect(args.sqlite)

    # Then the postgres side against the migrated destination.
    os.environ["DATABASE_ENGINE"] = "postgres"
    os.environ["DATABASE_URL"] = os.environ[args.dest_dsn_env]
    pg = repository.connect(None)

    vins = [r[0] for r in lite.execute(
        "SELECT vin FROM vehicle ORDER BY vin")]
    step = max(1, len(vins) // max(1, args.sample_vins))
    sampled = vins[::step][:args.sample_vins]

    checks = []

    def check(name, fn):
        a, b = fn(lite), fn(pg)
        same = a == b
        checks.append({"check": name, "identical": same})
        marker = "ok  " if same else "FAIL"
        print(f"  {marker}  {name}")
        if not same:
            checks[-1]["sqlite"] = repr(a)[:400]
            checks[-1]["postgres"] = repr(b)[:400]

    print("behavioral comparison (sqlite backup copy vs migrated postgres):")
    check("list_vehicles(active only)", lambda c: list_vehicles(c))
    check("list_vehicles(include_sold)",
          lambda c: list_vehicles(c, include_sold=True))
    check("list_tasks(all)", lambda c: list_tasks(c))
    check("list_tasks(outstanding) [work-order input]",
          lambda c: list_tasks(c, commitment_standing="outstanding"))
    check("list_recommendations", lambda c: list_recommendations(c))
    check("list_pending_identities", lambda c: list_pending_identities(c))
    check("sync_run_history", lambda c: sync_run_history(c))
    check("connected_systems_status", lambda c: connected_systems_status(c))
    check("recent_activity_feed(50)",
          lambda c: recent_activity_feed(c, limit=50))
    check("task_counts_by_department",
          lambda c: task_counts_by_department(c))
    check("inventory_health_percentage",
          lambda c: inventory_health_percentage(c))
    for vin in sampled:
        check(f"get_vehicle_detail({vin})",
              lambda c, v=vin: get_vehicle_detail(c, v))

    # Work-order PDF: same input tasks (asserted above) must yield the
    # same page count on both engines' data.
    try:
        from lotsync.reports.work_order import build_work_order
        from io import BytesIO
        from pypdf import PdfReader

        def pages(conn):
            tasks = list_tasks(conn, commitment_standing="outstanding")
            pdf = build_work_order(tasks, store_name="Rehearsal Motors")
            return len(PdfReader(BytesIO(pdf.pdf_bytes)).pages)

        check("work_order_pdf(page count)", pages)
    except ImportError as exc:
        print(f"  note  work-order PDF check skipped ({exc})")

    lite.close()
    pg.close()

    failures = [c for c in checks if not c["identical"]]
    print(f"\n{len(checks) - len(failures)}/{len(checks)} identical")
    if failures:
        print("BEHAVIORAL DIVERGENCE -- destination must not be cut over:")
        for f in failures:
            print(f"  - {f['check']}")
        print(json.dumps(failures, indent=2)[:4000])
        return 2
    print("BEHAVIOR IDENTICAL across engines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
