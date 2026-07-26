"""
Core reconciliation logic. This is the largest module in the package
and the main candidate for the Phase 2 Vehicle-object rewrite --
right now these functions each independently walk source dataframes
and produce report-shaped output; Phase 2 would have them build/update
Vehicle objects instead, with reports becoming a final rendering step
over those objects (see ARCHITECTURE.md).

Originally moved verbatim from the original reconcile.py -- no logic
changes. Phase 2 Slice 1 (see IMPLEMENTATION_PLAN.md) added the
optional db_conn/sync_run_id path in reconcile_keyper_tekion below --
still no change to any existing report output; see that function's
docstring for what's new and why. Slice 2 extended the same path to
also capture Keyper's unresolved-identity population (PendingIdentity)
instead of leaving it unpersisted -- see _persist_pending_identity.
Slice 3 added diff-before-write to every persist_* function below (an
Event is only written when its source's discrete status field actually
changed since the last sync -- see each function's docstring) plus
PendingIdentity -> Vehicle promotion, the system's first genuine state
transition -- see _promote_pending_identity_if_resolved.
"""

import pandas as pd

from lotsync.sync.normalizer import last6, stock_prefix
from lotsync.sync.matcher import build_tekion_lookup, build_sold_lookup
from lotsync.sync.state_engine import day_out_bucket
from lotsync.rules.inventory import is_new_car_stock, is_damaged_repair_stock


def _persist_keyper_observation(db_conn, sync_run_id, vin, keyper_status, summary, detail_fields):
    """
    Phase 2 Slice 1 addition. Writes this Keyper record's contribution
    to the Vehicle/Event tables -- a no-op when db_conn is None, which
    is exactly how every existing caller (and every existing test)
    invokes reconcile_keyper_tekion today. Only called for records that
    resolved to an actual VIN (fully_verified, key_out_aging, and the
    sold_key_not_removed_from_keyper case) -- records with no
    resolvable VIN (pending_dms_entry, out_and_unmatched, and every
    data_quality_exceptions case) are deliberately NOT persisted here.
    That population is Slice 2's explicit, written identity-resolution
    decision to make (see IMPLEMENTATION_PLAN.md, Slice 2's Risk
    entry), not something to decide implicitly inside this function.

    Phase 2 Slice 3 addition: diff-before-write, compared against the
    most recent "keyper_observed" Event for this VIN -- NOT against
    vehicle.keyper_status. Comparing against the Vehicle row's current
    field turned out to be the wrong basis in general (see
    persist_tekion_observations' docstring for the idempotency bug this
    caused once a field could be written by more than one observation
    per run); Keyper only ever writes this field once per run today, so
    this produces identical results to a Vehicle-field comparison here,
    but stays correct if that ever stops being true. The Vehicle row's
    current-state field is still upserted unconditionally either way --
    it's a cache of "what do we believe right now," not history, so it
    stays current even on a sync that produces no new Event. See
    IMPLEMENTATION_PLAN.md Slice 3 and DECISION_FRAMEWORK.md's "current
    state is always a derived read."
    """
    if db_conn is None:
        return
    from lotsync.database.repository import upsert_vehicle, insert_event, get_last_event_detail_fields
    previous = get_last_event_detail_fields(db_conn, vin, "keyper_observed")
    upsert_vehicle(db_conn, vin, keyper_status=keyper_status)
    if previous is not None and previous.get("keyper_status") == keyper_status:
        return
    insert_event(db_conn, vin=vin, event_type="keyper_observed", source="keyper",
                 sync_run_id=sync_run_id, summary=summary, detail_fields=detail_fields)


def _promote_pending_identity_if_resolved(db_conn, sync_run_id, raw_identifier, vin):
    """
    Phase 2 Slice 3 addition -- the system's first genuine state
    transition (see DATA_MODEL.md's PendingIdentity entry: "resolution
    ... belongs alongside the general historical-diffing/change-
    detection machinery Slice 3 builds"). Called every time a Keyper
    record resolves to a real Tekion or Sold match; a no-op unless a
    pending_identity row already exists for this exact raw identifier
    with status still 'pending' -- i.e. this specific record was
    previously unresolved and is only now resolving.

    Deliberately reuses the same match already established by the
    caller (reconcile_keyper_tekion's own stock-number/last-6 matching)
    rather than introducing a separate, looser resolution heuristic for
    promotion specifically -- per DECISION_FRAMEWORK.md's "reconciliation
    is not authorship": this connection only counts as earned confidence
    because the ordinary matching logic above already made it, the same
    way every other Keyper match in this pipeline is trusted.

    Must run after the Vehicle row for `vin` already exists (the caller,
    _persist_keyper_observation, upserts it first) -- resolved_vin has
    no FK constraint precisely so this ordering is a real requirement,
    not just a formality (see migrations/0002_pending_identity.sql).
    """
    if db_conn is None:
        return
    from lotsync.database.repository import get_pending_identity, resolve_pending_identity, insert_event
    pending = get_pending_identity(db_conn, source="keyper", raw_identifier=raw_identifier)
    if pending is None or pending["status"] != "pending":
        return
    resolve_pending_identity(db_conn, source="keyper", raw_identifier=raw_identifier, resolved_vin=vin)
    insert_event(
        db_conn, vin=vin, event_type="pending_identity_resolved", source="keyper",
        sync_run_id=sync_run_id,
        summary=f"Keyper identifier '{raw_identifier}' (previously unresolved, "
                f"{pending['identifier_type']}) now resolves to this vehicle",
        detail_fields={"pending_identity_id": pending["pending_identity_id"],
                        "raw_identifier": raw_identifier,
                        "previous_identifier_type": pending["identifier_type"]},
    )


