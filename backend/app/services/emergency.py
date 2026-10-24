"""EmergencyService — routing, payload assembly, dispatch (Task 20, Owner: maiabrunne).

Implements the opt-in, human-in-the-loop emergency flow (Req 11):

- ``evaluate`` returns a routing decision ONLY when the feature is enabled and the
  alert meets the configured emergency criteria; otherwise ``None`` (Req 11.1–11.3).
- Routing is transparent and deterministic: prefer the user's preferred doctor when
  reachable, else the nearest cardiac-capable hospital (Req 11.3, 11.10).
- ``build_payload`` assembles a non-diagnostic, experimental payload (Req 11.4, 11.9).
- ``dispatch`` records every attempt; the default ``simulated`` channel contacts no
  one, and a ``real`` channel is blocked unless opted-in (Req 11.5–11.7).

Builds on the Task 18 data layer (``care_repository`` + ``care_models``): the
repository manages its own connections, so this service holds no connection handle.
Decisions are plain dicts (JSON-serializable) so they round-trip to the client and
back into ``dispatch``.
"""
from __future__ import annotations

import json
from typing import Any

from .. import emergency_config as cfg
from ..adapters.notifier import NotifierAdapter, SimulatedNotifier
from ..db import care_repository as repo
from ..db.care_models import CareProfile, DispatchEvent, Provider
from .provider import ProviderService


class EmergencyError(Exception):
    """Raised for emergency-flow problems that map to specific HTTP statuses.

    ``code`` is one of: ``'empty_directory'`` (409), ``'real_not_enabled'`` (403).
    """

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _provider_to_dict(p: Provider) -> dict[str, Any]:
    """Serialize a Provider dataclass to the camelCase shape the client expects."""
    return {
        "id": p.id,
        "kind": p.kind,
        "name": p.name,
        "specialty": p.specialty,
        "canHandleCardiacEmergency": p.can_handle_cardiac_emergency,
        "phone": p.phone,
        "address": p.address,
        "lat": p.lat,
        "lon": p.lon,
        "isSynthetic": p.is_synthetic,
    }


