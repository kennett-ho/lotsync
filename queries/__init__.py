"""
Phase 2, Slice 7 -- dashboard-shaped read queries.

Deliberately separate from database/repository.py (persistence
primitives, one row/one write at a time) and sync/reconciler.py
(producing operational state from source observations). Every function
here is read-only: it aggregates rows that already exist and returns
plain, JSON-shaped data -- no new tables, no cached/stored columns,
nothing written back. See ARCHITECTURE.md and DECISION_FRAMEWORK.md's
"current state is always a derived read" principle, which explicitly
names dashboards as a future instance of this same shape -- this
module is that instance, not a new architectural pattern.
"""
