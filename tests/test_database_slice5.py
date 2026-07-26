"""
Phase 2, Sprint 4 (Slice 5) verification -- Task/TaskExecutionEvent
repository primitives (Milestone A) and their wiring into
sync/reconciler.py's actual task-generation and discharge logic
(Milestone B). See DATA_MODEL.md's Task/TaskExecutionEvent entries,
DECISION_FRAMEWORK.md's "Ontology, Architecture, Invariants, and
Reasoning Tools" section, and SPRINT_4_CHECKLIST.md.
"""

import os
import unittest

import pandas as pd

from lotsync.config.settings import load_settings
from lotsync.importers.tekion import load_tekion
from lotsync.importers.sold import load_tekion_sold
from lotsync.importers.mdd import load_mdd_not_paired
from lotsync.importers.recovr import load_recovr_full
from lotsync.database.repository import (
    connect, insert_task, get_open_task, get_task, honor_task, moot_task,
    cancel_task, escalate_task, insert_task_execution_event, assert_task_completed,
    upsert_vehicle,
)
from lotsync.sync.reconciler import (
    generate_install_tasks, persist_tekion_observations, persist_recovr_observations,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
CONFIG = os.path.join(FIXTURES, "test_config.xlsx")

# build_tracker_install_tasks' output against the standard fixture set,
# read directly (see the debug run in this milestone's own session, not
# recomputed from the function under test): MDD needs
# 1TESTVIN000000001 (K30001); RecovR needs 1TESTVIN000000002 (K30002)
# and 1TESTVIN000050001 (K50001, fragment-resolved).


class TaskCreationTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()

    def test_new_task_starts_outstanding_not_started(self):
        task_id = insert_task(self.conn, "VIN1", "install_recovr_device")
        task = get_task(self.conn, task_id)
        self.assertEqual(task["commitment_standing"], "outstanding")
        self.assertEqual(task["execution_status"], "not_started")

    def test_get_open_task_finds_outstanding_task(self):
        insert_task(self.conn, "VIN1", "install_recovr_device")
        task = get_open_task(self.conn, "VIN1", "install_recovr_device")
        self.assertIsNotNone(task)
        self.assertEqual(task["vin"], "VIN1")

    def test_get_open_task_returns_none_for_different_task_type(self):
        insert_task(self.conn, "VIN1", "install_recovr_device")
        self.assertIsNone(get_open_task(self.conn, "VIN1", "install_mdd_beacon"))

    def test_get_open_task_returns_none_once_discharged(self):
        task_id = insert_task(self.conn, "VIN1", "install_recovr_device")
        honor_task(self.conn, task_id)
        self.assertIsNone(get_open_task(self.conn, "VIN1", "install_recovr_device"))


class RealityDischargeTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()
        self.task_id = insert_task(self.conn, "VIN1", "install_recovr_device")

    def test_honor_task_sets_honored_and_completed_at_no_ratification(self):
        honor_task(self.conn, self.task_id)
        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "honored")
        self.assertIsNotNone(task["completed_at"])
        self.assertIsNone(task["ratified_by"], "Reality-discharge ratifies nothing -- the world confirmed it")
        self.assertIsNone(task["ratification_type"])

    def test_moot_task_sets_moot_no_ratification(self):
        moot_task(self.conn, self.task_id)
        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "moot")
        self.assertIsNone(task["ratified_by"])

    def test_discharging_an_already_terminal_task_is_a_no_op(self):
        honor_task(self.conn, self.task_id)
        (first_completed_at,) = (get_task(self.conn, self.task_id)["completed_at"],)
        moot_task(self.conn, self.task_id)  # attempting a second, conflicting discharge
        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "honored",
                          "history is immutable -- the first discharge stands, a second is a no-op")
        self.assertEqual(task["completed_at"], first_completed_at)


class IntentDischargeTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()
        self.task_id = insert_task(self.conn, "VIN1", "install_recovr_device")

    def test_cancel_task_requires_and_records_ratification(self):
        cancel_task(self.conn, self.task_id, ratified_by="emp123", ratification_type="human")
        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "cancelled")
        self.assertEqual(task["ratified_by"], "emp123")
        self.assertEqual(task["ratification_type"], "human")
        self.assertIsNotNone(task["completed_at"])

    def test_cancel_task_defaults_ratification_type_to_human(self):
        cancel_task(self.conn, self.task_id, ratified_by="emp123")
        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["ratification_type"], "human")

    def test_standing_policy_ratification_type_recorded(self):
        cancel_task(self.conn, self.task_id, ratified_by="standing_policy:wholesale_exclusion",
                    ratification_type="standing_policy")
        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["ratification_type"], "standing_policy")


class EscalationTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()
        self.parent_id = insert_task(self.conn, "VIN1", "install_recovr_device",
                                     dealership_id="Mark Kia", department="Inventory", priority="Medium")

    def test_escalate_task_supersedes_parent(self):
        escalate_task(self.conn, self.parent_id, "install_recovr_device_urgent",
                      ratified_by="emp123")
        parent = get_task(self.conn, self.parent_id)
        self.assertEqual(parent["commitment_standing"], "superseded")
        self.assertEqual(parent["ratified_by"], "emp123")

    def test_escalate_task_creates_child_pointing_back_at_parent(self):
        child_id = escalate_task(self.conn, self.parent_id, "install_recovr_device_urgent",
                                 ratified_by="emp123")
        child = get_task(self.conn, child_id)
        self.assertEqual(child["escalated_from_task_id"], self.parent_id)
        self.assertEqual(child["commitment_standing"], "outstanding",
                          "the new task starts outstanding on its own -- it does not inherit "
                          "the parent's disposition")
        self.assertEqual(child["execution_status"], "not_started")

    def test_escalate_task_inherits_vin_and_dealership_by_default(self):
        child_id = escalate_task(self.conn, self.parent_id, "install_recovr_device_urgent",
                                 ratified_by="emp123")
        child = get_task(self.conn, child_id)
        self.assertEqual(child["vin"], "VIN1")
        self.assertEqual(child["dealership_id"], "Mark Kia")

    def test_escalate_task_allows_overriding_priority_and_department(self):
        child_id = escalate_task(self.conn, self.parent_id, "install_recovr_device_urgent",
                                 ratified_by="emp123", priority="Critical", department="Lot Ops")
        child = get_task(self.conn, child_id)
        self.assertEqual(child["priority"], "Critical")
        self.assertEqual(child["department"], "Lot Ops")

    def test_escalate_unknown_task_raises(self):
        with self.assertRaises(ValueError):
            escalate_task(self.conn, 999999, "some_type", ratified_by="emp123")


class ExecutionLogTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()
        self.task_id = insert_task(self.conn, "VIN1", "install_recovr_device")

    def test_started_transition_sets_in_progress(self):
        insert_task_execution_event(self.conn, self.task_id, "started", actor_employee_id="emp1")
        self.assertEqual(get_task(self.conn, self.task_id)["execution_status"], "in_progress")

    def test_blocked_transition_sets_blocked(self):
        insert_task_execution_event(self.conn, self.task_id, "started")
        insert_task_execution_event(self.conn, self.task_id, "blocked", note="waiting on part")
        self.assertEqual(get_task(self.conn, self.task_id)["execution_status"], "blocked")

    def test_resumed_transition_sets_in_progress_again(self):
        insert_task_execution_event(self.conn, self.task_id, "started")
        insert_task_execution_event(self.conn, self.task_id, "blocked")
        insert_task_execution_event(self.conn, self.task_id, "resumed")
        self.assertEqual(get_task(self.conn, self.task_id)["execution_status"], "in_progress")

    def test_completed_transition_sets_completed(self):
        insert_task_execution_event(self.conn, self.task_id, "started")
        insert_task_execution_event(self.conn, self.task_id, "completed", actor_employee_id="emp1")
        self.assertEqual(get_task(self.conn, self.task_id)["execution_status"], "completed")

    def test_every_transition_is_preserved_not_collapsed(self):
        # The whole point of TaskExecutionEvent -- a mutable field would
        # have destroyed this sequence; the log must keep every step.
        for transition in ("started", "blocked", "resumed", "completed"):
            insert_task_execution_event(self.conn, self.task_id, transition)
        rows = self.conn.execute(
            "SELECT transition_type FROM task_execution_event WHERE task_id = ? ORDER BY task_execution_event_id",
            (self.task_id,),
        ).fetchall()
        self.assertEqual([r[0] for r in rows], ["started", "blocked", "resumed", "completed"])

    def test_execution_status_independent_of_commitment_standing(self):
        # A cancelled task can still have execution history -- the two
        # axes don't determine each other.
        insert_task_execution_event(self.conn, self.task_id, "started")
        cancel_task(self.conn, self.task_id, ratified_by="emp1")
        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "cancelled")
        self.assertEqual(task["execution_status"], "in_progress",
                          "execution_status must not be reset just because commitment_standing changed")