def _persist_pending_identity(db_conn, raw_identifier, identifier_type):
    """
    Phase 2 Slice 2 addition. Captures a Keyper record that never
    resolved to a VIN at all -- the population this function's three
    call sites below cover (tekion_auto_generated_stock_number,
    unrecognized, ambiguous_last6_vin_multiple_matches) is exactly
    today's data_quality_exceptions.csv. See DATA_MODEL.md's
    PendingIdentity entry for why this is a separate table from
    Vehicle, not a vin=NULL row or a sentinel VIN. Capture only --
    resolving one of these into a real Vehicle is Slice 3's job, not
    this one's (see IMPLEMENTATION_PLAN.md Slice 2's Risk entry).
    """
    if db_conn is None:
        return
    from lotsync.database.repository import upsert_pending_identity
    upsert_pending_identity(db_conn, source="keyper", raw_identifier=raw_identifier,
                             identifier_type=identifier_type)


def persist_tekion_observations(tekion_df: pd.DataFrame, sold_df: pd.DataFrame,
                                 db_conn=None, sync_run_id=None):
    """
    Phase 2 Slice 2. Every Tekion-mentioned VIN gets tekion_status/
    stock_number persisted, independent of whether Keyper also has a
    key for it -- this is deliberately a standalone walk over the full
    tekion_df/sold_df, not woven into reconcile_keyper_tekion (Keyper's
    own walk) or build_incoming_or_missing_investigate (which
    deliberately SKIPS Keyper-matched rows -- the wrong population
    here, since every Tekion vehicle needs its status persisted
    regardless of Keyper match). A no-op when db_conn is None, same
    convention as every other Phase 2 write path.

    Master/Unsold and Sold both write to the SAME tekion_status field
    (different values -- e.g. "Stocked In" vs "Sold"), not separate
    fields -- see models/vehicle.py's existing field comment and
    SPRINT_2_REVIEW.md's kickoff assumptions. Sold is walked after
    Master/Unsold so a vehicle present in both (sold but not yet
    removed from the Master/Unsold export) ends up with "Sold" as its
    persisted current status -- Vehicle is a current-state cache, not
    history; the Master/Unsold observation is still preserved as its
    own Event.

    year/make/model are deliberately left unpopulated -- Tekion's
    "Year Make Model" is a single combined string in this pipeline
    today, and no existing code parses it into structured fields; doing
    so isn't required by this slice's Definition of Done.

    Phase 2 Slice 3 addition: diff-before-write, keyed on
    (tekion_status, stock_number) TOGETHER, not tekion_status alone.
    This was a deliberate design discussion, not an implicit choice --
    see tests/fixtures/README.md's K80001/K80002 duplicate-sold-VIN
    fixture (same VIN, same "Sold" status, two different stock
    numbers, built specifically to exercise tekion_sync_conflicts.csv).
    A status-only diff would treat the second row as a no-op repeat and
    silently drop the very contradiction that fixture exists to
    surface. The claim Tekion is actually making each time is "stock
    <X> was sold," not just "status = Sold" -- two different stock
    numbers under an identical status label are two different claims
    (DECISION_FRAMEWORK.md's claims test), so this is a more faithful
    reading of "only claims earn history," not a loosening of it.
    stock_number doesn't drift continuously the way days_out does (it's
    stable except in exactly this kind of real, worth-surfacing
    contradiction), so including it here doesn't reopen the noise
    problem the single-field recommendation in IMPLEMENTATION_PLAN.md
    was written to prevent. Keyper/MDD/RecovR have no equivalent
    secondary identifying field in scope, so they stay a plain
    single-field diff.

    The diff is compared against the most recent matching-event_type
    Event for this VIN ("tekion_observed" for the master/unsold loop,
    "tekion_sold" for the sold loop) -- NOT against vehicle.tekion_status.
    This distinction is load-bearing here, unlike Keyper/MDD/RecovR: a
    VIN present in both tekion_df and sold_df has BOTH loops write to
    the SAME vehicle.tekion_status field within one run (sold wins, by
    design). Diffing against that shared, mid-run-mutated field meant
    every such VIN generated 2 spurious Events on every single rerun,
    forever -- the master-list write always saw the previous run's
    final "Sold" value and looked changed, then the sold-list write saw
    the "Stocked In" the master-list write had just reasserted moments
    earlier and also looked changed. Comparing each loop against its
    own event_type's history instead keeps the two claims -- "master
    list says X" and "sold list says Y" -- correctly independent of
    each other and of whatever the shared cache currently holds.

    KNOWN, ACCEPTED LIMITATION: diffing against "the single most recent
    Event of this type" is exact when a VIN has at most one observation
    per event_type per run -- true for the entire supported operational
    model. It is NOT exact when a single sync's own source data asserts
    the SAME event_type more than once for the SAME VIN with different
    values (concretely: sold_df containing two rows for one VIN under
    different stock numbers, both "tekion_sold" -- an internally
    contradictory Tekion export, not a normal operational state). In
    that case, each rerun of an unresolved, still-contradictory export
    re-fires both Events instead of settling to zero new Events. Fixing
    this exactly would require comparing this run's whole ordered
    sequence of same-(vin, event_type) observations against the
    previous run's whole sequence, not just the latest value --
    meaningfully more machinery, deferred deliberately per
    DECISION_FRAMEWORK.md's "don't build ahead of a demonstrated
    workflow": no real workflow has asked for perfect idempotency on an
    upstream data contradiction that tekion_sync_conflicts.csv already
    surfaces to a human, unaffected by anything here, every single day.
    Reconsider only if a real operational case demonstrates this matters
    (e.g. an unfixed Tekion contradiction persisting for weeks actually
    floods a dashboard's activity feed once Slice 7 builds one).
    """
    if db_conn is None:
        return
    from lotsync.database.repository import upsert_vehicle, insert_event, get_last_event_detail_fields

    def _persist(vin, status, stock, event_type, summary, detail_fields):
        previous = get_last_event_detail_fields(db_conn, vin, event_type)
        previous_key = (previous.get("tekion_status"), previous.get("tekion_stock")) if previous else None
        upsert_vehicle(db_conn, vin, tekion_status=status, stock_number=stock)
        if previous_key == (status, stock):
            return
        insert_event(db_conn, vin=vin, event_type=event_type, source="tekion",
                     sync_run_id=sync_run_id, summary=summary, detail_fields=detail_fields)

    for _, trow in tekion_df.iterrows():
        vin = trow["VIN #"]
        _persist(
            vin, trow["Status"], trow["Stock #"], "tekion_observed",
            summary=f"Tekion: {trow['Status']}, stock {trow['Stock #']}",
            detail_fields={"tekion_status": trow["Status"], "tekion_stock": trow["Stock #"],
                            "stocked_in_date": trow["Stocked In Date"]},
        )

    for _, srow in sold_df.iterrows():
        vin = srow["VIN #"]
        _persist(
            vin, srow["Status"], srow["Stock #"], "tekion_sold",
            summary=f"Tekion: sold, stock {srow['Stock #']}, {srow['Sold Date']}",
            detail_fields={"tekion_status": srow["Status"], "tekion_stock": srow["Stock #"],
                            "sold_date": srow["Sold Date"]},
        )


