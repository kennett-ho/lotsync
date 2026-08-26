"""
D4 bounded retention for raw `/run` upload batches (owner-ratified
2026-08-21; policy and design record: DATA_RETENTION.md section 3).

Raw vendor uploads are temporary operational evidence, not permanent
archives. Every `POST /inventory-sync/run` stages its files in a
timestamped batch directory under the uploads root; before this
module existed, nothing ever deleted them. The ratified windows:

- accepted (validated + successfully executed) batches: 7 days;
- rejected / unacknowledged-warning batches: 30 days;
- unmarked directories (pre-feature legacy, or a crash before the
  marker was written -- including the /run 500 path, which
  deliberately writes no marker): the LONGER 30-day window,
  conservatively;
- orphaned `validate-*` temp directories (normally deleted before
  the response returns; an orphan means the process died mid
  request): 24 hours.

Mechanism: at request end the router records the batch outcome in a
small `outcome.json` marker; an opportunistic sweep at the start of
`/run` and `/validate` deletes batch directories older than their
outcome's window. There is no scheduler on the current hosting tier,
and files only accumulate when these endpoints are used, so sweeping
there is sufficient by construction.

Safety properties (each pinned in tests/test_upload_retention.py):

- The in-flight batch is never touched: the sweep runs BEFORE the
  request creates its own batch directory, and any concurrent
  request's directory is seconds old -- far inside every window.
- Deletion happens only under the uploads root, and only for entries
  the sweep positively recognizes: directories whose name parses as
  a batch timestamp, or `validate-*` temp directories. Anything else
  (stray files, unrecognized names) is never deleted.
- Age comes from the batch directory's own name -- the same local
  clock that named it -- never from the marker, so a corrupt or
  hand-edited marker can shorten nothing. An unreadable or
  unrecognized marker falls back to the conservative 30-day window.
- `UPLOAD_RETENTION_SWEEP=disabled` is the operator kill-switch for
  investigations. Any value other than unset/"enabled" also
  disables: deletion is irreversible and a skipped sweep is always
  recoverable, so an unrecognized value fails toward keeping data.
- One structured INFO record per sweep -- counts and batch
  timestamps only, never client filenames (batch directory names are
  server-generated timestamps), never file contents.
- Neither the marker write nor the sweep ever raises into the
  request path; a failed marker simply leaves the batch unmarked
  (conservative window), a failed deletion is retried by the next
  sweep.

The one-time prune of the legacy PRODUCTION backlog remains an
explicit operator step at the production release gate, never a merge
side effect: production deploys only at the release train, and its
deploy notes must either set the kill-switch until the operator
performs the approved prune, or record explicit operator approval
that the first post-deploy sweep performs it (DATA_RETENTION.md
section 3).
"""

import datetime
import json
import logging
import os
import shutil
import time

from lotsync.api import observability

OUTCOME_MARKER = "outcome.json"

OUTCOME_ACCEPTED = "accepted"
OUTCOME_REJECTED = "rejected"
OUTCOME_WARNINGS_UNACKNOWLEDGED = "warnings_unacknowledged"
_KNOWN_OUTCOMES = {OUTCOME_ACCEPTED, OUTCOME_REJECTED, OUTCOME_WARNINGS_UNACKNOWLEDGED}

ACCEPTED_RETENTION = datetime.timedelta(days=7)
REJECTED_RETENTION = datetime.timedelta(days=30)
VALIDATE_ORPHAN_AGE = datetime.timedelta(hours=24)

# The exact format inventory_sync.py uses to name batch directories
# (datetime.now() -- naive local time; ages are computed against the
# same clock, and a DST hour is immaterial against 7/30-day windows).
_BATCH_NAME_FORMAT = "%Y%m%dT%H%M%S%f"


def sweep_enabled() -> bool:
    mode = os.environ.get("UPLOAD_RETENTION_SWEEP", "enabled").strip().lower()
    return mode in ("", "enabled")


def record_outcome(batch_dir: str, outcome: str) -> None:
    """Writes the batch's outcome.json marker. Never raises into the
    request path: a batch whose marker cannot be written stays
    unmarked and ages under the conservative 30-day window instead.
    `recorded_at` is informational (forensics) -- the sweep's age
    basis is always the directory name."""
    try:
        marker = {
            "outcome": outcome,
            "recorded_at": datetime.datetime.now().astimezone().isoformat(),
        }
        with open(os.path.join(batch_dir, OUTCOME_MARKER), "w", encoding="utf-8") as f:
            json.dump(marker, f)
    except OSError:
        observability.log_event(
            logging.WARNING, "upload_outcome_marker_failed",
            batch=os.path.basename(batch_dir), outcome=outcome,
        )


def _read_outcome(batch_dir: str):
    """The marker's outcome, or None for missing/unreadable/unknown --
    every failure mode maps to the conservative window."""
    try:
        with open(os.path.join(batch_dir, OUTCOME_MARKER), "r", encoding="utf-8") as f:
            outcome = json.load(f).get("outcome")
    except (OSError, ValueError):
        return None
    return outcome if outcome in _KNOWN_OUTCOMES else None


def sweep(uploads_dir: str) -> None:
    """The opportunistic retention sweep. Call at the start of /run
    and /validate, BEFORE the request creates its own directory.
    Never raises."""
    try:
        _sweep(uploads_dir)
    except Exception:
        # A sweep failure must never block the operator's actual
        # work; the next sweep retries. log_event itself never raises.
        observability.log_event(logging.WARNING, "upload_retention_sweep_failed")


def _sweep(uploads_dir: str) -> None:
    if not sweep_enabled() or not os.path.isdir(uploads_dir):
        return

    now = datetime.datetime.now()
    scanned = kept = delete_errors = 0
    deleted_batches = []
    deleted_validate_orphans = 0

    for entry in sorted(os.listdir(uploads_dir)):
        path = os.path.join(uploads_dir, entry)
        if not os.path.isdir(path):
            continue  # never a stray file
        scanned += 1

        if entry.startswith("validate-"):
            # mkdtemp names carry no timestamp; mtime is the age basis.
            try:
                age_seconds = time.time() - os.path.getmtime(path)
            except OSError:
                continue
            if age_seconds <= VALIDATE_ORPHAN_AGE.total_seconds():
                kept += 1
                continue
            if _remove(path):
                deleted_validate_orphans += 1
            else:
                delete_errors += 1
            continue

        try:
            batch_time = datetime.datetime.strptime(entry, _BATCH_NAME_FORMAT)
        except ValueError:
            kept += 1
            continue  # not a batch directory the sweep recognizes -- never deleted

        outcome = _read_outcome(path)
        window = ACCEPTED_RETENTION if outcome == OUTCOME_ACCEPTED else REJECTED_RETENTION
        if now - batch_time <= window:
            kept += 1
            continue
        if _remove(path):
            deleted_batches.append(entry)
        else:
            delete_errors += 1

    observability.log_event(
        logging.INFO, "upload_retention_sweep",
        scanned=scanned, kept=kept,
        deleted_batches=deleted_batches,
        deleted_validate_orphans=deleted_validate_orphans,
        delete_errors=delete_errors,
    )


def _remove(path: str) -> bool:
    try:
        shutil.rmtree(path)
        return True
    except OSError:
        return False
