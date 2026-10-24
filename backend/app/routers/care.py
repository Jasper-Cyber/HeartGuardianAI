"""Care profile / providers / emergency routers (Tasks 19-21, 24-25, Owner: maiabrunne).

Builds on the Task 18 data layer (``care_repository`` + ``care_models``) and the
Task 18/21 settings router (``routers/settings.py``, which owns ``/settings`` and
``/settings/disclaimer-ack``). This module adds the remaining care-network surface:

- ``/care/profile``            get/update care profile + emergency contacts (Req 10)
- ``/providers``               ranked provider suggestions (Req 10.4–10.7)
- ``/disclaimer``              shared disclaimer + concise experimental notice (Req 12.1, 12.6)
- ``/emergency/evaluate``      routing decision + payload preview (Req 11.2–11.4)
- ``/emergency/dispatch``      gated dispatch, simulated by default (Req 11.5–11.6)
- ``/emergency/history``       dispatch history (Req 11.7)

The repository manages its own connections, so these routes need no connection
dependency.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .. import disclaimer as disclaimer_copy
from .. import emergency_config as cfg
from ..db import care_repository as repo
from ..db.care_models import CareProfile, EmergencyContact
from ..services.emergency import EmergencyError, EmergencyService
from ..services.provider import ProviderService

router = APIRouter(tags=["care-network"])


# ---------------------------------------------------------------------------
# Pydantic models (camelCase wire shapes)
# ---------------------------------------------------------------------------
class EmergencyContactModel(BaseModel):
    name: str
    relationship: Optional[str] = None
    phone: str
    priority: int = 1


class CareProfileModel(BaseModel):
    fullName: Optional[str] = None
    phone: Optional[str] = None
    defaultLat: Optional[float] = None
    defaultLon: Optional[float] = None
    preferredProviderId: Optional[int] = None
    emergencyContacts: list[EmergencyContactModel] = Field(default_factory=list)

    @classmethod
    def from_model(cls, p: CareProfile | None) -> "CareProfileModel":
        if p is None:
            return cls()
        return cls(
            fullName=p.full_name,
            phone=p.phone,
            defaultLat=p.default_lat,
            defaultLon=p.default_lon,
            preferredProviderId=p.preferred_provider_id,
            emergencyContacts=[
                EmergencyContactModel(
                    name=c.name, relationship=c.relationship, phone=c.phone, priority=c.priority
                )
                for c in p.emergency_contacts
            ],
        )


class EvaluateIn(BaseModel):
    alertState: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    locationApproximate: bool = False


class DispatchIn(BaseModel):
    decision: dict[str, Any]
    confirmed: bool = False
    channel: Optional[str] = None
    alertId: Optional[int] = None


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------
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
def get_care_profile() -> CareProfileModel:
    """Return the care profile + emergency contacts (Req 10.2)."""
    return CareProfileModel.from_model(repo.get_care_profile())


@router.put("/care/profile", response_model=CareProfileModel)
def put_care_profile(body: CareProfileModel) -> CareProfileModel:
    """Create/replace the care profile + contacts (Req 10.2, 10.3)."""
    if body.preferredProviderId is not None and repo.get_provider(body.preferredProviderId) is None:
        raise HTTPException(status_code=422, detail="preferredProviderId is not a known provider")
    profile = CareProfile(
        full_name=body.fullName,
        phone=body.phone,
        default_lat=body.defaultLat,
        default_lon=body.defaultLon,
        preferred_provider_id=body.preferredProviderId,
        emergency_contacts=[
            EmergencyContact(
                name=c.name, relationship=c.relationship, phone=c.phone, priority=c.priority
            )
            for c in body.emergencyContacts
        ],
    )
    return CareProfileModel.from_model(repo.upsert_care_profile(profile))


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
@router.get("/providers")
def get_providers(
    lat: float = Query(...),
    lon: float = Query(...),
    emergency: bool = Query(False),
) -> dict[str, Any]:
    """Ranked provider suggestions near a location (Req 10.4–10.7, 10.10)."""
    profile = repo.get_care_profile()
    preferred_id = profile.preferred_provider_id if profile else None
    suggestions = ProviderService().suggest(lat, lon, emergency=emergency, preferred_id=preferred_id)
    return {
        "suggestions": [
            {
                "provider": {
                    "id": s.provider.id,
                    "kind": s.provider.kind,
                    "name": s.provider.name,
                    "specialty": s.provider.specialty,
                    "canHandleCardiacEmergency": s.provider.can_handle_cardiac_emergency,
                    "phone": s.provider.phone,
                    "address": s.provider.address,
                    "lat": s.provider.lat,
                    "lon": s.provider.lon,
                    "isSynthetic": s.provider.is_synthetic,
                },
                "distanceKm": s.distance_km,
                "isPreferred": s.is_preferred,
            }
            for s in suggestions
        ],
        "isSynthetic": True,
    }


# ---------------------------------------------------------------------------
# Emergency
# ---------------------------------------------------------------------------
def _handle_emergency_error(err: EmergencyError) -> HTTPException:
    status = {"empty_directory": 409, "real_not_enabled": 403}.get(err.code, 400)
    return HTTPException(status_code=status, detail=err.detail)


@router.post("/emergency/evaluate")
def emergency_evaluate(body: EvaluateIn) -> dict[str, Any]:
    """Return a routing decision + payload preview, or ``enabled:false`` (Req 11.2–11.4)."""
    service = EmergencyService()
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
        enabled = repo.get_settings().emergency_enabled
        return {
            "decision": None,
            "enabled": enabled,
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
def emergency_dispatch(body: DispatchIn) -> dict[str, Any]:
    """Perform a gated dispatch; simulated by default, real requires opt-in (Req 11.5–11.6)."""
    # Guard: never dispatch when the feature is disabled (Req 11.1).
    if not repo.get_settings().emergency_enabled:
        raise HTTPException(
            status_code=403,
            detail="The emergency-response feature is disabled. Enable it in settings first.",
        )
    service = EmergencyService()
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
def emergency_history() -> dict[str, Any]:
    """Return past dispatch events, newest first (Req 11.7)."""
    events = repo.list_dispatch_events()
    return {
        "events": [
            {
                "id": e.id,
                "alertId": e.alert_id,
                "recipientProviderId": e.recipient_provider_id,
                "routingReason": e.routing_reason,
                "channel": e.channel,
                "status": e.status,
                "payload": e.payload,  # JSON text as stored
                "createdAt": e.created_at,
            }
            for e in events
        ]
    }
