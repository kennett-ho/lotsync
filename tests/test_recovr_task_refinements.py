"""
Friday MVP task-generation refinements (Sprint 3.8) -- dedicated
regression coverage for the three RecovR/Keyper-related Task types and
the philosophy distinguishing them, separate from
test_event_fidelity.py's WholesaleExclusionTest (which predates this
refinement) and test_database_slice5.py's discharge-mechanic tests
(which exercise these types incidentally, through the shared synthetic
fixture, as part of testing something else).

Hand-built minimal DataFrames throughout, not the shared
tests/fixtures/synthetic/*.csv set -- these scenarios need precise,
independently-controlled Keyper/RecovR/RapidRecon combinations per
test, and adding rows to the shared fixture to cover them would ripple
into every other test that already asserts exact counts against it
(the same reasoning test_event_fidelity.py's own docstring already
gives for the same choice).

See sync/reconciler.py's "Task-generation philosophy" block (just above
build_tracker_install_tasks) for what installation vs. investigation
means; this file exists to prove that distinction holds in code, not
just in the docstring.
"""

import unittest

import pandas as pd

from lotsync.database.repository import connect, get_open_task, get_task
from lotsync.rules.aging import KEY_OUT_INVESTIGATE_THRESHOLD_DAYS
from lotsync.sync.reconciler import (
    build_tracker_install_tasks, generate_install_tasks,
    persist_tekion_observations, persist_recovr_observations,
)

_EMPTY_SOLD = pd.DataFrame(columns=["Stock #", "VIN #", "Status", "Sold Date", "Year Make Model"])
_EMPTY_MDD = pd.DataFrame(columns=["vin", "stock", "year", "make", "model", "Dealership", "Geofence"])
_EMPTY_RAPIDRECON = pd.DataFrame(columns=["VIN", "Step"])


def _tekion_df(vin, stock):
    return pd.DataFrame([{
        "Stock #": stock, "VIN #": vin, "Status": "Stocked In",
        "Year Make Model": "2024 Test Sedan", "Stocked In Date": "Jul 18 2026",
        "is_internal_fleet": False,
    }])


def _recovr_not_paired_df(vin, stock):
    return pd.DataFrame([{
        "VIN": vin, "Stock Number": stock, "Paired": "No",
        "Year": "2024", "Make": "Test", "Model": "Sedan",
    }])


def _recovr_paired_df(vin, stock):
    return pd.DataFrame([{
        "VIN": vin, "Stock Number": stock, "Paired": "Yes",
        "Year": "2024", "Make": "Test", "Model": "Sedan",
    }])


def _fully_verified_df(*vins):
    """Only "tekion_vin" is ever read from this -- see build_tracker_install_tasks."""
    return pd.DataFrame([{"tekion_vin": v} for v in vins], columns=["tekion_vin"])


def _empty_key_out_aging():
    return pd.DataFrame(columns=["tekion_vin", "days_out", "tekion_stock", "tekion_vehicle"])


def _key_out_aging_df(vin, stock, days_out):
    return pd.DataFrame([{
        "tekion_vin": vin, "days_out": days_out,
        "tekion_stock": stock, "tekion_vehicle": "2024 Test Sedan",
    }])


def _multi_key_out_aging_df(*rows):
    """
    rows: (vin, stock, days_out) tuples; days_out may be None to
    simulate a bad/missing checkout date. Built as ONE DataFrame from
    several dict rows -- unlike _key_out_aging_df's single-row shape,
    this reproduces reconcile_keyper_tekion's actual construction
    (pd.DataFrame(key_out_aging) from a list of per-Keyper-record
    dicts), which is what silently upcasts a None-containing "days_out"
    column to float64 (None -> NaN) in production. A single-row frame
    never triggers that promotion, which is why this file's other
    tests never caught the bug KeyOutDaysNanRegressionTest below
    covers.
    """
    return pd.DataFrame([
        {"tekion_vin": vin, "days_out": days_out, "tekion_stock": stock, "tekion_vehicle": "2024 Test Sedan"}
        for vin, stock, days_out in rows
    ])


