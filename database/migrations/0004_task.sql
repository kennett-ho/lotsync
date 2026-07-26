-- Phase 2, Sprint 4 -- Task + TaskExecutionEvent.
--
-- See DATA_MODEL.md's Task and TaskExecutionEvent entries for the full
-- reasoning (Pre-Sprint 4 design review, see SPRINT_4_DESIGN_REVIEW_SUMMARY.md
-- and DECISION_FRAMEWORK.md's "Ontology, Architecture, Invariants, and
-- Reasoning Tools" section). Summary: a Task is an operational
-- commitment, not a directive and not a Recommendation with a richer
-- status. It discharges via one of two independent mechanisms --
-- Reality (honored/moot) or Intent (cancelled/superseded) -- which the
-- original three-value status (not_started/in_progress/complete) could
-- not honestly represent.
--
-- commitment_standing vs execution_status: independent axes, the same
-- cache-over-log pattern vehicle's status fields already use. A Task
-- can be outstanding with execution blocked, or already cancelled while
-- execution was mid-flight. execution_status is a plain, application-
-- managed cache column here -- NOT a database trigger. Every other
-- cache column in this schema (vehicle.tekion_status, keyper_status,
-- mdd_status, recovr_status) is already updated by explicit application
-- logic, not a trigger; introducing a trigger here would be a new,
-- inconsistent pattern this migration deliberately avoids. The actual
-- logic that derives execution_status from task_execution_event is
-- Sprint 4's backend implementation work, not this migration's concern
-- -- this table only declares the column exists, the same way
-- migrations/0001_initial.sql declared vehicle's status columns before
-- any code populated them.
--
-- No FOREIGN KEY on dealership_id (no Dealership table yet, same as
-- vehicle.current_dealership_id and sync_run.dealership_id) or on
-- assigned_employee_id/ratified_by (no Employee table yet, same as
-- event.actor_employee_id).
--
-- escalated_from_task_id IS given a real FOREIGN KEY, self-referential
-- -- unlike pending_identity.resolved_vin (Slice 2) or event.sync_run_id
-- (Sprint 3), an escalated-from parent Task must already exist at the
-- moment a child Task references it (escalation always follows an
-- already-created parent), so the constraint is safe to declare now
-- rather than deferred.

CREATE TABLE IF NOT EXISTS task (
    task_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    vin                     TEXT NOT NULL,
    dealership_id           TEXT,
    task_type               TEXT NOT NULL,
    department              TEXT,
    priority                TEXT,
    commitment_standing     TEXT NOT NULL DEFAULT 'outstanding',
    execution_status        TEXT NOT NULL DEFAULT 'not_started',
    assigned_employee_id    TEXT,
    ratified_by             TEXT,
    ratification_type       TEXT,
    escalated_from_task_id  INTEGER,
    reason                  TEXT,
    created_at              TEXT NOT NULL,
    completed_at            TEXT,
    FOREIGN KEY (vin) REFERENCES vehicle (vin),
    FOREIGN KEY (escalated_from_task_id) REFERENCES task (task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_vin ON task (vin);
CREATE INDEX IF NOT EXISTS idx_task_commitment_standing ON task (commitment_standing);
CREATE INDEX IF NOT EXISTS idx_task_escalated_from_task_id ON task (escalated_from_task_id);

CREATE TABLE IF NOT EXISTS task_execution_event (
    task_execution_event_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id                  INTEGER NOT NULL,
    transition_type          TEXT NOT NULL,
    actor_employee_id        TEXT,
    note                     TEXT,
    observed_at              TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES task (task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_execution_event_task_id ON task_execution_event (task_id);