def _load_task_generation_inputs():
    settings = load_settings(CONFIG)
    tekion_df = load_tekion(set(), os.path.join(FIXTURES, "tekion_master.csv"))
    sold_df = load_tekion_sold(os.path.join(FIXTURES, "tekion_sold.csv"))
    mdd_df = load_mdd_not_paired(os.path.join(FIXTURES, "mdd_not_paired.csv"))
    recovr_df = load_recovr_full(os.path.join(FIXTURES, "recovr.csv"))
    return tekion_df, sold_df, mdd_df, recovr_df, settings["store_name"]


class TaskGenerationTest(unittest.TestCase):
    """
    Milestone B: generate_install_tasks reuses build_tracker_install_tasks
    directly -- see that function's docstring for why, over the
    alternative (and materially different) build_recovr_install_from_keyper
    methodology.
    """

    def setUp(self):
        self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df, self.store_name = \
            _load_task_generation_inputs()
        self.conn = connect(":memory:")
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)

    def test_generates_one_outstanding_task_per_candidate(self):
        generate_install_tasks(self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
                               self.store_name, db_conn=self.conn)
        rows = self.conn.execute(
            "SELECT vin, task_type, commitment_standing, execution_status FROM task ORDER BY vin"
        ).fetchall()
        self.assertEqual(set(rows), {
            ("1TESTVIN000000001", "install_mdd_beacon", "outstanding", "not_started"),
            ("1TESTVIN000000002", "install_recovr_device", "outstanding", "not_started"),
            ("1TESTVIN000050001", "install_recovr_device", "outstanding", "not_started"),
        })

    def test_rerun_does_not_create_duplicate_tasks(self):
        generate_install_tasks(self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
                               self.store_name, db_conn=self.conn)
        generate_install_tasks(self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
                               self.store_name, db_conn=self.conn)
        (count,) = self.conn.execute("SELECT COUNT(*) FROM task").fetchone()
        self.assertEqual(count, 3, "rerun must not create a second Task for an already-outstanding one")

    def test_no_op_when_db_conn_omitted(self):
        generate_install_tasks(self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
                               self.store_name, db_conn=None)


class RecovrHonorDischargeTest(unittest.TestCase):
    """Milestone B: RecovR's positive "paired" signal Reality-discharges an outstanding install_recovr_device Task."""

    def setUp(self):
        self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df, self.store_name = \
            _load_task_generation_inputs()
        self.conn = connect(":memory:")
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        generate_install_tasks(self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
                               self.store_name, db_conn=self.conn)
        self.task_id = get_open_task(self.conn, "1TESTVIN000000002", "install_recovr_device")["task_id"]

    def test_recovr_flip_to_paired_honors_the_task(self):
        flipped = self.recovr_df.copy(deep=True)
        target = flipped["VIN"].astype(str).str.strip() == "1TESTVIN000000002"
        flipped.loc[target, "Paired"] = "Yes"

        persist_recovr_observations(flipped, db_conn=self.conn)

        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "honored")
        self.assertIsNone(task["ratified_by"], "Reality-discharge ratifies nothing")

    def test_still_not_paired_leaves_task_outstanding(self):
        # Sanity check -- an unrelated diff-free rerun must not honor
        # the task on its own.
        persist_recovr_observations(self.recovr_df, db_conn=self.conn)
        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "outstanding")

    def test_unrelated_vin_paired_flip_does_not_honor_this_task(self):
        # 1TESTVIN000090001 (K90001) is already Paired=Yes in the base
        # fixture and belongs to a different VIN entirely -- confirms
        # the discharge is VIN-scoped, not global.
        persist_recovr_observations(self.recovr_df, db_conn=self.conn)
        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "outstanding")


