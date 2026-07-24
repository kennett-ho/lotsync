# Running the tests

No external dependencies — everything here uses Python's built-in
`unittest`, on purpose (see ARCHITECTURE.md on minimal dependencies).

```
cd lotsync
PYTHONPATH=.. python3 -m unittest discover -s tests -p "test_*.py" -v
```

(Adjust `PYTHONPATH` to wherever the `lotsync/` package's parent
directory lives.)

## What's covered

- `test_normalizer.py`, `test_inventory_rules.py`, `test_state_engine.py`
  — fast unit tests for pure functions, no fixtures needed.
- `test_regression.py` — full-pipeline integration test against the
  synthetic fixtures in `fixtures/synthetic/`. This is what replaced
  the manual "run old script, run new package, diff every CSV" check
  performed during the Phase 1 module split. **Run this after any
  change to `sync/` or `rules/` before considering the change done.**
- `test_database_slice1.py` — Phase 2 Slice 1 (see
  `IMPLEMENTATION_PLAN.md`): confirms passing a database connection
  into `reconcile_keyper_tekion()` doesn't change any existing report
  output, and that the Vehicle/Event rows it writes match exactly the
  Keyper records that resolve to a real VIN -- no more, no fewer. Run
  this after any change to the database write path, the same way
  `test_regression.py` gates changes to `sync/`/`rules/`.

## What this does NOT cover

This fixture set is small and hand-crafted to pin down known edge
cases — it's not a substitute for occasionally running the full
pipeline against real, current dealership exports and spot-checking
the output. Real data has a way of finding cases a hand-built fixture
set didn't anticipate (see the discovery history in ARCHITECTURE.md
and PRODUCT.md's development record — nearly every business rule in
this codebase came from a real-data surprise, not from advance
design). Treat this suite as a safety net for regressions in behavior
already understood, not as proof the system handles everything.
