"""
Production-shaped synthetic SQLite dataset generator (Sprint 07).

Builds a disposable SQLite database at production scale and shape for
rehearsing the SQLite -> PostgreSQL migration
(tools/migrate_sqlite_to_postgres.py). It deliberately reproduces the
migration-sensitive conditions recorded in
PRODUCTION_MIGRATION_PLAN.md section 4:

- ~4,700 vehicles with the production status distributions
  (Sold-heavy tekion_status, sparse keyper/mdd/recovr statuses)
- ~8,900 events incl. historical event_time values (2022+), NULL
  optionals, integer-like TEXT sync_run_id provenance tags
- SPARSE IDENTITY SEQUENCES: rows are inserted then deleted so that
  sqlite_sequence.seq > MAX(id) for event, task, and pending_identity
  (the production pending_identity case, seq 3 vs 2 rows), plus
  non-contiguous surviving IDs
- task self-FK escalation pairs (escalated_from_task_id)
- recommendation -> task FK (converted_to_task with resulting_task_id)
- honored/moot closed tasks alongside outstanding ones
- EMPTY organization / dealership / employee / user_membership tables
  (exactly the production final-backup state -- those rows are created
  in PostgreSQL at auth-cutover prep, not migrated)
- schema at migration 0009 (applied by the real runner via connect())

Fully deterministic: fixed RNG seed, fixed base timestamps, no
datetime.now() anywhere. Same arguments => byte-identical row content.

This does NOT replace the standing 34-vehicle QA dealership
(dev_seed/); it exists only for migration scale/timing rehearsal.

Usage (repo root):
    PYTHONPATH=.. python tools/generate_rehearsal_dataset.py \
        --out <path.db> [--scale production|small] [--force]
"""

import argparse
import json
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.dirname(_REPO))

SEED = 20260816
BASE_DAY = "2026-08-{day:02d}T{hh:02d}:{mm:02d}:{ss:02d}.{us:06d}"

MAKES_MODELS = [
    ("Kia", "Sportage LX"), ("Kia", "Sorento SX"), ("Kia", "Telluride EX"),
    ("Kia", "Forte GT-Line"), ("Kia", "K5 LXS"), ("Kia", "Seltos S"),
    ("Kia", "Niro EX"), ("Kia", "Carnival SX"), ("Kia", "EV6 Wind"),
    ("Kia", "Soul LX"),
]

EVENT_TYPES = [
    ("tekion_inventory_observed", "tekion"),
    ("keyper_status_changed", "keyper"),
    ("recovr_pairing_observed", "recovr"),
    ("mdd_pairing_observed", "mdd"),
    ("rapidrecon_step_changed", "rapidrecon"),
    ("tekion_sold_observed", "tekion"),
]


def ts(rng, day_lo=7, day_hi=13):
    return BASE_DAY.format(
        day=rng.randint(day_lo, day_hi), hh=rng.randint(8, 21),
        mm=rng.randint(0, 59), ss=rng.randint(0, 59),
        us=rng.randint(0, 999999))


def scaled(n_vehicles: int, prod_value: int) -> int:
    """Scale a production-observed count to this dataset's size."""
    return max(1, round(prod_value * n_vehicles / 4672))


