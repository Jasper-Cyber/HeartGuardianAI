"""Repository functions for the care-network tables (Task 18, Owner: maiabrunne).

Thin, well-typed data-access helpers over the ``user_settings``,
``care_profiles``, ``emergency_contacts``, ``providers`` and ``dispatch_events``
tables. Services depend on these functions, not on raw SQL, so swapping the
storage layer (e.g. to Task 4's repository or TimescaleDB later) stays localized.

All functions accept an explicit :class:`sqlite3.Connection` so callers control
transaction boundaries (and tests can share one in-memory db).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from .connection import DEMO_USER_ID


def _now() -> str:
    """Current UTC time as an ISO-8601 string (seconds precision, ``Z`` suffix)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# user_settings
# ---------------------------------------------------------------------------
_DEFAULT_SETTINGS = {
    "warnings_enabled": True,
    "suggestions_enabled": False,
    "emergency_enabled": False,
    "disclaimer_ack_at": None,
}


def get_settings(conn: sqlite3.Connection, user_id: int = DEMO_USER_ID) -> dict[str, Any]:
    """Return the user's settings, creating a default row on first read."""
    row = conn.execute(
        "SELECT warnings_enabled, suggestions_enabled, emergency_enabled, disclaimer_ack_at "
        "FROM user_settings WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO user_settings "
            "(user_id, warnings_enabled, suggestions_enabled, emergency_enabled, updated_at) "
            "VALUES (?, 1, 0, 0, ?)",
            (user_id, _now()),
        )
        return {**_DEFAULT_SETTINGS}
    return {
        "warnings_enabled": bool(row["warnings_enabled"]),
        "suggestions_enabled": bool(row["suggestions_enabled"]),
        "emergency_enabled": bool(row["emergency_enabled"]),
        "disclaimer_ack_at": row["disclaimer_ack_at"],
    }


def update_settings(
    conn: sqlite3.Connection,
    *,
    warnings_enabled: bool | None = None,
    suggestions_enabled: bool | None = None,
    emergency_enabled: bool | None = None,
    user_id: int = DEMO_USER_ID,
) -> dict[str, Any]:
    """Patch feature flags (only the provided fields change) and return the result."""
    current = get_settings(conn, user_id)
    merged = {
        "warnings_enabled": current["warnings_enabled"] if warnings_enabled is None else warnings_enabled,
        "suggestions_enabled": current["suggestions_enabled"] if suggestions_enabled is None else suggestions_enabled,
        "emergency_enabled": current["emergency_enabled"] if emergency_enabled is None else emergency_enabled,
    }
    conn.execute(
        "UPDATE user_settings SET warnings_enabled = ?, suggestions_enabled = ?, "
        "emergency_enabled = ?, updated_at = ? WHERE user_id = ?",
        (
            int(merged["warnings_enabled"]),
            int(merged["suggestions_enabled"]),
            int(merged["emergency_enabled"]),
            _now(),
            user_id,
        ),
    )
    return get_settings(conn, user_id)


def record_disclaimer_ack(conn: sqlite3.Connection, user_id: int = DEMO_USER_ID) -> str:
    """Record that the experimental disclaimer was acknowledged; return the timestamp (Req 12.5)."""
    get_settings(conn, user_id)  # ensure a row exists
    ts = _now()
    conn.execute(
        "UPDATE user_settings SET disclaimer_ack_at = ?, updated_at = ? WHERE user_id = ?",
        (ts, ts, user_id),
    )
    return ts


# ---------------------------------------------------------------------------
# providers
# ---------------------------------------------------------------------------
def _provider_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "name": row["name"],
        "specialty": row["specialty"],
        "canHandleCardiacEmergency": bool(row["can_handle_cardiac_emergency"]),
        "phone": row["phone"],
        "address": row["address"],
        "lat": row["lat"],
        "lon": row["lon"],
        "isSynthetic": bool(row["is_synthetic"]),
    }


def insert_provider(conn: sqlite3.Connection, provider: dict[str, Any]) -> int:
    """Insert one provider directory entry; return its new id."""
    cur = conn.execute(
        "INSERT INTO providers "
        "(kind, name, specialty, can_handle_cardiac_emergency, phone, address, lat, lon, "
        " is_synthetic, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            provider["kind"],
            provider["name"],
            provider.get("specialty"),
            int(provider.get("canHandleCardiacEmergency", False)),
            provider.get("phone"),
            provider.get("address"),
            provider["lat"],
            provider["lon"],
            int(provider.get("isSynthetic", True)),
            _now(),
        ),
    )
    return int(cur.lastrowid)