def persist_mdd_observations(mdd_df: pd.DataFrame, db_conn=None, sync_run_id=None):
    """
    Phase 2 Slice 2. Only annotates VINs already known as a Vehicle
    from another source -- MDD's not-paired export can span multiple
    stores/dealerships (see importers/mdd.py), and VIN is the one
    reliable identity signal here. MDD's own "Dealership" column is
    deliberately NOT used to scope this write: if a VIN already
    resolves to a Vehicle we know (which, by construction, only
    happens via our own single-store Tekion import -- see
    persist_tekion_observations), that's a stronger, VIN-based
    guarantee of store-correctness than trusting MDD's own dealership
    tag, consistent with this project's existing skepticism toward
    other sources' store-attribution fields (see README.md, Keyper's
    unreliable System field).

    Only positive evidence is ever recorded: MDD only ever supplies a
    "not paired" exception list, never a full assignment feed, so
    mdd_status is set to "not_paired" for exactly the VINs mentioned
    here and left untouched (NULL/unknown) for everything else -- never
    inferred as "paired." See README.md's own documented limitation.

    Phase 2 Slice 3 addition: diff-before-write on mdd_status. This is
    the write path where diffing matters most in practice -- MDD's
    export re-reports every still-unpaired vehicle on every single
    sync, so without diffing this function alone would have generated a
    new Event every run for every vehicle that simply remains unpaired,
    forever. Diffing turns that into exactly one Event the first time a
    vehicle is observed not-paired, then silence until something
    actually changes.

    Compared against the most recent "mdd_observed" Event, not against
    vehicle.mdd_status -- see persist_tekion_observations' docstring for
    why the Vehicle field is the wrong general basis for this decision.
    MDD only ever writes this field once per VIN per run, so this
    produces identical results to a Vehicle-field comparison here.
    """
    if db_conn is None:
        return
    from lotsync.database.repository import upsert_vehicle, insert_event, get_last_event_detail_fields
    known_vins = {row[0] for row in db_conn.execute("SELECT vin FROM vehicle")}

    for _, row in mdd_df.iterrows():
        vin = str(row["vin"]).strip()
        if vin not in known_vins:
            continue
        previous = get_last_event_detail_fields(db_conn, vin, "mdd_observed")
        upsert_vehicle(db_conn, vin, mdd_status="not_paired")
        if previous is not None and previous.get("mdd_status") == "not_paired":
            continue
        insert_event(
            db_conn, vin=vin, event_type="mdd_observed", source="mdd",
            sync_run_id=sync_run_id,
            summary=f"MDD: not paired, stock {row['stock']}",
            detail_fields={"mdd_status": "not_paired", "mdd_stock": row["stock"],
                            "mdd_dealership": row["Dealership"]},
        )


