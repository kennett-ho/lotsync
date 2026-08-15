"""
Sprint 03 (DealerDOH) -- database engine selection and the PostgreSQL
connection layer.

This module exists so database/repository.py's public surface -- and
therefore every caller in the codebase, including all ~390 tests --
keeps its exact sqlite3-style contract (`conn.execute(sql_with_?,
params)`, tuple rows, `commit()`/`rollback()`/`close()`) while the
actual engine underneath becomes configurable:

    DATABASE_ENGINE=sqlite     (default -- production's engine, unchanged)
    DATABASE_ENGINE=postgres   (DealerDOH DEV -- Supabase PostgreSQL)

Explicit configuration, never inference: production keeps running
SQLite by simply never setting DATABASE_ENGINE, and nothing in this
module activates unless it is set to "postgres" deliberately.

PostgreSQL specifics live here and only here:

- `?` placeholder translation to psycopg's `%s` (literal-aware -- see
  translate_qmark_sql; NOT a blind str.replace).
- Connection acquisition: a small process-wide psycopg connection pool
  for the runtime database (DATABASE_URL -- for DealerDOH DEV this is
  the Supabase SESSION pooler DSN, since direct Supabase connections
  are IPv6-only from Render; see DEV_ENVIRONMENT.md), or a dedicated
  connection with a private, disposable schema for tests'
  connect(":memory:") convention -- SQLite gives every ":memory:"
  connection its own isolated database, and a fresh per-connection
  schema (dropped on close) is the exact PostgreSQL equivalent of that
  contract.
- prepare_threshold=None on every connection: psycopg's automatic
  server-side prepared statements break behind transaction-mode
  poolers (statement state doesn't follow the client between backend
  connections). Session mode wouldn't strictly need this, but
  disabling it makes the layer safe under either pooler mode for the
  cost of a few microseconds per query at dev scale.

Secrets: DATABASE_URL is read from the environment at connect time and
never logged, echoed, or stored anywhere by this module.
"""

import os
import uuid

# psycopg is imported lazily (inside functions) so that SQLite-only
# deployments -- production today -- never require the dependency to
# be importable at module-import time.

_VALID_ENGINES = ("sqlite", "postgres")

# Process-wide pool for the runtime DSN (not for ":memory:" test
# connections, which are dedicated and schema-isolated). Created
# lazily on first postgres runtime connect.
_pool = None

# DSNs whose runtime database this process has already verified as
# fully migrated -- lets pooled per-request connections skip the
# migration check after the first one (see repository.connect()).
_migrated_dsns = set()


def get_engine() -> str:
    """The configured database engine: 'sqlite' unless DATABASE_ENGINE=postgres."""
    engine = os.environ.get("DATABASE_ENGINE", "sqlite").strip().lower()
    if engine not in _VALID_ENGINES:
        raise ValueError(
            f"DATABASE_ENGINE={engine!r} is not supported -- "
            f"expected one of {_VALID_ENGINES}"
        )
    return engine


def _require_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError(
            "DATABASE_ENGINE=postgres but DATABASE_URL is not set. "
            "Set DATABASE_URL to the PostgreSQL DSN (for DealerDOH DEV: "
            "the Supabase session-pooler connection string)."
        )
    return dsn


def translate_qmark_sql(sql: str) -> str:
    """
    Translates sqlite3-style `?` placeholders to psycopg-style `%s`,
    and escapes literal `%` to `%%`, WITHOUT touching the contents of
    single-quoted string literals or double-quoted identifiers. This
    is a character-walk with explicit quote-state tracking, not a
    global replace -- a `?` or `%` inside a SQL string literal is data
    and must survive unchanged.
    """
    out = []
    i = 0
    n = len(sql)
    in_single = False
    in_double = False
    while i < n:
        ch = sql[i]
        if ch == "%":
            # psycopg's placeholder parser scans the WHOLE query text
            # without understanding SQL quoting, so a literal % must be
            # escaped to %% in every context, including inside quoted
            # literals/identifiers.
            out.append("%%")
        elif in_single:
            out.append(ch)
            if ch == "'":
                if i + 1 < n and sql[i + 1] == "'":  # escaped '' stays inside the literal
                    out.append("'")
                    i += 1
                else:
                    in_single = False
        elif in_double:
            out.append(ch)
            if ch == '"':
                in_double = False
        elif ch == "'":
            in_single = True
            out.append(ch)
        elif ch == '"':
            in_double = True
            out.append(ch)
        elif ch == "?":
            out.append("%s")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


