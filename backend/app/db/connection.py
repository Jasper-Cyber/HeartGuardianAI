"""SQLite connection helper shared across the backend.

NOTE (maiabrunne / Task 18): The canonical connection + core-schema module is
Task 4 (Owner: Jasper-Cyber), which is not merged yet. This helper is written to
*coexist* with that work rather than replace it:

- It resolves the same single database file (``HEARTGUARDIAN_DB`` env var, else
  ``heartguardian.db`` at the backend root), so when Task 4 lands both layers read
  and write the same database.
- It only ever creates tables with ``CREATE TABLE IF NOT EXISTS`` and never drops
  anything, so it will not clobber Task 4's ``users`` / ``measurements`` schema.

When Task 4 merges, its ``get_connection`` can replace this one with no change to
the care-network repositories, because they depend only on the function signature
below.
"""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Backend root: backend/app/db/connection.py -> parents[2] == backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB_PATH = _BACKEND_ROOT / "heartguardian.db"


def get_db_path() -> str:
    """Return the path to the SQLite file.

    Uses the ``HEARTGUARDIAN_DB`` environment variable when set (handy for tests
    and for pointing at an in-memory/temp file), otherwise the single on-disk
    database at the backend root.
    """
    return os.environ.get("HEARTGUARDIAN_DB", str(_DEFAULT_DB_PATH))


def connect(db_path: str | None = None) -> sqlite3.Connection:
    """Open a configured SQLite connection.

    - ``row_factory`` is :class:`sqlite3.Row` so callers can use column names.
    - Foreign keys are enabled (off by default in SQLite).
    """
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_connection(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    """Context-managed connection that commits on success and rolls back on error."""
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