def persist_recovr_observations(recovr_df: pd.DataFrame, db_conn=None, sync_run_id=None):
    """
    Phase 2 Slice 2. Unlike MDD, RecovR's full list includes both
    paired and unpaired vehicles, so both are recorded here as positive
    evidence either way. Only annotates VINs already known as a Vehicle
    -- RecovR's export can span a multi-brand "Kia umbrella" account
    (see importers/recovr.py), so, same restraint as MDD above and
    RapidRecon below, this never creates a new Vehicle row from RecovR
    data alone.

    Short (non-17-char) VIN fragments are resolved by unique last-6
    suffix match against already-known VINs -- if zero or more than one
    candidate matches, the row is skipped rather than guessed at, the
    same "don't guess" convention already used in
    build_tracker_install_tasks and build_recovr_install_from_keyper.
    Not reused directly from those functions, since both apply
    additional business-scoping (store prefix, sold-exclusion) that's
    a report-generation decision, out of scope for this raw fact write
    -- see SPRINT_2_REVIEW.md.

    Phase 2 Slice 3 addition: diff-before-write on recovr_status. Unlike
    MDD, RecovR reports both paired and unpaired positively every run,
    so without diffing every RecovR-covered vehicle would generate a new
    Event on every single sync regardless of pairing status ever
    changing.

    Compared against the most recent "recovr_observed" Event, not
    against vehicle.recovr_status -- see persist_tekion_observations'
    docstring for why the Vehicle field is the wrong general basis for
    this decision. RecovR only ever writes this field once per VIN per
    run, so this produces identical results to a Vehicle-field
    comparison here.
    """
    if db_conn is None:
        return
    from lotsync.database.repository import upsert_vehicle, insert_event, get_last_event_detail_fields
    known_vins = {row[0] for row in db_conn.execute("SELECT vin FROM vehicle")}

    for _, row in recovr_df.iterrows():
        raw_vin = str(row["VIN"]).strip()
        status = "paired" if row["Paired"] == "Yes" else "not_paired"

        if len(raw_vin) == 17:
            vin = raw_vin if raw_vin in known_vins else None
        else:
            frag = last6(raw_vin)
            hits = [v for v in known_vins if v.endswith(frag)]
            vin = hits[0] if len(hits) == 1 else None

        if vin is None:
            continue

        previous = get_last_event_detail_fields(db_conn, vin, "recovr_observed")
        upsert_vehicle(db_conn, vin, recovr_status=status)
        if previous is not None and previous.get("recovr_status") == status:
            continue
        insert_event(
            db_conn, vin=vin, event_type="recovr_observed", source="recovr",
            sync_run_id=sync_run_id,
            summary=f"RecovR: {status}, stock {row['Stock Number']}",
            detail_fields={"recovr_status": status, "recovr_stock": row["Stock Number"],
                            "recovr_vin_raw": raw_vin},
        )


def persist_rapidrecon_observations(rapidrecon_df: pd.DataFrame, db_conn=None, sync_run_id=None):
    """
    Phase 2 Slice 2. Writes an Event only -- no Vehicle status field is
    set. Two deliberate assumptions decided during Sprint 2's kickoff,
    not invented silently:

    1. No new "recon_status" (or similar) field exists on Vehicle for
       this, and none is added here. IMPLEMENTATION_PLAN.md's Slice 2
       scope text says all five sources "update the relevant Vehicle
       status field," but DATA_MODEL.md defines no such field for
       RapidRecon, and ARCHITECTURE.md explicitly treats RapidRecon as
       "contextual enrichment only, not yet a state provider" until a
       confirmed Step-value mapping exists (`Step` has 77 distinct
       values with no confirmed business meaning -- see
       enrich_with_rapidrecon above). Inventing a field now would
       repeat the exact mistake this project already corrected once
       (the original unfounded Incoming/Missing day thresholds).
    2. Only annotates VINs already known as a Vehicle -- never creates
       one. RapidRecon spans multiple stores/brands in one export (per
       importers/rapidrecon.py, only ~72% of rows share this store's
       Tekion prefix in real data), so an out-of-scope RapidRecon-only
       VIN must never silently create a Vehicle row for a vehicle this
       deployment doesn't actually have.

    If a real Vehicle-level field is ever wanted here, that's a
    DATA_MODEL.md governance change to make explicitly then, not a
    default to slide into now.
    """
    if db_conn is None:
        return
    from lotsync.database.repository import insert_event
    known_vins = {row[0] for row in db_conn.execute("SELECT vin FROM vehicle")}

    recon_cols = ["Step", "DIS", "DIR", "Priority", "Recall", "Note"]
    available_cols = [c for c in recon_cols if c in rapidrecon_df.columns]

    for _, row in rapidrecon_df.iterrows():
        vin = str(row["VIN"]).strip()
        if vin not in known_vins:
            continue
        detail_fields = {f"recon_{c.lower()}": row[c] for c in available_cols}
        insert_event(
            db_conn, vin=vin, event_type="rapidrecon_observed", source="rapidrecon",
            sync_run_id=sync_run_id,
            summary=f"RapidRecon: Step={row.get('Step', 'unknown')}",
            detail_fields=detail_fields,
        )