class PostgresConnection:
    """
    Duck-types the slice of sqlite3.Connection this codebase actually
    uses: execute / executemany / executescript / commit / rollback /
    close. Rows come back as plain tuples (psycopg's default), same as
    sqlite3's -- callers cannot tell the difference, which is the
    point.
    """

    def __init__(self, pg_conn, *, pool=None, test_schema: str = None):
        self._conn = pg_conn
        self._pool = pool          # set for pooled runtime connections
        self._schema = test_schema  # set for ":memory:"-equivalent test connections
        self._closed = False

    # -- the sqlite3-shaped surface -------------------------------------

    def execute(self, sql: str, params=None):
        if params is None:
            return self._conn.execute(translate_qmark_sql(sql))
        return self._conn.execute(translate_qmark_sql(sql), params)

    def executemany(self, sql: str, seq_of_params):
        cur = self._conn.cursor()
        cur.executemany(translate_qmark_sql(sql), seq_of_params)
        return cur

    def executescript(self, script: str):
        # No parameters in migration scripts, so no translation is
        # needed or wanted (comments in .sql files may legitimately
        # contain '?'). psycopg executes a multi-statement string in
        # one round trip when no parameters are passed.
        return self._conn.execute(script)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._schema is not None:
            # Mirror sqlite3's ":memory:" lifecycle: the database
            # vanishes when the connection closes.
            try:
                self._conn.rollback()
                self._conn.execute(f'DROP SCHEMA IF EXISTS "{self._schema}" CASCADE')
                self._conn.commit()
            finally:
                self._conn.close()
        elif self._pool is not None:
            # Pooled runtime connection: hand it back, don't destroy it.
            self._conn.rollback()
            self._pool.putconn(self._conn)
        else:
            self._conn.close()


def _get_pool():
    global _pool
    if _pool is None:
        import psycopg_pool

        _pool = psycopg_pool.ConnectionPool(
            _require_dsn(),
            min_size=1,
            max_size=int(os.environ.get("DATABASE_POOL_MAX", "4")),
            timeout=15,  # fail visibly rather than hang when the DB is unreachable
            kwargs={"prepare_threshold": None},
            open=True,
        )
    return _pool


def connect_postgres(db_path=None) -> PostgresConnection:
    """
    The postgres counterpart of repository.connect()'s connection
    acquisition, keyed off the same db_path argument every existing
    caller already passes:

    - None            -> pooled connection to the runtime database
    - ":memory:"      -> dedicated connection with a fresh, private,
                         dropped-on-close schema (test isolation,
                         equivalent to SQLite's per-connection
                         in-memory database)
    - anything else   -> refused loudly; a filesystem path is a SQLite
                         concept, and silently honoring one while
                         configured for postgres would hide a
                         misconfiguration
    """
    import psycopg

    if db_path is None:
        pool = _get_pool()
        return PostgresConnection(pool.getconn(), pool=pool)

    if db_path == ":memory:":
        schema = "lotsync_test_" + uuid.uuid4().hex[:12]
        conn = psycopg.connect(_require_dsn(), prepare_threshold=None)
        conn.execute(f'CREATE SCHEMA "{schema}"')
        conn.execute(f'SET search_path TO "{schema}"')
        conn.commit()
        return PostgresConnection(conn, test_schema=schema)

    raise ValueError(
        f"DATABASE_ENGINE=postgres cannot open the SQLite-style path {db_path!r} -- "
        "postgres connections are configured via DATABASE_URL. "
        "(Pass None for the runtime database, or ':memory:' for an "
        "isolated disposable test database.)"
    )


def runtime_migrations_verified(dsn_key: str = "") -> bool:
    """Has this process already verified the runtime DB's migrations? (See repository.connect.)"""
    return (dsn_key or os.environ.get("DATABASE_URL", "")) in _migrated_dsns


def mark_runtime_migrations_verified(dsn_key: str = "") -> None:
    _migrated_dsns.add(dsn_key or os.environ.get("DATABASE_URL", ""))
