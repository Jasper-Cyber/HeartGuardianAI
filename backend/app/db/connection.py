"""SQLite connection and schema bootstrap for HeartGuardian AI.

Uses the Python standard-library ``sqlite3`` driver. The database is a single
local file (synthetic data only). ``init_db`` applies ``schema.sql`` idempotently
and seeds the single demo user + simulator-state row.

Usage:
    from app.db.connection import get_connection, init_db
    init_db()                      # once at startup
    with get_connection() as conn: # per-request / per-operation
        ...
"""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Resolve the DB path from an env var so tests can point at a temp file.
# Defaults to backend/heartguardian.db.
_DEFAULT_DB = Path(__file__).resolve().parents[2] / "heartguardian.db"
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# The MVP is single-user; this is the fixed demo user id.
DEMO_USER_ID = 1


def _db_path() -> str:
    return os.environ.get("HEARTGUARDIAN_DB", str(_DEFAULT_DB))


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string (schema timestamp format)."""
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    """Open a configured raw SQLite connection (caller must close it)."""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection and ALWAYS close it on exit.

    - ``row_factory`` is :class:`sqlite3.Row` so rows behave like dicts.
    - Foreign keys are enforced.
    - The connection is CLOSED when the ``with`` block exits. (A bare
      ``sqlite3.Connection`` used as a context manager only commits/rolls back
      and does NOT close, which previously leaked a connection on every call.)

    Mutating callers still call ``conn.commit()`` explicitly; reads need no commit.
    On an exception the transaction is rolled back before the connection closes.
    """
    conn = _connect()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables (idempotent) and ensure the demo user + sim_state exist."""
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema_sql)

        now = utc_now_iso()
        # Ensure the single demo user exists.
        conn.execute(
            "INSERT OR IGNORE INTO users (id, display_name, created_at) VALUES (?, ?, ?)",
            (DEMO_USER_ID, "Demo User", now),
        )
        # Ensure the single simulator-state row exists.
        conn.execute(
            """
            INSERT OR IGNORE INTO sim_state (id, scenario, status, seed, cursor_ts, updated_at)
            VALUES (1, 'A', 'paused', 42, NULL, ?)
            """,
            (now,),
        )
        conn.commit()


def reset_db() -> None:
    """Drop and recreate the database file. Intended for tests/dev only."""
    path = _db_path()
    if path != ":memory:" and os.path.exists(path):
        os.remove(path)
    init_db()
