"""Care-network + settings + emergency routers (Tasks 18-21, Owner: maiabrunne).

Endpoint groups (all additive to the shared ``main.py``):

- ``/settings``                feature flags + disclaimer acknowledgement (Req 10.1, 11.1, 12.5)
- ``/care/profile``            get/update care profile + emergency contacts (Req 10)
- ``/providers``               ranked provider suggestions (Req 10.4–10.7)
- ``/emergency/evaluate``      routing decision + payload preview (Req 11.2–11.4)
- ``/emergency/dispatch``      gated dispatch, simulated by default (Req 11.5–11.6)
- ``/emergency/history``       dispatch history (Req 11.7)

A dependency opens one SQLite connection per request and ensures the care schema +
synthetic provider directory exist, so these routes work even before Task 4 lands.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import disclaimer as disclaimer_copy
from .. import emergency_config as cfg
from ..db import care_repository as repo
from ..db.connection import connect
from ..db.provider_seed import seed_providers
from ..services.emergency import EmergencyError, EmergencyService
from ..services.provider import ProviderService

router = APIRouter(tags=["care-network"])


# ---------------------------------------------------------------------------
# Per-request connection dependency (self-contained until Task 4's lands).
# ---------------------------------------------------------------------------
def get_conn() -> Iterator[Any]:
    """Yield a request-scoped SQLite connection with the care schema + seed ready."""
    conn = connect()
    try:
        seed_providers(conn)  # idempotent: creates schema + seeds directory once
        conn.commit()
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class SettingsIn(BaseModel):
    warnings_enabled: bool | None = Field(default=None, alias="warningsEnabled")
    suggestions_enabled: bool | None = Field(default=None, alias="suggestionsEnabled")
    emergency_enabled: bool | None = Field(default=None, alias="emergencyEnabled")

    model_config = {"populate_by_name": True}


class SettingsOut(BaseModel):
    warningsEnabled: bool
    suggestionsEnabled: bool
    emergencyEnabled: bool
    disclaimerAckAt: str | None


class EmergencyContactModel(BaseModel):
    name: str
    relationship: str | None = None
    phone: str
    priority: int = 1


class CareProfileModel(BaseModel):
    fullName: str | None = None
    phone: str | None = None
    defaultLat: float | None = None
    defaultLon: float | None = None
    preferredProviderId: int | None = None
    emergencyContacts: list[EmergencyContactModel] = Field(default_factory=list)


class EvaluateIn(BaseModel):
    alertState: str
    lat: float | None = None
    lon: float | None = None
    locationApproximate: bool = False


class DispatchIn(BaseModel):
    decision: dict[str, Any]
    confirmed: bool = False
    channel: str | None = None
    alertId: int | None = None


# ---------------------------------------------------------------------------
# Settings + disclaimer
# ---------------------------------------------------------------------------
def _settings_out(s: dict[str, Any]) -> SettingsOut:
    return SettingsOut(
        warningsEnabled=s["warnings_enabled"],
        suggestionsEnabled=s["suggestions_enabled"],
        emergencyEnabled=s["emergency_enabled"],
        disclaimerAckAt=s["disclaimer_ack_at"],
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings(conn=Depends(get_conn)) -> SettingsOut:
    """Return feature flags (suggestions/emergency default OFF) (Req 10.1, 11.1)."""
    return _settings_out(repo.get_settings(conn))


@router.put("/settings", response_model=SettingsOut)
def put_settings(body: SettingsIn, conn=Depends(get_conn)) -> SettingsOut:
    """Patch feature flags; only provided fields change."""
    updated = repo.update_settings(
        conn,
        warnings_enabled=body.warnings_enabled,
        suggestions_enabled=body.suggestions_enabled,
        emergency_enabled=body.emergency_enabled,
    )
    return _settings_out(updated)


@router.post("/settings/disclaimer-ack")
def ack_disclaimer(conn=Depends(get_conn)) -> dict[str, str]:
    """Record the one-time disclaimer acknowledgement (Req 12.5)."""
    ts = repo.record_disclaimer_ack(conn)
    return {"disclaimerAckAt": ts}


@router.get("/disclaimer")
def get_disclaimer() -> dict[str, str]:
    """Return the shared disclaimer + concise experimental notice (Req 12.1, 12.6)."""
    return {
        "text": disclaimer_copy.DISCLAIMER_TEXT,
        "notice": disclaimer_copy.EXPERIMENTAL_NOTICE,
    }


# ---------------------------------------------------------------------------
# Care profile
# ---------------------------------------------------------------------------
@router.get("/care/profile", response_model=CareProfileModel)
def get_care_profile(conn=Depends(get_conn)) -> dict[str, Any]:
    """Return the care profile + emergency contacts (Req 10.2)."""
    return repo.get_care_profile(conn)


@router.put("/care/profile", response_model=CareProfileModel)
def put_care_profile(body: CareProfileModel, conn=Depends(get_conn)) -> dict[str, Any]:
    """Create/replace the care profile + contacts (Req 10.2, 10.3)."""
    if body.preferredProviderId is not None and repo.get_provider(conn, body.preferredProviderId) is None:
        raise HTTPException(status_code=422, detail="preferredProviderId is not a known provider")
    return repo.upsert_care_profile(conn, body.model_dump())


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
@router.get("/providers")
def get_providers(
    lat: float = Query(...),
    lon: float = Query(...),
    emergency: bool = Query(False),
    conn=Depends(get_conn),
) -> dict[str, Any]:
    """Ranked provider suggestions near a location (Req 10.4–10.7, 10.10)."""
    profile = repo.get_care_profile(conn)
    suggestions = ProviderService(conn).suggest(
        lat, lon, emergency=emergency, preferred_id=profile.get("preferredProviderId")
    )
    return {"suggestions": suggestions, "isSynthetic": True}


# ---------------------------------------------------------------------------
# Emergency
# ---------------------------------------------------------------------------
def _handle_emergency_error(err: EmergencyError) -> HTTPException:
    status = {"empty_directory": 409, "real_not_enabled": 403}.get(err.code, 400)
    return HTTPException(status_code=status, detail=err.detail)


@router.post("/emergency/evaluate")
def emergency_evaluate(body: EvaluateIn, conn=Depends(get_conn)) -> dict[str, Any]:
    """Return a routing decision + payload preview, or ``enabled:false`` (Req 11.2–11.4)."""
    service = EmergencyService(conn)
    try:
        decision = service.evaluate(
            alert_state=body.alertState,
            lat=body.lat,
            lon=body.lon,
            location_approximate=body.locationApproximate,
        )
    except EmergencyError as err:
        raise _handle_emergency_error(err) from err

    if decision is None:
        # Either the feature is off or the state is not an emergency trigger.
        settings = repo.get_settings(conn)
        return {
            "decision": None,
            "enabled": settings["emergency_enabled"],
            "emergencyGuidance": cfg.STATIC_EMERGENCY_GUIDANCE,
            "notice": disclaimer_copy.EXPERIMENTAL_NOTICE,
        }
    return {
        "decision": decision,
        "enabled": True,
        "emergencyGuidance": cfg.STATIC_EMERGENCY_GUIDANCE,
        "notice": disclaimer_copy.EXPERIMENTAL_NOTICE,
    }


@router.post("/emergency/dispatch")
def emergency_dispatch(body: DispatchIn, conn=Depends(get_conn)) -> dict[str, Any]:
    """Perform a gated dispatch; simulated by default, real requires opt-in (Req 11.5–11.6)."""
    # Guard: never dispatch when the feature is disabled (Req 11.1).
    if not repo.get_settings(conn)["emergency_enabled"]:
        raise HTTPException(
            status_code=403,
            detail="The emergency-response feature is disabled. Enable it in settings first.",
        )
    service = EmergencyService(conn)
    try:
        result = service.dispatch(
            body.decision,
            channel=body.channel,
            confirmed=body.confirmed,
            alert_id=body.alertId,
        )
    except EmergencyError as err:
        raise _handle_emergency_error(err) from err
    result["emergencyGuidance"] = cfg.STATIC_EMERGENCY_GUIDANCE
    result["notice"] = disclaimer_copy.EXPERIMENTAL_NOTICE
    return result


@router.get("/emergency/history")
def emergency_history(conn=Depends(get_conn)) -> dict[str, Any]:
    """Return past dispatch events, newest first (Req 11.7)."""
    return {"events": repo.list_dispatch_events(conn)}
