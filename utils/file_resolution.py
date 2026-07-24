"""
Real dealership exports don't have stable filenames -- this same
project has seen "Tekion_Sold.csv" and, in a later upload, the exact
same report type as "1784737639423_Tekion_Sold_Report.csv" (a
timestamp-prefixed filename, likely from whatever export tool the
dealership used that day). Hardcoding an exact filename in each
importer would break on every naming variation. This resolves a file
by a case-insensitive substring match against the uploads directory
instead, which survives prefixes/suffixes changing as long as the
core report name doesn't.
"""

import glob
import os

# Default location for dealership export files, relative to the repo
# root -- overridable via LOTSYNC_UPLOADS_DIR for a different machine
# or folder layout. (Previously hardcoded to /mnt/user-data/uploads,
# a path specific to this project's original development sandbox, not
# meaningful on a real deployment machine.)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.environ.get("LOTSYNC_UPLOADS_DIR", os.path.join(_REPO_ROOT, "data", "uploads"))


def find_upload(pattern=None, uploads_dir: str = UPLOADS_DIR, exclude: str = None,
                 require_all: list = None) -> str:
    """
    Returns the path to the single file in uploads_dir matching the
    given criteria (case-insensitive):
      - `pattern`: a string, or a list of alternatives (ANY match)
      - `require_all`: a list where EVERY substring must be present
        (use this instead of a fixed multi-word pattern like "Kia
        RecovR" -- real filenames are underscore-separated, e.g.
        "RecovR_Kia_Report", so a space-joined pattern silently never
        matches)
      - `exclude`: files containing this substring are filtered out
        first, before any include check

    At least one of `pattern` / `require_all` must be given. Raises
    FileNotFoundError if none match, or ValueError if more than one
    does -- ambiguity here should surface loudly, not silently pick one.
    """
    patterns = None
    if pattern is not None:
        patterns = [pattern] if isinstance(pattern, str) else list(pattern)

    candidates = []
    for f in glob.glob(os.path.join(uploads_dir, "*")):
        name = os.path.basename(f).lower()
        if exclude is not None and exclude.lower() in name:
            continue
        if require_all is not None and not all(p.lower() in name for p in require_all):
            continue
        if patterns is not None and not any(p.lower() in name for p in patterns):
            continue
        candidates.append(f)

    if not candidates:
        raise FileNotFoundError(
            f"No file matching pattern={patterns} require_all={require_all}"
            f"{f' (excluding {exclude!r})' if exclude else ''} found in {uploads_dir}"
        )
    if len(candidates) > 1:
        raise ValueError(
            f"Multiple files matching pattern={patterns} require_all={require_all} "
            f"found in {uploads_dir}: {candidates} -- criteria needs to be more specific."
        )
    return candidates[0]