def _rapidrecon_df(vin, step):
    return pd.DataFrame([{"VIN": vin, "Step": step}])


VIN = "1TESTVIN000000010"
STOCK = "K30010"


class InstallRecovrTest(unittest.TestCase):
    """
    Generate when: active Tekion inventory, not Wholesale/At Auction,
    Keyper status In, no RecovR device.
    """

    def test_keyper_in_and_recovr_missing_generates_install_task(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(VIN, STOCK),
            "TestStore", rapidrecon_df=_EMPTY_RAPIDRECON,
            fully_verified_df=_fully_verified_df(VIN), key_out_aging_df=_empty_key_out_aging(),
        )
        self.assertEqual(len(tasks), 1)
        row = tasks.iloc[0]
        self.assertEqual(row["task"], "install_recovr_device")
        self.assertEqual(row["vin"], VIN)
        self.assertIn("Keyper confirms the key is In", row["reason"],
                       "the reason must explain WHY the task exists, not just what device is missing")

    def test_recovr_already_paired_generates_nothing(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_paired_df(VIN, STOCK),
            "TestStore", fully_verified_df=_fully_verified_df(VIN), key_out_aging_df=_empty_key_out_aging(),
        )
        self.assertTrue(tasks.empty)

    def test_wholesale_still_excludes_install_even_with_key_in(self):
        # Sprint 3.7's Wholesale/At Auction exclusion is unchanged by
        # this refinement -- it applies before the Keyper check, not
        # instead of it.
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(VIN, STOCK),
            "TestStore", rapidrecon_df=_rapidrecon_df(VIN, "WHOLESALE"),
            fully_verified_df=_fully_verified_df(VIN), key_out_aging_df=_empty_key_out_aging(),
        )
        self.assertTrue(tasks.empty)


class InvestigateKeyForRecovrTest(unittest.TestCase):
    """
    Generate when: otherwise RecovR-eligible, Keyper status Out, no
    RecovR device. Purpose: the install cannot be completed because the
    key is unavailable.
    """

    def test_keyper_out_generates_investigate_not_install(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(VIN, STOCK),
            "TestStore", fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=1),
        )
        self.assertEqual(len(tasks), 1)
        row = tasks.iloc[0]
        self.assertEqual(row["task"], "investigate_key_for_recovr")
        self.assertNotIn("install_recovr_device", tasks["task"].values,
                          "a vehicle must never get both an install and an investigate task for the same need")
        self.assertIn("checked Out", row["reason"])
        self.assertIn("cannot proceed until the key is available", row["reason"])

    def test_mutually_exclusive_with_install_for_the_same_vehicle(self):
        # Same vehicle cannot appear in Keyper's In population AND its
        # Out population at once (reconcile_keyper_tekion routes every
        # record to exactly one), but confirm the *task-generation*
        # side of that exclusivity holds too: Out wins if somehow both
        # were passed, never both tasks.
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(VIN, STOCK),
            "TestStore",
            fully_verified_df=_fully_verified_df(VIN),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=1),
        )
        task_types = set(tasks["task"].values)
        self.assertEqual(len(task_types), 1, "exactly one RecovR-related task type, never both")

    def test_wholesale_excludes_investigate_task_too(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(VIN, STOCK),
            "TestStore", rapidrecon_df=_rapidrecon_df(VIN, "AT AUCTION"),
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=1),
        )
        self.assertTrue(tasks.empty)

    def test_no_keyper_record_at_all_generates_nothing(self):
        # Absence of a Keyper record is not evidence the key is In --
        # "don't guess" applies here the same as everywhere else in
        # this module.
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(VIN, STOCK),
            "TestStore", fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_empty_key_out_aging(),
        )
        self.assertTrue(tasks.empty)

    def test_recovr_flip_to_paired_honors_the_investigate_task(self):
        # Sprint 3.8 extension to persist_recovr_observations: the
        # device getting installed resolves the real-world problem
        # investigate_key_for_recovr existed to flag, regardless of
        # what this pipeline believed about the key.
        conn = connect(":memory:")
        persist_tekion_observations(_tekion_df(VIN, STOCK), _EMPTY_SOLD, db_conn=conn)
        generate_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(VIN, STOCK),
            "TestStore", db_conn=conn,
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=1),
        )
        task = get_open_task(conn, VIN, "investigate_key_for_recovr")
        self.assertIsNotNone(task, "sanity check: the investigate task must exist before it can be honored")

        persist_recovr_observations(_recovr_paired_df(VIN, STOCK), db_conn=conn)

        discharged = get_task(conn, task["task_id"])
        self.assertEqual(discharged["commitment_standing"], "honored")


