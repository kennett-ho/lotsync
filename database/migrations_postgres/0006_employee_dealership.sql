-- PostgreSQL dialect of database/migrations/0006_employee_dealership.sql
-- (Sprint 03). See that file for the full design reasoning (including
-- why FKs are NOT retrofitted onto the four earlier tables' employee/
-- dealership columns -- that decision is engine-independent and stands).
-- No dialect differences beyond none being needed: this file is
-- textually identical DDL; it exists so the postgres migration set is
-- complete and versioned 1:1 with the SQLite set.

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
