"""
Phase 2, Slice 1 (see IMPLEMENTATION_PLAN.md) landed here: SQLite via
the stdlib sqlite3 module (no ORM, no SQLAlchemy dependency added --
still not warranted at this scale/concurrency, per ARCHITECTURE.md's
"Phase 2 database design" section), a numbered migration file per
schema change (migrations/), and a thin repository.py for
upsert/insert. Only Vehicle and Event exist so far, and only Keyper's
import path writes to them -- everything else about the CSV pipeline
is completely unchanged and untouched by this.

Slice 2 (full source coverage) and onward will keep landing here as
IMPLEMENTATION_PLAN.md's slices proceed. See that document, not this
docstring, for the up-to-date plan -- this note just marks that the
persistence-layer question ("how many sync cycles has this
discrepancy persisted") referenced throughout this project's earlier
history is now actively being acted on, not still deferred.
"""