class InvestigateCheckedOutKeyTest(unittest.TestCase):
    """
    Generate independently of RecovR when: active Tekion inventory, not
    Wholesale/At Auction, Keyper status Out, checked out at least
    KEY_OUT_INVESTIGATE_THRESHOLD_DAYS.
    """

    def test_threshold_constant_matches_the_confirmed_dealership_value(self):
        # Guards against silent drift between this constant and the
        # dealership-confirmed decision it encodes (see rules/aging.py).
        self.assertEqual(KEY_OUT_INVESTIGATE_THRESHOLD_DAYS, 3)

    def test_at_threshold_generates_the_task(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD,
            pd.DataFrame(columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]),
            "TestStore",
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=KEY_OUT_INVESTIGATE_THRESHOLD_DAYS),
        )
        matches = tasks[tasks["task"] == "investigate_checked_out_key"]
        self.assertEqual(len(matches), 1)
        row = matches.iloc[0]
        self.assertEqual(row["vin"], VIN)
        self.assertIn(f"{KEY_OUT_INVESTIGATE_THRESHOLD_DAYS}-day", row["reason"])

    def test_below_threshold_generates_nothing(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD,
            pd.DataFrame(columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]),
            "TestStore",
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=KEY_OUT_INVESTIGATE_THRESHOLD_DAYS - 1),
        )
        self.assertTrue(tasks.empty, "one day short of the threshold must not generate the task yet")

    def test_independent_of_recovr_status_when_already_paired(self):
        # The key point of "independently of RecovR" -- a vehicle that
        # already HAS a RecovR device still needs its checked-out key
        # investigated.
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_paired_df(VIN, STOCK),
            "TestStore",
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=10),
        )
        matches = tasks[tasks["task"] == "investigate_checked_out_key"]
        self.assertEqual(len(matches), 1, "RecovR already being paired must not suppress this task")

    def test_independent_of_recovr_status_when_no_recovr_record_at_all(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD,
            pd.DataFrame(columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]),
            "TestStore",
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=10),
        )
        matches = tasks[tasks["task"] == "investigate_checked_out_key"]
        self.assertEqual(len(matches), 1)

    def test_wholesale_excludes_it(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD,
            pd.DataFrame(columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]),
            "TestStore", rapidrecon_df=_rapidrecon_df(VIN, "WHOLESALE"),
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=10),
        )
        self.assertTrue(tasks.empty)

    def test_sold_vehicle_excludes_it(self):
        sold_df = pd.DataFrame([{
            "Stock #": STOCK, "VIN #": VIN, "Status": "Sold",
            "Year Make Model": "2024 Test Sedan", "Sold Date": "Jul 20 2026",
        }])
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), sold_df, _EMPTY_MDD,
            pd.DataFrame(columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]),
            "TestStore",
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=10),
        )
        self.assertTrue(tasks.empty)


