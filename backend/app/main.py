"""FastAPI application entrypoint for HeartGuardian AI.

Run (from the backend/ directory):
    uvicorn app.main:app --reload --port 8000

Interactive API docs are then available at http://localhost:8000/docs

NOTE: This is an experimental prototype. All data is synthetic and labeled
experimental. The service does not diagnose conditions and is not a medical device.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__

app = FastAPI(
    title="HeartGuardian AI API",
    version=__version__,
    description=(
        "Experimental prototype backend. Serves synthetic physiological data, "
        "anomaly analysis, insights, and an opt-in care-network / emergency flow. "
        "Not a medical device; does not diagnose conditions."
    ),
)

# CORS: allow the Expo dev client (Metro) and local tools to call the API during
# development. Tighten this for any non-local deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-only; scope to known origins before shipping
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness probe used by the mobile client and CI."""
    return {"status": "ok", "version": __version__}


# ---------------------------------------------------------------------------
# Router registration.
# Each feature owner appends ONE line here as their router lands (see TEAM.md
# "Shared files" guidance). Keep these additive to avoid merge conflicts, e.g.:
#
#   from .routers import measurements
#   app.include_router(measurements.router)
# ---------------------------------------------------------------------------

# Care-network / settings / emergency routers (Tasks 18-21, Owner: maiabrunne).
from .routers import care  # noqa: E402

app.include_router(care.router)
