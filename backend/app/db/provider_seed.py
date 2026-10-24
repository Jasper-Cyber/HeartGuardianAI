"""Synthetic provider directory seed (Task 18, Owner: maiabrunne).

Ships a small, clearly-synthetic directory of doctors and hospitals so the
provider-suggestion and emergency-routing flows are demonstrable without any real
data (Req 10.4, 10.10). Coordinates cluster around a fictional demo location so
haversine distances come out in a realistic few-kilometre range.

All records are labeled ``isSynthetic = True``. Names/addresses are invented and
do not correspond to real providers.
"""
from __future__ import annotations

import sqlite3

from . import care_repository as repo

# Fictional demo "home" location used as the default/approx location in seeds.
DEMO_HOME_LAT = 37.7749
DEMO_HOME_LON = -122.4194

# A deliberately synthetic directory. Mix of doctors and hospitals; only some
# hospitals can handle a cardiac emergency, so emergency routing has to choose.
SYNTHETIC_PROVIDERS: list[dict] = [
    {
        "kind": "doctor",
        "name": "Dr. Avery Sim (Demo)",
        "specialty": "cardiology",
        "canHandleCardiacEmergency": False,
        "phone": "+1-555-0100",
        "address": "12 Placeholder Ave, Demo City",
        "lat": 37.7790,
        "lon": -122.4150,
    },
    {
        "kind": "doctor",
        "name": "Dr. Jordan Example (Demo)",
        "specialty": "general practice",
        "canHandleCardiacEmergency": False,
        "phone": "+1-555-0101",
        "address": "48 Sample St, Demo City",
        "lat": 37.7710,
        "lon": -122.4250,
    },
    {
        "kind": "hospital",
        "name": "Demo General Hospital (Synthetic)",
        "specialty": "emergency",
        "canHandleCardiacEmergency": True,
        "phone": "+1-555-0110",
        "address": "900 Mock Blvd, Demo City",
        "lat": 37.7840,
        "lon": -122.4080,
    },
    {
        "kind": "hospital",
        "name": "Sample Community Clinic (Synthetic)",
        "specialty": "urgent care",
        "canHandleCardiacEmergency": False,
        "phone": "+1-555-0111",
        "address": "120 Example Rd, Demo City",
        "lat": 37.7680,
        "lon": -122.4300,
    },
    {
        "kind": "hospital",
        "name": "Placeholder Heart Center (Synthetic)",
        "specialty": "cardiac emergency",
        "canHandleCardiacEmergency": True,
        "phone": "+1-555-0112",
        "address": "5 Demo Cardiac Way, Demo City",
        "lat": 37.7905,
        "lon": -122.4010,
    },
]


def seed_providers(conn: sqlite3.Connection, *, reset: bool = False) -> int:
    """Seed the synthetic provider directory. Idempotent unless ``reset=True``.

    The tables are created by Task 4's ``init_db()`` (via ``schema.sql``) at app
    startup, so this function only populates rows. Returns the number of providers
    in the directory afterwards; a no-op if already populated and ``reset`` is False.
    """
    if reset:
        conn.execute("DELETE FROM providers")
    if repo.count_providers(conn) == 0:
        for p in SYNTHETIC_PROVIDERS:
            repo.insert_provider(conn, p)
    return repo.count_providers(conn)