class EmergencyService:
    """Decides who to notify, builds the payload, and performs a gated dispatch."""

    def __init__(self, notifier: NotifierAdapter | None = None) -> None:
        self._providers = ProviderService()
        self._notifier = notifier or SimulatedNotifier()

    # --- Routing ---------------------------------------------------------
    def evaluate(
        self,
        *,
        alert_state: str,
        lat: float | None,
        lon: float | None,
        location_approximate: bool = False,
    ) -> dict[str, Any] | None:
        """Return an ``EmergencyDecision`` dict, or ``None`` when no flow should run.

        Returns ``None`` when the emergency feature is disabled or the alert state is
        not an emergency trigger (Req 11.1, 11.2). Raises :class:`EmergencyError`
        (``empty_directory``) when there is no provider to route to.
        """
        settings = repo.get_settings()
        if not settings.emergency_enabled:
            return None
        if alert_state not in cfg.EMERGENCY_TRIGGER_STATES:
            return None

        profile = repo.get_care_profile()
        use_lat, use_lon, approx = self._resolve_location(profile, lat, lon, location_approximate)

        recipient, reason = self._route(profile, use_lat, use_lon)
        if recipient is None:
            raise EmergencyError(
                "empty_directory",
                "No providers are available to route to. Contact your local emergency "
                "services directly.",
            )

        payload = self.build_payload(
            profile=profile,
            alert_state=alert_state,
            lat=use_lat,
            lon=use_lon,
            approximate=approx,
        )
        return {
            "recipient": _provider_to_dict(recipient),
            "routingReason": reason,
            "payload": payload,
            "channel": self._default_channel(),
        }

    def _resolve_location(
        self,
        profile: CareProfile | None,
        lat: float | None,
        lon: float | None,
        approximate: bool,
    ) -> tuple[float, float, bool]:
        """Use live coordinates when present, else fall back to the profile default (Req 10.6/10.8)."""
        if lat is not None and lon is not None:
            return lat, lon, approximate
        if profile is not None and profile.default_lat is not None and profile.default_lon is not None:
            return profile.default_lat, profile.default_lon, True
        # Last-resort: no location at all. ProviderService still ranks by distance
        # from (0,0); the payload flags the location as approximate/unknown.
        return 0.0, 0.0, True

    def _route(
        self, profile: CareProfile | None, lat: float, lon: float
    ) -> tuple[Provider | None, str]:
        """Apply the transparent routing rule (Req 11.3). Returns (recipient, reason)."""
        preferred_id = profile.preferred_provider_id if profile else None
        ranked = self._providers.suggest(lat, lon, emergency=True, preferred_id=preferred_id)
        if not ranked:
            return None, cfg.REASON_NEAREST_CAPABLE

        # Rule 1: preferred doctor, if present and within reach.
        if preferred_id is not None:
            for s in ranked:
                if s.provider.id == preferred_id and s.distance_km <= cfg.MAX_REACHABLE_KM:
                    return s.provider, cfg.REASON_PREFERRED_REACHABLE

        # Rule 2: nearest cardiac-capable provider (ranked list already puts capable
        # providers first, then nearest).
        for s in ranked:
            if s.provider.can_handle_cardiac_emergency:
                return s.provider, cfg.REASON_NEAREST_CAPABLE

        # No capable provider exists; fall back to the single nearest provider so the
        # flow still surfaces someone, with the nearest-capable reason for auditing.
        return ranked[0].provider, cfg.REASON_NEAREST_CAPABLE

    # --- Payload ---------------------------------------------------------
    def build_payload(
        self,
        *,
        profile: CareProfile | None,
        alert_state: str,
        lat: float,
        lon: float,
        approximate: bool,
    ) -> dict[str, Any]:
        """Assemble the dispatch payload (Req 11.4). Non-diagnostic and experimental (Req 11.9)."""
        summary = (
            cfg.FINDING_SUMMARY_PREFIX
            + f"an '{alert_state}' level pattern was observed in the user's synthetic monitoring data."
        )
        contacts = (
            [
                {
                    "name": c.name,
                    "relationship": c.relationship,
                    "phone": c.phone,
                    "priority": c.priority,
                }
                for c in profile.emergency_contacts
            ]
            if profile
            else []
        )
        return {
            "patient": {
                "name": profile.full_name if profile else None,
                "phone": profile.phone if profile else None,
            },
            "location": {
                "lat": lat,
                "lon": lon,
                "approximate": approximate,
                "description": None,
            },
            "emergencyContacts": contacts,
            "findingSummary": summary,
            "isExperimental": True,
        }

    # --- Dispatch --------------------------------------------------------
    def dispatch(
        self,
        decision: dict[str, Any],
        *,
        channel: str | None = None,
        confirmed: bool,
        alert_id: int | None = None,
    ) -> dict[str, Any]:
        """Perform a dispatch for a prior decision; record it in history (Req 11.5–11.7).

        - ``confirmed`` MUST be True; otherwise a ``pending_confirm`` row is recorded
          and nothing is sent (no dispatch without explicit confirmation, Req 11.5).
        - ``channel='simulated'`` (default) records and returns without contacting anyone.
        - ``channel='real'`` is blocked unless :data:`REAL_DISPATCH_ENABLED` is on;
          raises :class:`EmergencyError` (``real_not_enabled``) otherwise (Req 11.6).
        """
        channel = channel or self._default_channel()
        recipient = decision["recipient"]
        payload_json = json.dumps(decision["payload"])

        if not confirmed:
            event_id = repo.insert_dispatch_event(
                DispatchEvent(
                    alert_id=alert_id,
                    recipient_provider_id=recipient.get("id"),
                    routing_reason=decision["routingReason"],
                    channel=channel,
                    status="pending_confirm",
                    payload=payload_json,
                )
            )
            return {
                "id": event_id,
                "status": "pending_confirm",
                "channel": channel,
                "detail": "Dispatch requires explicit confirmation; nothing was sent.",
            }

        if channel == cfg.CHANNEL_REAL and not cfg.REAL_DISPATCH_ENABLED:
            raise EmergencyError(
                "real_not_enabled",
                "A real dispatch channel is not enabled. Real outreach requires an opt-in "
                "configuration flag and a configured notifier. The default simulated channel "
                "records the dispatch in-app without contacting anyone.",
            )

        result = self._notifier.send(recipient, decision["payload"])
        event_id = repo.insert_dispatch_event(
            DispatchEvent(
                alert_id=alert_id,
                recipient_provider_id=recipient.get("id"),
                routing_reason=decision["routingReason"],
                channel=channel,
                status=result.status,
                payload=payload_json,
            )
        )
        return {
            "id": event_id,
            "status": result.status,
            "channel": channel,
            "detail": result.detail,
        }

    @staticmethod
    def _default_channel() -> str:
        """Simulated by default; real only when explicitly opted-in (Req 11.6)."""
        return cfg.CHANNEL_REAL if cfg.REAL_DISPATCH_ENABLED else cfg.CHANNEL_SIMULATED