def reconcile_keyper_tekion(keyper_df: pd.DataFrame, tekion_df: pd.DataFrame,
                             sold_df: pd.DataFrame, sync_date, day_out_buckets,
                             db_conn=None, sync_run_id=None):
    """
    Walks every Keyper record and routes it into exactly one of:
    fully_verified, key_out_aging, flag_to_controller, sold_removal
    (handled separately in build_sold_vehicles_report), or
    data_quality_exceptions. Returns the first four as separate lists
    plus the set of matched Tekion row indexes (needed to compute
    incoming_or_missing afterward).

    db_conn/sync_run_id (Phase 2 Slice 1, both optional, default None):
    when a database connection is passed, every record that resolves to
    a real VIN additionally upserts a Vehicle row and writes an Event --
    pure addition, see _persist_keyper_observation above. Leaving
    db_conn as None (every call site before Slice 1, and every existing
    test) reproduces the exact original behavior with zero DB activity.
    """
    tekion_by_stock, tekion_by_last6, tekion_prefixes = build_tekion_lookup(tekion_df)
    sold_by_stock, sold_by_last6 = build_sold_lookup(sold_df)

    fully_verified = []
    key_out_aging = []
    flag_to_controller = []
    exceptions = []
    matched_tekion_idx = set()

    for _, krow in keyper_df.iterrows():
        itype = krow["identifier_type"]
        ival = krow["identifier_value"]
        raw = krow["identifier_raw"]
        status = krow["Status"]

        if itype == "non_vehicle":
            continue

        base = {
            "keyper_identifier": raw,
            "keyper_status": status,
            "keyper_system": krow["System"],
            "keyper_checkout_date": krow["Checkout Date"],
        }

        if itype in ("tekion_auto_generated_stock_number", "unrecognized"):
            exceptions.append({**base, "reason": itype})
            _persist_pending_identity(db_conn, raw_identifier=raw, identifier_type=itype)
            continue

        # Resolve against Tekion, but don't count store-mismatched
        # prefixes as failures -- they belong to a store we don't have
        # a Tekion export for.
        tekion_idx = None
        out_of_scope = False
        if itype == "stock_number":
            tekion_idx = tekion_by_stock.get(ival)
            if tekion_idx is None and stock_prefix(ival) not in tekion_prefixes:
                out_of_scope = True
        elif itype == "last6_vin":
            candidates = tekion_by_last6.get(ival, [])
            if len(candidates) == 1:
                tekion_idx = candidates[0]
            elif len(candidates) > 1:
                exceptions.append({**base, "reason": "ambiguous_last6_vin_multiple_matches"})
                _persist_pending_identity(db_conn, raw_identifier=raw,
                                           identifier_type="ambiguous_last6_vin_multiple_matches")
                continue

        if out_of_scope:
            continue  # different store; not ours to report on

        if tekion_idx is not None:
            matched_tekion_idx.add(tekion_idx)
            trow = tekion_df.loc[tekion_idx]
            match_info = {
                **base,
                "tekion_stock": trow["Stock #"],
                "tekion_vin": trow["VIN #"],
                "tekion_vehicle": trow["Year Make Model"],
            }
            if status == "In":
                fully_verified.append(match_info)
                _persist_keyper_observation(
                    db_conn, sync_run_id, trow["VIN #"], "In",
                    summary=f"Keyper: key checked In, matched Tekion stock {trow['Stock #']}",
                    detail_fields={"keyper_identifier": raw, "keyper_status": "In",
                                    "tekion_stock": trow["Stock #"]},
                )
            else:  # "Out"
                days_out = None
                if pd.notna(krow["checkout_dt"]):
                    days_out = (sync_date - krow["checkout_dt"]).days
                match_info["days_out"] = days_out
                match_info["aging_bucket"] = (
                    day_out_bucket(days_out, day_out_buckets) if days_out is not None else "unknown (bad checkout date)"
                )
                key_out_aging.append(match_info)
                _persist_keyper_observation(
                    db_conn, sync_run_id, trow["VIN #"], "Out",
                    summary=f"Keyper: key checked Out, matched Tekion stock {trow['Stock #']}"
                            + (f" ({days_out} days out)" if days_out is not None else ""),
                    detail_fields={"keyper_identifier": raw, "keyper_status": "Out",
                                    "tekion_stock": trow["Stock #"], "days_out": days_out},
                )
            _promote_pending_identity_if_resolved(db_conn, sync_run_id, raw, trow["VIN #"])
            continue

        # No Tekion match -- check whether it's actually already sold
        # before assuming Pending DMS Entry.
        sold_idx = None
        if itype == "stock_number":
            sold_idx = sold_by_stock.get(ival)
        elif itype == "last6_vin":
            sc = sold_by_last6.get(ival, [])
            if len(sc) == 1:
                sold_idx = sc[0]

        if sold_idx is not None:
            srow = sold_df.loc[sold_idx]
            flag_to_controller.append({
                **base,
                "reason": "sold_key_not_removed_from_keyper",
                "tekion_stock": srow["Stock #"],
                "tekion_vin": srow["VIN #"],
                "sold_date": srow["Sold Date"],
            })
            _persist_keyper_observation(
                db_conn, sync_run_id, srow["VIN #"], status,
                summary=f"Keyper: key still present ({status}) for Tekion stock "
                        f"{srow['Stock #']}, sold {srow['Sold Date']}",
                detail_fields={"keyper_identifier": raw, "keyper_status": status,
                                "tekion_stock": srow["Stock #"], "sold_date": srow["Sold Date"]},
            )
            _promote_pending_identity_if_resolved(db_conn, sync_run_id, raw, srow["VIN #"])
        else:
            reason = "pending_dms_entry" if status == "In" else "out_and_unmatched_no_tekion_record"
            flag_to_controller.append({**base, "reason": reason})

    return (pd.DataFrame(fully_verified), pd.DataFrame(key_out_aging),
            pd.DataFrame(flag_to_controller), pd.DataFrame(exceptions),
            matched_tekion_idx)