class KeyOutDaysNanRegressionTest(unittest.TestCase):
    """
    Regression coverage for a real production bug: reconcile_keyper_tekion
    builds key_out_aging_df via pd.DataFrame(key_out_aging), a list of
    per-Keyper-record dicts where days_out is a genuine Python None for
    a bad/missing checkout date. Mixing None with real int values in the
    same "days_out" column silently upcasts the whole column to
    float64 -- None becomes NaN, and every OTHER valid day count
    becomes a float too (4 -> 4.0). `is None`/`is not None` checks never
    catch NaN (NaN is not None, and any comparison against NaN is
    False), so a vehicle with an unknown checkout date used to still
    generate an investigate_checked_out_key task -- despite this
    module's own "don't guess" restraint saying it shouldn't -- with
    literal "nan days" in its reason text. Fixed in
    build_tracker_install_tasks by normalizing days_out back to a real
    Python None/int immediately when reading key_out_aging_df.
    """

    UNKNOWN_VIN = "1TESTVIN000000098"
    UNKNOWN_STOCK = "K30098"
    KNOWN_VIN = "1TESTVIN000000099"
    KNOWN_STOCK = "K30099"

    def _tasks(self):
        tekion_df = pd.concat(
            [_tekion_df(self.UNKNOWN_VIN, self.UNKNOWN_STOCK), _tekion_df(self.KNOWN_VIN, self.KNOWN_STOCK)],
            ignore_index=True,
        )
        key_out_aging_df = _multi_key_out_aging_df(
            (self.UNKNOWN_VIN, self.UNKNOWN_STOCK, None),
            (self.KNOWN_VIN, self.KNOWN_STOCK, KEY_OUT_INVESTIGATE_THRESHOLD_DAYS + 1),
        )
        self.assertEqual(
            key_out_aging_df["days_out"].dtype.kind, "f",
            "sanity check: this fixture must actually reproduce the float64/NaN upcast, "
            "or this test isn't exercising the bug at all",
        )
        return build_tracker_install_tasks(
            tekion_df, _EMPTY_SOLD, _EMPTY_MDD,
            pd.DataFrame(columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]),
            "TestStore",
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=key_out_aging_df,
        )

    def test_unknown_checkout_date_generates_no_task_rather_than_guessing(self):
        tasks = self._tasks()
        matches = tasks[tasks["vin"] == self.UNKNOWN_VIN]
        self.assertTrue(matches.empty, "an unconfirmed checkout date must not be treated as over-threshold")

    def test_known_checkout_date_generates_a_clean_task(self):
        tasks = self._tasks()
        matches = tasks[(tasks["vin"] == self.KNOWN_VIN) & (tasks["task"] == "investigate_checked_out_key")]
        self.assertEqual(len(matches), 1)
        reason = matches.iloc[0]["reason"]
        self.assertIn(f"{KEY_OUT_INVESTIGATE_THRESHOLD_DAYS + 1} days", reason)
        self.assertNotIn(".0", reason, "days_out must render as an int, not a float (4.0)")

    def test_no_reason_text_ever_contains_nan(self):
        tasks = self._tasks()
        for reason in tasks["reason"]:
            self.assertNotIn("nan", reason.lower())


