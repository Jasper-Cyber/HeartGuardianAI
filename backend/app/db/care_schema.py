"""Care-network schema (Task 18, Owner: maiabrunne).

Defines the tables that back the care-profile / provider / emergency features:
``user_settings``, ``care_profiles``, ``emergency_contacts``, ``providers`` and
``dispatch_events`` (matching the design doc's schema).

These statements use ``CREATE TABLE IF NOT EXISTS`` so they are safe to run
alongside Task 4's core schema (``users``, ``measurements``, ...). A minimal
``users`` row is ensured so the care tables' foreign keys resolve even before
Task 4's seed lands; when Task 4 owns ``users`` this simply becomes a no-op.
"""
from __future__ import annotations

import sqlite3

from .connection import connect

# The single synthetic demo user id used across the MVP.
DEMO_USER_ID = 1

# A tolerant ``users`` table so care-network FKs resolve before Task 4 lands.
# Task 4 owns the authoritative definition; IF NOT EXISTS keeps this additive.
_USERS_FALLBACK = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    display_name  TEXT NOT NULL DEFAULT 'Demo User',
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
"""

_CARE_SCHEMA = """
-- Per-user settings & feature flags (Req 10.1, 11.1, 12.5).
CREATE TABLE IF NOT EXISTS user_settings (
    user_id              INTEGER PRIMARY KEY REFERENCES users(id),
    warnings_enabled     INTEGER NOT NULL DEFAULT 1,
    suggestions_enabled  INTEGER NOT NULL DEFAULT 0,
    emergency_enabled    INTEGER NOT NULL DEFAULT 0,
    disclaimer_ack_at    TEXT,
    updated_at           TEXT NOT NULL
);

-- Provider directory: doctors and hospitals (seeded synthetic data) (Req 10.3).
CREATE TABLE IF NOT EXISTS providers (
    id             INTEGER PRIMARY KEY,
    kind           TEXT NOT NULL,          -- 'doctor' | 'hospital'
    name           TEXT NOT NULL,
    specialty      TEXT,
    can_handle_cardiac_emergency INTEGER NOT NULL DEFAULT 0,
    phone          TEXT,
    address        TEXT,
    lat            REAL NOT NULL,
    lon            REAL NOT NULL,
    is_synthetic   INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_providers_kind ON providers(kind);

-- Care profile: the user's own contact info and default/approx location (Req 10).
CREATE TABLE IF NOT EXISTS care_profiles (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    full_name      TEXT,
    phone          TEXT,
    default_lat    REAL,
    default_lon    REAL,
    preferred_provider_id INTEGER REFERENCES providers(id),
    updated_at     TEXT NOT NULL,
    UNIQUE(user_id)
);

-- Emergency contacts linked to a user (Req 10.1).
CREATE TABLE IF NOT EXISTS emergency_contacts (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    name           TEXT NOT NULL,
    relationship   TEXT,
    phone          TEXT NOT NULL,
    priority       INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_contacts_user ON emergency_contacts(user_id, priority);

-- Dispatch history: every emergency routing decision + payload (Req 11.6).
CREATE TABLE IF NOT EXISTS dispatch_events (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    alert_id       INTEGER,
    recipient_provider_id INTEGER REFERENCES providers(id),
    routing_reason TEXT NOT NULL,
    channel        TEXT NOT NULL,          -- 'simulated' | 'real'
    status         TEXT NOT NULL,          -- 'pending_confirm' | 'cancelled' | 'sent' | 'failed'
    payload        TEXT NOT NULL,          -- JSON
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dispatch_user_ts ON dispatch_events(user_id, created_at);
"""


def init_care_schema(conn: sqlite3.Connection | None = None) -> None:
    """Create the care-network tables (idempotent) and ensure the demo user exists.

    Safe to call at startup and in tests. If ``conn`` is omitted a short-lived
    connection is opened and committed.
    """
    owns_connection = conn is None
    conn = conn or connect()
    try:
        conn.execute(_USERS_FALLBACK)
        conn.executescript(_CARE_SCHEMA)
        # Ensure the single demo user row exists so FKs resolve.
        conn.execute(
            "INSERT OR IGNORE INTO users (id, display_name) VALUES (?, 'Demo User')",
            (DEMO_USER_ID,),
        )
        if owns_connection:
            conn.commit()
    finally:
        if owns_connection:
            conn.close()