def build_incoming_or_missing_investigate(tekion_df: pd.DataFrame, matched_tekion_idx: set,
                                           sync_date, incoming_missing_buckets,
                                           new_car_buckets) -> pd.DataFrame:
    """
    This report used to be framed as 'incoming fresh trades,' but that's
    only one explanation for 'active in Tekion, no Keyper key at all.'
    There are three, and they behave differently:

    1. A physical trade-in already on the lot, just not keyed into
       Keyper yet -- normal turnaround per the real workflow is 2 days
       (checked every morning, stocked into Keyper by midshift).
    2. A brand-new car ordered from the factory, Stocked In in Tekion
       as soon as it's allocated, but not yet physically at the
       dealership -- no Keyper key is expected until transport drops
       it off, so its normal "no key yet" window is naturally longer.
    3. A new vehicle that arrived damaged and is in/awaiting repair --
       physically present, but not lot-ready, so neither other scale's
       assumptions fit it. No priority bucket applied yet; no grounded
       repair-duration baseline exists.

    These are told apart by stock number: a bare 'K' followed only by
    digits (e.g. K30707) is a new-car order; a stock number ending in
    'DM' is damaged/in-repair; anything else (KB, KT, KP, K####A,
    K####SL, etc.) is treated as a trade/other vehicle already on the
    lot. See rules/inventory.py for how these were defined.

    There's also a fourth, unrelated explanation this report can't
    distinguish from an overdue Trade/Other case: a vehicle that was
    sold, never marked sold in Tekion, and had its Keyper key deleted
    once the fob went out the door. That case is invisible to the
    Sold-report cross-check elsewhere in this module, since a sale
    never recorded in Tekion never makes it into the Sold report either.

    Age is computed from Stocked In Date directly, not Tekion's own
    "Age (Days)" field -- that field diverges from the Stocked-In-Date-
    implied age by more than 5 days on ~10% of rows in this export, so
    it isn't a reliable basis even for a rough signal.
    """
    rows = []
    for idx, trow in tekion_df.iterrows():
        if idx in matched_tekion_idx or trow["is_internal_fleet"]:
            continue
        stocked_in_dt = pd.to_datetime(trow["Stocked In Date"], format="%b %d %Y", errors="coerce")
        days = (sync_date - stocked_in_dt).days if pd.notna(stocked_in_dt) else None

        stock = trow["Stock #"]
        if is_new_car_stock(stock):
            vehicle_type = "New Car (Awaiting Dropoff)"
            priority = day_out_bucket(days, new_car_buckets) if days is not None else "unknown (bad stocked-in date)"
        elif is_damaged_repair_stock(stock):
            vehicle_type = "New (Damaged - In Repair)"
            priority = "not yet timed - no repair-duration baseline set"
        else:
            vehicle_type = "Trade/Other"
            priority = day_out_bucket(days, incoming_missing_buckets) if days is not None else "unknown (bad stocked-in date)"

        rows.append({
            "vehicle_type": vehicle_type,
            "priority": priority,
            "days_since_stocked_in": days,
            "tekion_stock": stock,
            "tekion_vin": trow["VIN #"],
            "tekion_vehicle": trow["Year Make Model"],
            "stocked_in_date": trow["Stocked In Date"],
        })
    df = pd.DataFrame(rows)
    if len(df):
        df = df.sort_values("days_since_stocked_in", ascending=False, na_position="last")
    return df