class TekionSoldMootDischargeTest(unittest.TestCase):
    """Milestone B: a vehicle selling Reality-discharges (moots) any outstanding install-type Task for it."""

    def setUp(self):
        self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df, self.store_name = \
            _load_task_generation_inputs()
        self.conn = connect(":memory:")
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        generate_install_tasks(self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
                               self.store_name, db_conn=self.conn)

    def test_vehicle_selling_moots_its_outstanding_recovr_task(self):
        recovr_task_id = get_open_task(self.conn, "1TESTVIN000000002", "install_recovr_device")["task_id"]

        newly_sold = pd.DataFrame([{
            "Stock #": "K30002", "VIN #": "1TESTVIN000000002", "Status": "Sold",
            "Year Make Model": "2024 Test Sedan", "Sold Date": "Jul 20 2026",
        }])
        sold_with_new_row = pd.concat([self.sold_df, newly_sold], ignore_index=True)

        persist_tekion_observations(self.tekion_df, sold_with_new_row, db_conn=self.conn)

        task = get_task(self.conn, recovr_task_id)
        self.assertEqual(task["commitment_standing"], "moot")
        self.assertIsNone(task["ratified_by"], "Reality-discharge ratifies nothing")

    def test_vehicle_selling_moots_its_outstanding_mdd_task_too(self):
        mdd_task_id = get_open_task(self.conn, "1TESTVIN000000001", "install_mdd_beacon")["task_id"]

        newly_sold = pd.DataFrame([{
            "Stock #": "K30001", "VIN #": "1TESTVIN000000001", "Status": "Sold",
            "Year Make Model": "2024 Test Sedan", "Sold Date": "Jul 20 2026",
        }])
        sold_with_new_row = pd.concat([self.sold_df, newly_sold], ignore_index=True)

        persist_tekion_observations(self.tekion_df, sold_with_new_row, db_conn=self.conn)

        task = get_task(self.conn, mdd_task_id)
        self.assertEqual(task["commitment_standing"], "moot")

    def test_unrelated_vehicle_selling_does_not_moot_other_tasks(self):
        recovr_task_id = get_open_task(self.conn, "1TESTVIN000000002", "install_recovr_device")["task_id"]
        # K30005 (1TESTVIN000030005) is already sold in the base fixture
        # and has no outstanding install task -- rerunning with the
        # unchanged base sold_df must not disturb an unrelated task.
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        task = get_task(self.conn, recovr_task_id)
        self.assertEqual(task["commitment_standing"], "outstanding")


class CompletionAssertionCoexistenceTest(unittest.TestCase):
    """
    Milestone C: manual completion assertions (assert_task_completed)
    coexisting with automatic Reality-discharge (Milestone B's
    honor_task hook) as two independent mechanisms -- not one
    overriding the other. See the Milestone C breadcrumb discussion in
    conversation for the full reasoning; summarized in
    assert_task_completed's own docstring.
    """

    def setUp(self):
        self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df, self.store_name = \
            _load_task_generation_inputs()
        self.conn = connect(":memory:")
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        generate_install_tasks(self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
                               self.store_name, db_conn=self.conn)
        self.task_id = get_open_task(self.conn, "1TESTVIN000000002", "install_recovr_device")["task_id"]

    def test_assertion_alone_does_not_honor_the_task(self):
        assert_task_completed(self.conn, self.task_id, actor_employee_id="emp1")
        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "outstanding",
                          "a human's claim is provisional -- it must not override the source")
        self.assertEqual(task["execution_status"], "completed")

    def test_source_agreeing_afterward_honors_via_the_existing_reality_discharge_path(self):
        # The agreeing path needs no new code: the same honor_task hook
        # Milestone B already built fires exactly as it does without any
        # prior human assertion.
        assert_task_completed(self.conn, self.task_id, actor_employee_id="emp1")

        flipped = self.recovr_df.copy(deep=True)
        target = flipped["VIN"].astype(str).str.strip() == "1TESTVIN000000002"
        flipped.loc[target, "Paired"] = "Yes"
        persist_recovr_observations(flipped, db_conn=self.conn)

        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "honored")
        self.assertEqual(task["execution_status"], "completed",
                          "the human's own execution record is untouched by the later corroboration")

    def test_source_disagreeing_afterward_leaves_a_stable_surfaced_contradiction(self):
        # The disagreeing path: the Task must neither auto-honor (the
        # human's claim overriding the source) nor discard the
        # assertion. Both claims stay visible, unresolved, in their own
        # logs -- that state itself IS the surfaced contradiction.
        assert_task_completed(self.conn, self.task_id, actor_employee_id="emp1")

        # RecovR's next sync still shows not_paired -- unchanged input,
        # run twice to also confirm the disagreement doesn't drift or
        # escalate on repeated reruns.
        persist_recovr_observations(self.recovr_df, db_conn=self.conn)
        persist_recovr_observations(self.recovr_df, db_conn=self.conn)

        task = get_task(self.conn, self.task_id)
        self.assertEqual(task["commitment_standing"], "outstanding")
        self.assertEqual(task["execution_status"], "completed")

    def test_execution_log_preserves_the_completion_assertion_regardless_of_outcome(self):
        assert_task_completed(self.conn, self.task_id, actor_employee_id="emp1", note="installed on lift 3")
        persist_recovr_observations(self.recovr_df, db_conn=self.conn)  # still disagrees

        rows = self.conn.execute(
            "SELECT transition_type, actor_employee_id, note FROM task_execution_event WHERE task_id = ?",
            (self.task_id,),
        ).fetchall()
        self.assertEqual(rows, [("completed", "emp1", "installed on lift 3")],
                          "the human's claim is never edited or removed, regardless of what the source says later")


if __name__ == "__main__":
    unittest.main()