def list_providers(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return every provider in the directory."""
    rows = conn.execute("SELECT * FROM providers ORDER BY id").fetchall()
    return [_provider_from_row(r) for r in rows]


def get_provider(conn: sqlite3.Connection, provider_id: int) -> dict[str, Any] | None:
    """Return a single provider by id, or ``None``."""
    row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
    return _provider_from_row(row) if row else None


def count_providers(conn: sqlite3.Connection) -> int:
    """Return the number of providers in the directory."""
    return int(conn.execute("SELECT COUNT(*) AS n FROM providers").fetchone()["n"])


# ---------------------------------------------------------------------------
# care_profiles + emergency_contacts
# ---------------------------------------------------------------------------
def get_care_profile(conn: sqlite3.Connection, user_id: int = DEMO_USER_ID) -> dict[str, Any]:
    """Return the care profile with its emergency contacts (empty shell if unset)."""
    row = conn.execute(
        "SELECT full_name, phone, default_lat, default_lon, preferred_provider_id "
        "FROM care_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    contacts = list_emergency_contacts(conn, user_id)
    if row is None:
        return {
            "fullName": None,
            "phone": None,
            "defaultLat": None,
            "defaultLon": None,
            "preferredProviderId": None,
            "emergencyContacts": contacts,
        }
    return {
        "fullName": row["full_name"],
        "phone": row["phone"],
        "defaultLat": row["default_lat"],
        "defaultLon": row["default_lon"],
        "preferredProviderId": row["preferred_provider_id"],
        "emergencyContacts": contacts,
    }


def upsert_care_profile(
    conn: sqlite3.Connection, profile: dict[str, Any], user_id: int = DEMO_USER_ID
) -> dict[str, Any]:
    """Create/replace the care profile and its emergency contacts; return the result.

    ``emergencyContacts`` (if present) fully replaces the existing contact set so
    the stored list always matches what the user submitted.
    """
    conn.execute(
        "INSERT INTO care_profiles "
        "(user_id, full_name, phone, default_lat, default_lon, preferred_provider_id, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET "
        "  full_name = excluded.full_name, phone = excluded.phone, "
        "  default_lat = excluded.default_lat, default_lon = excluded.default_lon, "
        "  preferred_provider_id = excluded.preferred_provider_id, updated_at = excluded.updated_at",
        (
            user_id,
            profile.get("fullName"),
            profile.get("phone"),
            profile.get("defaultLat"),
            profile.get("defaultLon"),
            profile.get("preferredProviderId"),
            _now(),
        ),
    )
    if "emergencyContacts" in profile:
        replace_emergency_contacts(conn, profile["emergencyContacts"], user_id)
    return get_care_profile(conn, user_id)


def list_emergency_contacts(
    conn: sqlite3.Connection, user_id: int = DEMO_USER_ID
) -> list[dict[str, Any]]:
    """Return the user's emergency contacts ordered by priority (1 = first)."""
    rows = conn.execute(
        "SELECT name, relationship, phone, priority FROM emergency_contacts "
        "WHERE user_id = ? ORDER BY priority, id",
        (user_id,),
    ).fetchall()
    return [
        {
            "name": r["name"],
            "relationship": r["relationship"],
            "phone": r["phone"],
            "priority": r["priority"],
        }
        for r in rows
    ]


def replace_emergency_contacts(
    conn: sqlite3.Connection, contacts: list[dict[str, Any]], user_id: int = DEMO_USER_ID
) -> None:
    """Replace all emergency contacts for the user with the provided list."""
    conn.execute("DELETE FROM emergency_contacts WHERE user_id = ?", (user_id,))
    for idx, c in enumerate(contacts, start=1):
        conn.execute(
            "INSERT INTO emergency_contacts (user_id, name, relationship, phone, priority, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                c["name"],
                c.get("relationship"),
                c["phone"],
                c.get("priority", idx),
                _now(),
            ),
        )


# ---------------------------------------------------------------------------
# dispatch_events
# ---------------------------------------------------------------------------
def insert_dispatch_event(
    conn: sqlite3.Connection, event: dict[str, Any], user_id: int = DEMO_USER_ID
) -> int:
    """Record a dispatch event (simulated or real); return its id (Req 11.6)."""
    cur = conn.execute(
        "INSERT INTO dispatch_events "
        "(user_id, alert_id, recipient_provider_id, routing_reason, channel, status, payload, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            event.get("alertId"),
            event.get("recipientProviderId"),
            event["routingReason"],
            event["channel"],
            event["status"],
            json.dumps(event["payload"]),
            _now(),
        ),
    )
    return int(cur.lastrowid)


def list_dispatch_events(
    conn: sqlite3.Connection, user_id: int = DEMO_USER_ID
) -> list[dict[str, Any]]:
    """Return the user's dispatch history, newest first (Req 11.7)."""
    rows = conn.execute(
        "SELECT id, alert_id, recipient_provider_id, routing_reason, channel, status, payload, created_at "
        "FROM dispatch_events WHERE user_id = ? ORDER BY created_at DESC, id DESC",
        (user_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "alertId": r["alert_id"],
            "recipientProviderId": r["recipient_provider_id"],
            "routingReason": r["routing_reason"],
            "channel": r["channel"],
            "status": r["status"],
            "payload": json.loads(r["payload"]),
            "createdAt": r["created_at"],
        }
        for r in rows
    ]