def build_sold_vehicles_report(sold_df: pd.DataFrame, keyper_df: pd.DataFrame,
                                recovr_df: pd.DataFrame, sync_date=None) -> pd.DataFrame:
    """
    For every sold vehicle: is a key still checked into Keyper (either
    In or Out -- either way it shouldn't still be tracked), and does
    RecovR still show it Paired? MDD can't be checked here -- we only
    have MDD's "not paired" export, not the full assignment list, so
    there's no way to confirm a sold car's beacon was actually removed
    versus simply not present in the "not paired" file for some other
    reason. That's flagged explicitly rather than guessed at. See
    importers/mdd_history.py for what would close this gap.

    days_since_sale matters for prioritization once this runs against
    real historical data, not just a recent window: a vehicle sold last
    week still showing a Keyper key is normal pipeline lag, not a
    problem. A vehicle sold three years ago still showing one is a
    genuinely stale, probably-forgotten record -- the actual target of
    a historical cleanup sweep. sync_date is optional (defaults to
    "today") so this still works for the ordinary rolling-window case
    where staleness prioritization matters less.
    """
    import datetime as _dt
    if sync_date is None:
        sync_date = _dt.datetime.now()

    keyper_by_stock, keyper_by_last6 = {}, {}
    for idx, row in keyper_df.iterrows():
        if row["identifier_type"] == "stock_number":
            keyper_by_stock.setdefault(row["identifier_value"], []).append(idx)
        elif row["identifier_type"] == "last6_vin":
            keyper_by_last6.setdefault(row["identifier_value"], []).append(idx)

    # If a VIN appears more than once in RecovR, prefer any Paired=Yes
    # row over Paired=No, regardless of row order -- see reconcile.py
    # code-review notes for why a plain last-occurrence-wins dict here
    # would be a silent correctness risk.
    recovr_by_vin = {}
    for i, row in recovr_df.iterrows():
        v = str(row["VIN"]).strip()
        if v not in recovr_by_vin or row["Paired"] == "Yes":
            recovr_by_vin[v] = i

    rows = []
    for _, srow in sold_df.iterrows():
        vin = str(srow["VIN #"]).strip()
        stock = str(srow["Stock #"]).strip().upper()

        keyper_hits = keyper_by_stock.get(stock, []) + keyper_by_last6.get(last6(vin), [])
        keyper_still_present = len(keyper_hits) > 0

        recovr_status = "not_found"
        if vin in recovr_by_vin:
            paired = recovr_df.loc[recovr_by_vin[vin], "Paired"]
            recovr_status = "still_paired" if paired == "Yes" else "unpaired"

        needs_removal = keyper_still_present or recovr_status == "still_paired"

        sold_dt = pd.to_datetime(srow["Sold Date"], format="%b %d %Y", errors="coerce")
        days_since_sale = (sync_date - sold_dt).days if pd.notna(sold_dt) else None

        rows.append({
            "overall_status": "needs_removal" if needs_removal else "sale_complete",
            "days_since_sale": days_since_sale,
            "vin": vin,
            "stock": srow["Stock #"],
            "sold_date": srow["Sold Date"],
            "vehicle": srow["Year Make Model"],
            "keyper_still_present": keyper_still_present,
            "recovr_status": recovr_status,
            "mdd_status": "unknown - only MDD's not-paired list is available, not the full assignment feed",
        })

    df = pd.DataFrame(rows)
    if len(df):
        df = df.sort_values("days_since_sale", ascending=False, na_position="last")
    return df


