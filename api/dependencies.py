"""
Phase 3, Sprint 2 -- the one new piece of wiring this sprint adds on
top of database/repository.py: a FastAPI dependency that hands each
request a connection from the existing connect(), and closes it when
the request finishes. Route handlers request one via
`Depends(get_db)`; tests override this dependency with an in-memory
connection the same way every existing test already uses
connect(":memory:") directly (see api/dependencies.py's use in
tests/test_api_routes.py).
"""

import sqlite3
from typing import Iterator

from lotsync.database.repository import connect


def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
