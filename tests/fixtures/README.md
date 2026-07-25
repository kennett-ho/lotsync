# Test Fixtures

Synthetic data in `synthetic/` — small, hand-crafted, and NOT real
dealership data. Every row exists to pin down one specific behavior
found and fixed during this project's development. If you're adding a
new business rule, the pattern is: add a row here for the new case,
then a corresponding assertion in `tests/test_regression.py`.

Fixed sync date used throughout: **2026-07-21**.

## keyper.csv

| identifier | scenario |
|---|---|
| K30001 | In, matches Tekion by stock number → fully_verified |
| K30002 | Out, 0 days out → "Should be here" |
| K30003 | Out, ~31 days out → "Likely Sold, Verify to Remove from OMS" |
| 099999 | In, matches Tekion via last-6-VIN (numeric identifier, no letter prefix) |
| K30099 | In, tagged `System=Mitsu-SVC` but must still resolve — regression guard for the "Keyper System field isn't a reliable store indicator" bug |
| K30005 | In, sold — key never removed from Keyper |
| K30006 | In, genuinely unmatched (not in Tekion, not sold) → pending_dms_entry |
| K30007 | Out, genuinely unmatched → out_and_unmatched_no_tekion_record |
| 784 | 3-digit numeric → tekion_auto_generated_stock_number exception |
| #ODD1 | Doesn't fit any known format → unrecognized exception |
| 555555 | 6-digit numeric matching TWO Tekion VINs' last-6 → ambiguous_last6_vin_multiple_matches |
| GOLF CART | Non-vehicle facility key → excluded entirely |
| ZZ00001 | Prefix never appears in the Tekion fixture → out_of_scope_store, excluded entirely |

## tekion_master.csv

Includes match targets for the Keyper rows above, plus unmatched
vehicles for the Incoming/Missing report:

| stock | scenario |
|---|---|
| K50001 | Bare K+digits, stocked in ~2 days ago → New Car, "Awaiting Transport Dropoff" |
| K50002 | Bare K+digits, stocked in ~11 days ago → New Car, "Investigate" |
| K50003DM | Damaged/in-repair suffix → no priority bucket applied |
| K50004A | Trade suffix, ~1 day → Trade/Other, "Within Normal Turnaround" |
| K50005SL | Trade suffix, ~11 days → Trade/Other, "Overdue" |
| K50006A | VIN is on the Excluded VINs list in test_config.xlsx → must not appear in the Incoming/Missing report at all |
| K60001 / K60002 | Both VINs end in 555555 → the ambiguous-match pair; both should remain unmatched (visible here), since Keyper's 555555 couldn't confidently resolve to either one |
| K70001 | Also appears in tekion_sold.csv → sold_but_still_stocked_in conflict |

## tekion_sold.csv

| stock | scenario |
|---|---|
| K30005 | Matches Keyper's K30005 |
| K70001 | Same VIN as the Master List row above → sync conflict |
| K80001 / K80002 | Same VIN, two different stock numbers → duplicate_sold_vin |
| K90001 | Still shows Paired=Yes in recovr.csv → needs_removal via RecovR, not Keyper |

K80001 alone (ignoring the duplicate) is also used as the
"fully clean, sale_complete" case — not in Keyper, not in RecovR.

## mdd_not_paired.csv / recovr.csv

K30001 (active) and K30005 (sold) both appear in the MDD "not paired"
list — the sold one must be excluded from the resulting task list.
RecovR includes a short (non-17-character) VIN fragment (`050001`)
that should resolve via last-6 matching to K50001's full VIN.

## rapidrecon.csv

Added in Phase 2 Sprint 2 (Slice 2) — not exercised by
`test_regression.py`, which predates any RapidRecon assertions; used
only by `test_database_slice2.py`'s `persist_rapidrecon_observations`
tests.

| VIN | scenario |
|---|---|
| 1TESTVIN000000001 | Same VIN as Keyper's K30001 → already a known Vehicle, gets a `rapidrecon_observed` Event |
| 1TESTVIN999999999 | Not a VIN known from any other source → must be skipped, not turned into a new Vehicle row |