def enrich_with_rapidrecon(df: pd.DataFrame, vin_column: str,
                            rapidrecon_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds RapidRecon context (Step, DIS, DIR, Priority, Recall count, Note)
    to any report that has a VIN column, when a match exists. Does NOT
    reclassify anything -- RapidRecon's "Step" field has 77 distinct
    values in real data, many with only a handful of rows, and no
    confirmed business meaning for which ones mean "recon complete" vs.
    "still in progress." Rather than guess at that (the same mistake
    made early on with the Incoming/Missing day thresholds), this only
    surfaces the raw context so a human can judge -- exactly the same
    "sorted, unlabeled" pattern used before real numbers existed for
    the fresh-trade turnaround.

    Real-world motivation: an actual RapidRecon note on a 2021 Dodge
    Durango read "KEYS HAVE NEVER BEEN IN KEYPER... has someone checked
    under last 6 of vin#?" -- staff manually doing, by hand, close to
    what this reconciliation pipeline already automates. Surfacing that
    same context automatically on the reports that already flag a
    missing key turns a search through recon notes into something
    that's just already there.
    """
    if vin_column not in df.columns or df.empty:
        return df

    recon_cols = ["VIN", "Step", "DIS", "DIR", "Priority", "Recall", "Note"]
    recon_slim = rapidrecon_df[[c for c in recon_cols if c in rapidrecon_df.columns]].copy()
    recon_slim = recon_slim.rename(columns={
        "VIN": "_recon_vin", "Step": "recon_step", "DIS": "recon_days_in_stock",
        "DIR": "recon_days_in_recon", "Priority": "recon_priority",
        "Recall": "recon_open_recalls", "Note": "recon_note",
    })
    # A VIN could theoretically appear more than once in RapidRecon
    # (e.g. re-acquired later); keep the first occurrence only, same
    # first-occurrence convention used elsewhere in this pipeline.
    recon_slim = recon_slim.drop_duplicates(subset="_recon_vin", keep="first")

    merged = df.merge(recon_slim, left_on=vin_column, right_on="_recon_vin", how="left")
    merged = merged.drop(columns=["_recon_vin"])
    return merged


def build_recovr_install_from_keyper(fully_verified: pd.DataFrame, key_out_aging: pd.DataFrame,
                                      exceptions: pd.DataFrame, recovr_df: pd.DataFrame,
                                      rapidrecon_df: pd.DataFrame):
    """
    A different starting point than build_tracker_install_tasks(),
    which starts from Tekion's "Stocked In" status. This starts from
    Keyper instead -- a key physically in your possession is arguably
    a stronger signal a vehicle is really on the lot than a DMS status
    field, especially given the Tekion data-quality issues found
    elsewhere in this project (auto-generated placeholder stock
    numbers, sold-but-still-shows-stocked-in conflicts).

    Population: every Keyper record that resolved to an active,
    UNSOLD Tekion vehicle (fully_verified + key_out_aging -- both are
    already, by construction, matched against Tekion's Stocked-In-only
    export, so "sold" is already excluded without an extra check).
    From there:
      - excluded if RapidRecon's Step is WHOLESALE or AT AUCTION (the
        two step values with reasonably confident business meaning,
        confirmed against real data -- see ARCHITECTURE.md on why the
        other 75+ Step values aren't used for exclusion decisions)
      - excluded if RecovR already shows Paired=Yes for that VIN
      - flagged separately, not silently dropped, if RapidRecon shows
        Step=Archive (ambiguous meaning -- could be sold, wholesaled,
        or something else not confirmed) or if a short (non-17-char)
        RecovR VIN fragment can't be confidently resolved to exactly
        one vehicle

    Returns (install_list, needs_review, unresolved_keyper_identities):
      - install_list: the actual "go install these" list
      - needs_review: Archive-step or ambiguous-fragment cases, held
        out rather than auto-included or auto-excluded
      - unresolved_keyper_identities: Keyper records with a physical
        key (per Keyper) that never resolved to a specific Tekion
        vehicle at all (the ambiguous_last6/auto-generated/unrecognized
        exceptions) -- these ARE cars on your lot, but this pipeline
        can't currently say which VIN to check RecovR against.
    """
    matched = pd.concat([fully_verified, key_out_aging], ignore_index=True) if len(fully_verified) or len(key_out_aging) else pd.DataFrame()
    if matched.empty:
        return pd.DataFrame(), pd.DataFrame(), exceptions

    # RecovR lookup: full VINs matched directly; short fragments matched
    # by last-6 against the candidate pool, same approach as
    # build_tracker_install_tasks -- only counted if exactly one
    # candidate resolves, never guessed.
    recovr_paired_vins = set()
    recovr_fragment_rows = []
    for _, row in recovr_df.iterrows():
        vin = str(row["VIN"]).strip()
        if row["Paired"] != "Yes":
            continue
        if len(vin) == 17:
            recovr_paired_vins.add(vin)
        else:
            recovr_fragment_rows.append(vin)

    candidate_vins = set(matched["tekion_vin"].astype(str).str.strip())
    for frag in recovr_fragment_rows:
        hits = [v for v in candidate_vins if v.endswith(frag)]
        if len(hits) == 1:
            recovr_paired_vins.add(hits[0])
        # ambiguous or no match -- not added; matches the
        # "don't guess" convention used everywhere else in this pipeline

    recon_cols = ["VIN", "Step"]
    recon_slim = rapidrecon_df[[c for c in recon_cols if c in rapidrecon_df.columns]].copy()
    recon_slim = recon_slim.rename(columns={"VIN": "_recon_vin", "Step": "recon_step"})
    recon_slim = recon_slim.drop_duplicates(subset="_recon_vin", keep="first")

    matched = matched.merge(recon_slim, left_on="tekion_vin", right_on="_recon_vin", how="left")
    matched = matched.drop(columns=["_recon_vin"])
    matched["already_has_recovr"] = matched["tekion_vin"].astype(str).str.strip().isin(recovr_paired_vins)

    wholesale_steps = {"WHOLESALE", "AT AUCTION"}
    step_upper = matched["recon_step"].astype(str).str.strip().str.upper()

    is_wholesale = step_upper.isin(wholesale_steps)
    is_archive = step_upper == "ARCHIVE"

    install_list = matched[~matched["already_has_recovr"] & ~is_wholesale & ~is_archive].copy()
    needs_review = matched[~matched["already_has_recovr"] & is_archive].copy()

    return install_list, needs_review, exceptions


def build_tracker_install_tasks(tekion_df: pd.DataFrame, sold_df: pd.DataFrame,
                                 mdd_df: pd.DataFrame, recovr_df: pd.DataFrame,
                                 store_name: str) -> pd.DataFrame:
    """
    See rules/tracker.py for why this logic lives here and not there.
    """
    active_vins = set(
        tekion_df.loc[~tekion_df["is_internal_fleet"], "VIN #"].astype(str).str.strip()
    )
    sold_vins = set(sold_df["VIN #"].astype(str).str.strip())
    tekion_prefixes = {stock_prefix(s) for s in tekion_df["Stock #"]}

    tasks = []

    mdd_not_paired = mdd_df[mdd_df["Dealership"] == store_name]
    for _, row in mdd_not_paired.iterrows():
        vin = str(row["vin"]).strip()
        if vin in sold_vins or vin not in active_vins:
            continue
        tasks.append({
            "source": "MDD", "task": "install_mdd_beacon", "vin": vin,
            "stock": row["stock"], "vehicle": f"{row['year']} {row['make']} {row['model']}",
        })

    recovr_not_paired = recovr_df[recovr_df["Paired"] == "No"]
    for _, row in recovr_not_paired.iterrows():
        vin = str(row["VIN"]).strip()
        stock = str(row["Stock Number"]).strip().upper()
        if len(vin) == 17:
            if vin in sold_vins:
                continue
            if vin not in active_vins:
                if stock_prefix(stock) not in tekion_prefixes:
                    continue
        else:
            frag = last6(vin)
            candidates = [v for v in active_vins if v.endswith(frag)]
            if len(candidates) != 1:
                continue
            vin = candidates[0]
            if vin in sold_vins:
                continue
        tasks.append({
            "source": "RecovR", "task": "install_recovr_device", "vin": vin,
            "stock": row["Stock Number"], "vehicle": f"{row['Year']} {row['Make']} {row['Model']}",
        })

    return pd.DataFrame(tasks)