def generate(out_path: str, scale: str, force: bool) -> dict:
    if os.path.exists(out_path):
        if not force:
            raise SystemExit(
                f"REFUSED: {out_path} already exists. Pass --force to "
                "overwrite a previous rehearsal dataset.")
        os.remove(out_path)

    if os.environ.get("DATABASE_ENGINE", "sqlite").lower() != "sqlite":
        raise SystemExit(
            "REFUSED: DATABASE_ENGINE must be sqlite (or unset) -- this "
            "generator writes a SQLite file via the real migration runner.")

    from lotsync.database.repository import connect

    n_veh = {"production": 4700, "small": 120}[scale]
    rng = random.Random(SEED)

    conn = connect(out_path)  # applies migrations 0001-0009, real runner
    cur = conn.cursor() if hasattr(conn, "cursor") else conn

    # ---- vehicles ---------------------------------------------------
    n_sold = scaled(n_veh, 3482)
    n_stocked = scaled(n_veh, 1158)
    n_reserved = scaled(n_veh, 30)
    n_received = scaled(n_veh, 1)
    n_onhold = max(0, n_veh - n_sold - n_stocked - n_reserved - n_received)
    statuses = (["Sold"] * n_sold + ["Stocked In"] * n_stocked
                + ["Reserved"] * n_reserved + ["Received"] * n_received
                + ["On hold"] * n_onhold)
    rng.shuffle(statuses)

    n_key_out = scaled(n_veh, 265)
    n_key_in = scaled(n_veh, 772)
    n_rec_paired = scaled(n_veh, 1162)
    n_rec_np = scaled(n_veh, 244)
    n_mdd_np = scaled(n_veh, 338)

    vins = []
    vehicle_rows = []
    for i in range(n_veh):
        vin = f"1REHTEST{i:09d}"
        vins.append(vin)
        year = rng.choice([2022, 2023, 2024, 2025, 2026])
        make, model = MAKES_MODELS[i % len(MAKES_MODELS)]
        tek = statuses[i]
        keyper = ("Out" if i < n_key_out else
                  "In" if i < n_key_out + n_key_in else None)
        recovr = ("paired" if i % n_veh < n_rec_paired else
                  "not_paired" if i < n_rec_paired + n_rec_np else None)
        mdd = "not_paired" if (i % 13 == 0 and i < n_mdd_np * 13) else None
        stock = None if i % 233 == 0 else f"RH{i:05d}"
        new_used = rng.choice([None, None, "New", "Used"])
        vehicle_rows.append((
            vin, stock, None, None, None, new_used, None,
            tek, keyper, mdd, recovr, None,
            f"{year} {make} {model}",
        ))
    cur.executemany(
        "INSERT INTO vehicle (vin, stock_number, year, make, model, "
        "new_or_used, current_dealership_id, tekion_status, keyper_status, "
        "mdd_status, recovr_status, inventory_state, display_name) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", vehicle_rows)

    # ---- sync runs (12, production source mix) ----------------------
    sync_sources = (["tekion"] * 3 + ["keyper"] * 3 + ["recovr"] * 3
                    + ["rapidrecon"] * 2 + ["mdd"] * 1)
    rng.shuffle(sync_sources)
    for src_name in sync_sources:
        started = ts(rng)
        cur.execute(
            "INSERT INTO sync_run (source, dealership_id, started_at, "
            "completed_at, records_processed, issues_found, "
            "tasks_generated, status) VALUES (?,?,?,?,?,?,?,?)",
            (src_name, None, started, started[:-6] + "999999",
             rng.randint(200, 4700), rng.randint(0, 6),
             rng.randint(0, 40), "complete"))
    run_ids = [r[0] for r in conn.execute(
        "SELECT sync_run_id FROM sync_run ORDER BY sync_run_id")]

    # ---- events (~8,900 at production scale) ------------------------
    target_events = scaled(n_veh, 8876)
    event_rows = []
    i = 0
    while len(event_rows) < target_events:
        vin = vins[i % len(vins)]
        etype, esrc = EVENT_TYPES[(i + i // len(vins)) % len(EVENT_TYPES)]
        historical = (i % 17 == 0)
        event_time = (f"{rng.randint(2022, 2026)}-{rng.randint(1, 12):02d}-"
                      f"{rng.randint(1, 28):02d}T00:00:00"
                      if historical else None)
        detail = (json.dumps({"observed": etype, "n": i})
                  if i % 2 == 0 else None)
        summary = None if i % 11 == 0 else f"{etype} for {vin[-6:]}"
        event_rows.append((
            vin, etype, esrc, str(rng.choice(run_ids)), None, None,
            ts(rng), summary, detail, event_time))
        i += 1
    cur.executemany(
        "INSERT INTO event (vin, event_type, source, sync_run_id, "
        "actor_employee_id, dealership_id, observed_at, summary, "
        "detail_fields, event_time) VALUES (?,?,?,?,?,?,?,?,?,?)",
        event_rows)

    # Sparse sequence + non-contiguous IDs: delete deterministic
    # middle rows AND the tail rows, leaving sqlite_sequence.seq
    # greater than MAX(event_id).
    max_eid = conn.execute("SELECT MAX(event_id) FROM event").fetchone()[0]
    middle_victims = [max_eid - 500 - k * 37 for k in range(20)]
    tail_victims = list(range(max_eid - 14, max_eid + 1))
    cur.executemany("DELETE FROM event WHERE event_id = ?",
                    [(v,) for v in middle_victims + tail_victims])

    # ---- event_freshness (~682 at production scale) -----------------
    target_fresh = scaled(n_veh, 682)
    fresh_rows = []
    seen = set()
    j = 0
    while len(fresh_rows) < target_fresh:
        vin = vins[(j * 7) % len(vins)]
        etype, esrc = EVENT_TYPES[j % len(EVENT_TYPES)]
        key = (vin, etype, esrc)
        j += 1
        if key in seen:
            continue
        seen.add(key)
        fresh_rows.append((vin, etype, esrc, ts(rng),
                           str(rng.choice(run_ids))))
    cur.executemany(
        "INSERT INTO event_freshness (vin, event_type, source, "
        "last_observed_at, last_sync_run_id) VALUES (?,?,?,?,?)",
        fresh_rows)

    # ---- pending identities: THE production case (seq 3, count 2) ---
    for k in range(3):
        cur.execute(
            "INSERT INTO pending_identity (source, raw_identifier, "
            "identifier_type, status, first_observed_at, last_observed_at, "
            "resolved_vin, resolved_at) VALUES (?,?,?,?,?,?,?,?)",
            ("keyper", f"REH-TAG-{9100 + k}", "stock_number", "pending",
             ts(rng, 7, 8), ts(rng, 12, 13), None, None))
    cur.execute("DELETE FROM pending_identity WHERE pending_identity_id = 2")

    # ---- tasks (production mix + escalation pairs + closed states) --
    n_mddt = scaled(n_veh, 332)
    n_recovrt = scaled(n_veh, 22)
    n_keyt = scaled(n_veh, 8)
    task_specs = ([("install_mdd_beacon", "Lot Operations")] * n_mddt
                  + [("install_recovr_device", "Lot Operations")] * n_recovrt
                  + [("investigate_key_for_recovr", "Lot Operations")] * n_keyt)
    task_rows = []
    for k, (ttype, dept) in enumerate(task_specs):
        vin = vins[(k * 11) % len(vins)]
        standing, completed_at = "outstanding", None
        if k == 3:
            standing, completed_at = "honored", ts(rng, 12, 13)
        elif k in (5, 9, 14):
            standing = "moot"
        # priority and department are NULL: the live pipeline's only
        # task writer (sync/reconciler.py's insert_task call) passes
        # neither, so production rows have neither. The rehearsal
        # frontend smoke caught an earlier version of this generator
        # inventing priority values production never writes.
        task_rows.append((
            vin, None, ttype, None, None,
            standing, "not_started", None,
            None if k % 3 else "system", None if k % 3 else "automatic",
            None, None if k % 7 else "generated by rehearsal rules",
            ts(rng), completed_at))
    cur.executemany(
        "INSERT INTO task (vin, dealership_id, task_type, department, "
        "priority, commitment_standing, execution_status, "
        "assigned_employee_id, ratified_by, ratification_type, "
        "escalated_from_task_id, reason, created_at, completed_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", task_rows)

    # Two escalation pairs: new tasks referencing earlier task_ids
    # (self-FK exercised; escalated_from < task_id always).
    for parent in (1, 2):
        vin = conn.execute("SELECT vin FROM task WHERE task_id = ?",
                           (parent,)).fetchone()[0]
        cur.execute(
            "INSERT INTO task (vin, dealership_id, task_type, department, "
            "priority, commitment_standing, execution_status, "
            "assigned_employee_id, ratified_by, ratification_type, "
            "escalated_from_task_id, reason, created_at, completed_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (vin, None, "investigate_checked_out_key", None, None,
             "outstanding", "not_started", None, "system",
             "automatic", parent, "escalated in rehearsal", ts(rng), None))

    # Sparse task sequence: delete the last task.
    cur.execute("DELETE FROM task WHERE task_id = "
                "(SELECT MAX(task_id) FROM task)")

    # ---- task execution events (small, FK to task) ------------------
    # execution_status is a cache over this log (DATA_MODEL.md) -- keep
    # the pair consistent, exactly as insert_task_execution_event would.
    for tid, transition, cached in ((1, "started", "in_progress"),
                                    (1, "blocked", "blocked"),
                                    (3, "started", "in_progress")):
        cur.execute(
            "INSERT INTO task_execution_event (task_id, transition_type, "
            "actor_employee_id, note, observed_at) VALUES (?,?,?,?,?)",
            (tid, transition, None, f"rehearsal transition {transition}",
             ts(rng, 12, 13)))
        cur.execute("UPDATE task SET execution_status = ? WHERE task_id = ?",
                    (cached, tid))

    # ---- recommendations (2 open + 1 converted with task FK) --------
    for k in range(2):
        cur.execute(
            "INSERT INTO recommendation (vin, severity, title, detail, "
            "rule_source, status, resulting_task_id, created_at, "
            "resolved_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (vins[k * 29], "high", "Key out aging",
             f"rehearsal recommendation {k}", "key_out_aging", "open",
             None, ts(rng), None))
    cur.execute(
        "INSERT INTO recommendation (vin, severity, title, detail, "
        "rule_source, status, resulting_task_id, created_at, resolved_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (vins[97], "high", "Key out aging", "converted in rehearsal",
         "key_out_aging", "converted_to_task", 2, ts(rng, 8, 9),
         ts(rng, 12, 13)))

    # organization / dealership / employee / user_membership stay EMPTY
    # -- the production final backup's exact state.

    conn.commit()

    manifest = {
        "seed": SEED,
        "scale": scale,
        "counts": {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("vehicle", "event", "event_freshness", "task",
                      "task_execution_event", "recommendation", "sync_run",
                      "pending_identity", "organization", "dealership",
                      "employee", "user_membership")
        },
        "sqlite_sequence": {
            r[0]: r[1] for r in conn.execute(
                "SELECT name, seq FROM sqlite_sequence")},
        "max_ids": {
            "event": conn.execute("SELECT MAX(event_id) FROM event").fetchone()[0],
            "task": conn.execute("SELECT MAX(task_id) FROM task").fetchone()[0],
            "pending_identity": conn.execute(
                "SELECT MAX(pending_identity_id) FROM pending_identity"
            ).fetchone()[0],
        },
        "schema_version": conn.execute(
            "SELECT MAX(version) FROM schema_migrations").fetchone()[0],
        "size_bytes": None,  # filled after close
    }
    conn.close()
    manifest["size_bytes"] = os.path.getsize(out_path)
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", choices=("production", "small"),
                    default="production")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--manifest", help="Write counts manifest JSON here")
    args = ap.parse_args(argv)

    manifest = generate(args.out, args.scale, args.force)
    print(json.dumps(manifest, indent=2))
    if args.manifest:
        with open(args.manifest, "w") as fh:
            json.dump(manifest, fh, indent=2)


if __name__ == "__main__":
    main()
