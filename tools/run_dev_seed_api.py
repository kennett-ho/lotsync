"""
Run the LotSync/DealerDOH API locally against the disposable synthetic
dev-seed database (see seed_dev.py) -- the closest local equivalent of
the DealerDOH development deployment. Sprint 02 tooling.

    PYTHONPATH=.. python tools/run_dev_seed_api.py

Sets development env vars only where the caller hasn't already:
ENVIRONMENT=development (reported by /health) and LOTSYNC_DB_PATH
pointed at seed_dev.py's default database. Run seed_dev.py first if
that file doesn't exist yet.
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "LOTSYNC_DB_PATH", os.path.join(_REPO_ROOT, "data", "dealerdoh-dev-seed.db")
)

# Same `from lotsync...` import convention as everywhere else -- the
# checkout directory is named `lotsync`, so its parent on sys.path
# resolves it (see README.md / render.yaml / seed_dev.py).
sys.path.insert(0, os.path.dirname(_REPO_ROOT))

import uvicorn  # noqa: E402  (env must be final before app import chain)

if __name__ == "__main__":
    uvicorn.run("lotsync.api.app:app", host="127.0.0.1", port=8000)
