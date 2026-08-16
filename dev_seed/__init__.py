"""
dev_seed -- the DealerDOH DEV standing QA dealership (Sprint 04).

A deliberately constructed synthetic dealership whose vehicles exercise
the product's important operational rules, with expected outcomes
enforced automatically on both persistence engines. Three modules, one
contract:

- scenarios.py  -- the scenario roster and the deterministic source
                   files it generates (the WHAT). Every row traces to
                   SYNTHETIC_QA_MATRIX.md by scenario ID.
- seeder.py     -- replays the scenarios through the real pipeline
                   (sync/pipeline.run_inventory_sync -- the HOW).
                   Nothing writes to the database directly.
- expected.py   -- the machine-readable expected outcomes (the PROOF),
                   asserted by tests/test_qa_dataset.py on SQLite and
                   PostgreSQL alike.

SYNTHETIC_QA_MATRIX.md (repo root) is the human-readable source of
truth this package implements; if the two ever disagree, the matrix
wins and this package has a bug.
"""
