# Ingestion-Safety Fixtures (Sprint 10, Rail D)

The committed adversarial inputs behind
`tests/test_ingestion_validation.py` — one fixture per validation
class V1_1_RELEASE_READINESS §5.D requires proven. Column shapes match
the real importers exactly (same evidence base as
`tests/fixtures/synthetic/`, which remains the *well-formed* set these
files deliberately deviate from).

| Fixture | Deviation it proves |
|---|---|
| `empty.csv` | Zero-byte file → `EMPTY_FILE` |
| `tekion_headers_only.csv` | Headers, no data rows, authoritative snapshot → `NO_DATA_ROWS` (error) |
| `mdd_headers_only.csv` | Headers, no data rows, exception list → `NO_DATA_ROWS` (warning + acknowledgement) |
| `tekion_missing_status.csv` | Right report, required column absent → `MISSING_REQUIRED_COLUMN` |
| `keyper_variant_stand_in.csv` | Keyper-like columns that are NOT the Full Inventory contract → `REPORT_VARIANT_UNSUPPORTED` (see below) |
| `tekion_duplicate_vins.csv` | Same VIN under two stock numbers in a *current* snapshot → `DUPLICATE_VINS` |
| `tekion_malformed_vin.csv` | 16-character VIN → `MALFORMED_VINS` |
| `tekion_blank_vin.csv` | Blank VIN where rows originate Vehicle identity → `MISSING_VINS` (error) |
| `tekion_duplicate_header.csv` | Same header twice → `DUPLICATE_HEADER` |
| `unrecognized_report.csv` | No known contract's evidence → `UNRECOGNIZED_REPORT` |
| `ambiguous_tekion.csv` | Both "Stocked In Date" and "Sold Date" → `AMBIGUOUS_REPORT_TYPE` |
| `sold_exact_duplicate_rows.csv` | Exact duplicate rows in the sold report → `DUPLICATE_ROWS`; the same-VIN-different-stock pair is deliberately NOT flagged (legitimate sold history — see `rules/validation.py`'s conflict machinery) |

**`keyper_variant_stand_in.csv` is a synthetic stand-in, not a real
Keyper Event Report.** No sample of that report exists in this
repository, and its schema is deliberately NOT invented
(`sync/report_contracts.py`'s `KEYPER_KEY_EVENT` entry carries no
column facts). This fixture only proves the *boundary*: a Keyper-ish
file that is not the Full Key Inventory contract is rejected and can
never masquerade as the full snapshot. When vendor discovery
(V1_1_RELEASE_READINESS §6.2) supplies the real format, replace this
stand-in with a genuine sample and give `KEYPER_KEY_EVENT` its real
columns.

Byte-level cases with no meaningful text representation (fake .xlsx
magic bytes, BOM-prefixed header, undecodable binary, oversized file,
row-bomb) are generated at test runtime in temp directories — see
`FileSafetyTest` in the test module.