class NoDuplicateTasksTest(unittest.TestCase):
    """Ensure no duplicate tasks are created for the same operational purpose, for every task type this refinement touches."""

    def _run_twice(self, recovr_df, key_out_aging_df, fully_verified_df=None):
        conn = connect(":memory:")
        persist_tekion_observations(_tekion_df(VIN, STOCK), _EMPTY_SOLD, db_conn=conn)
        for _ in range(2):
            generate_install_tasks(
                _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, recovr_df, "TestStore", db_conn=conn,
                fully_verified_df=fully_verified_df if fully_verified_df is not None else _fully_verified_df(),
                key_out_aging_df=key_out_aging_df,
            )
        (count,) = conn.execute("SELECT COUNT(*) FROM task WHERE vin = ?", (VIN,)).fetchone()
        return count

    def test_install_recovr_device_not_duplicated(self):
        count = self._run_twice(
            _recovr_not_paired_df(VIN, STOCK), _empty_key_out_aging(),
            fully_verified_df=_fully_verified_df(VIN),
        )
        self.assertEqual(count, 1)

    def test_investigate_key_for_recovr_not_duplicated(self):
        count = self._run_twice(
            _recovr_not_paired_df(VIN, STOCK), _key_out_aging_df(VIN, STOCK, days_out=1),
        )
        self.assertEqual(count, 1)

    def test_investigate_checked_out_key_not_duplicated(self):
        count = self._run_twice(
            pd.DataFrame(columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]),
            _key_out_aging_df(VIN, STOCK, days_out=10),
        )
        self.assertEqual(count, 1)

    def test_investigate_checked_out_key_coexists_with_investigate_key_for_recovr(self):
        # Same vehicle, same sync: key is Out (>= threshold) AND RecovR
        # is missing -- two distinct real problems, so two distinct open
        # tasks is correct, not a duplicate of "the same operational
        # purpose."
        conn = connect(":memory:")
        persist_tekion_observations(_tekion_df(VIN, STOCK), _EMPTY_SOLD, db_conn=conn)
        generate_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(VIN, STOCK),
            "TestStore", db_conn=conn,
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_key_out_aging_df(VIN, STOCK, days_out=10),
        )
        task_types = {
            row[0] for row in conn.execute("SELECT task_type FROM task WHERE vin = ?", (VIN,)).fetchall()
        }
        self.assertEqual(task_types, {"investigate_key_for_recovr", "investigate_checked_out_key"})


class KeyperMissingWarningTest(unittest.TestCase):
    """
    "If the Keyper report is missing during a sync, do not silently
    produce zero RecovR-related tasks" -- confirms the skip is
    surfaced, not just silent, and that MDD generation is unaffected.
    """

    def test_no_keyper_data_skips_recovr_related_generation_and_warns(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(VIN, STOCK),
            "TestStore",
            # fully_verified_df/key_out_aging_df both omitted -> None -> "Keyper wasn't part of this sync"
        )
        self.assertTrue(tasks.empty, "no RecovR-related task without any Keyper evidence at all")

    def test_mdd_generation_unaffected_by_missing_keyper(self):
        conn = connect(":memory:")
        persist_tekion_observations(_tekion_df(VIN, STOCK), _EMPTY_SOLD, db_conn=conn)
        mdd_df = pd.DataFrame([{
            "vin": VIN, "stock": STOCK, "year": 2024, "make": "Test", "model": "Sedan",
            "Dealership": "TestStore", "Geofence": "Not Paired",
        }])
        warnings = generate_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, mdd_df,
            pd.DataFrame(columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]),
            "TestStore", db_conn=conn,
        )
        task = get_open_task(conn, VIN, "install_mdd_beacon")
        self.assertIsNotNone(task, "MDD was never Keyper-gated -- must still generate")
        self.assertEqual(len(warnings), 1)

    def test_warning_message_names_all_three_recovr_related_task_types(self):
        warnings = generate_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD,
            pd.DataFrame(columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]),
            "TestStore", db_conn=connect(":memory:"),
        )
        self.assertEqual(len(warnings), 1)
        message = warnings[0]
        self.assertIn("Keyper", message)
        self.assertIn("Install RecovR", message)
        self.assertIn("Investigate Key for RecovR", message)
        self.assertIn("Investigate Checked-Out Key", message)

    def test_keyper_present_but_empty_is_not_a_warning(self):
        # The silence-vs-absence distinction this whole mechanism rests
        # on: Keyper ran and genuinely found nothing to report is a
        # legitimate outcome, not the same as Keyper being missing.
        warnings = generate_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD,
            pd.DataFrame(columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]),
            "TestStore", db_conn=connect(":memory:"),
            fully_verified_df=_fully_verified_df(),
            key_out_aging_df=_empty_key_out_aging(),
        )
        self.assertEqual(warnings, [])

    def test_no_op_db_conn_still_returns_empty_list_not_none(self):
        result = generate_install_tasks(
            _tekion_df(VIN, STOCK), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(VIN, STOCK),
            "TestStore", db_conn=None,
        )
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
