-- Phase 3, Sprint 1 -- Employee + Dealership.
--
-- Both were fully specified in DATA_MODEL.md since the Phase 2
-- "frontend discovery" review (Employee: "identified as load-bearing,
-- not optional... nearly every Event and Task has an attributed
-- actor"; Dealership: "current concern, modeled -- see models/dealership.py")
-- but, per FRONTEND_BACKEND_RECONCILIATION.md's finding, neither ever
-- got a migration. Every column across four existing tables that
-- should reference one of these has been sitting as unconstrained free
-- text since Slice 1, waiting for exactly this migration:
-- vehicle.current_dealership_id, task.dealership_id,
-- task.assigned_employee_id, task.ratified_by, event.actor_employee_id,
-- event.dealership_id, sync_run.dealership_id.
--
-- Column shapes match DATA_MODEL.md's Employee and Dealership entries
-- exactly. name is NOT NULL on both -- the one piece of validation
-- genuinely implied by "this is a real employee/dealership record" that
-- DATA_MODEL.md's field tables don't already spell out as a SQL
-- constraint; every other field is exactly as nullable as DATA_MODEL.md
-- describes it.
--
-- Dealership is created first, Employee second, so Employee's
-- dealership_id can carry a real FOREIGN KEY declared at creation time
-- -- safe for the same reason escalated_from_task_id's self-referential
-- FK was safe in migrations/0004_task.sql: the referenced table already
-- exists the moment this column is declared, so there is no window
-- where the constraint could reject a legitimately-already-written row.
-- This does not contradict models/employee.py's "not a hard constraint"
-- docstring note -- that note is about real-world staffing behavior
-- (staff legitimately work across sister-store lines), not about
-- whether a populated dealership_id must reference a real Dealership
-- row. Requiring the latter is ordinary referential integrity, not a
-- business-rule overreach.
--
-- Deliberately NOT done here: retrofitting FOREIGN KEY constraints onto
-- the four already-existing tables' employee/dealership-shaped columns
-- listed above. SQLite has no ALTER TABLE ... ADD CONSTRAINT -- doing
-- this properly requires recreating each of those tables (rename,
-- create new with the FK, copy rows, drop old, rename back), which is
-- real migration risk against live, tested tables for a guarantee this
-- project has already chosen to accept getting a different way once
-- before: migrations/0004_task.sql left event.sync_run_id unconstrained
-- even after sync_run came to exist, for exactly this reason, and
-- proved the "no orphans" guarantee at the application/test level
-- instead (see tests/test_database_slice4.py) rather than via schema.
-- The same choice is made here, for the same reason, across all seven
-- listed columns. An application-level orphan-check test is left for
-- whichever future slice first actually starts writing real employee_id/
-- dealership_id values into those columns (nothing does yet -- see this
-- sprint's review) -- writing that test now, against columns nothing
-- populates, would be testing a behavior that doesn't exist yet.

CREATE TABLE IF NOT EXISTS dealership (
    dealership_id  TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    brand          TEXT
);

CREATE TABLE IF NOT EXISTS employee (
    employee_id    TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    role           TEXT,
    department     TEXT,
    dealership_id  TEXT,
    status         TEXT,
    FOREIGN KEY (dealership_id) REFERENCES dealership (dealership_id)
);

CREATE INDEX IF NOT EXISTS idx_employee_dealership_id ON employee (dealership_id);
