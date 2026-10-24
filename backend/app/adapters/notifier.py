"""NotifierAdapter interface + SimulatedNotifier (Task 20, Owner: maiabrunne).

A :class:`NotifierAdapter` isolates the dispatch channel from the
:class:`~app.services.emergency.EmergencyService`. The MVP ships only
:class:`SimulatedNotifier`, which records/returns a result WITHOUT contacting any
real recipient (Req 11.6). Real channels are interface-only stubs that require
opt-in configuration and consent before they could ever be implemented.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class DispatchResult:
    """Outcome of a notifier send.

    ``status`` is one of ``'sent'`` | ``'failed'``. ``detail`` carries a short,
    human-readable note (e.g. that nothing was actually sent in simulation).
    """

    status: str
    detail: str


@runtime_checkable
class NotifierAdapter(Protocol):
    """Pluggable dispatch channel."""

    channel: str

    def send(self, recipient: dict[str, Any], payload: dict[str, Any]) -> DispatchResult: ...


class SimulatedNotifier:
    """Default notifier: records intent and returns success, contacting no one (Req 11.6)."""

    channel = "simulated"

    def send(self, recipient: dict[str, Any], payload: dict[str, Any]) -> DispatchResult:
        name = recipient.get("name", "unknown recipient")
        return DispatchResult(
            status="sent",
            detail=(
                f"SIMULATED dispatch recorded for '{name}'. No real message was sent; "
                "this is an in-app demonstration only."
            ),
        )


# --- Interface-only, future channels (require opt-in config + consent) -----
class SmsNotifierAdapter:
    """Future SMS channel. Not implemented in the MVP (Req 11, safety-gated)."""

    channel = "real"

    def send(self, recipient: dict[str, Any], payload: dict[str, Any]) -> DispatchResult:  # noqa: ARG002
        raise NotImplementedError(
            "SmsNotifierAdapter is interface-only in the MVP. A real SMS channel requires "
            "explicit opt-in configuration, credentials, and user consent."
        )


class VoiceCallNotifierAdapter:
    """Future voice-call channel. Not implemented in the MVP (Req 11, safety-gated)."""

    channel = "real"

    def send(self, recipient: dict[str, Any], payload: dict[str, Any]) -> DispatchResult:  # noqa: ARG002
        raise NotImplementedError(
            "VoiceCallNotifierAdapter is interface-only in the MVP. A real voice channel requires "
            "explicit opt-in configuration, credentials, and user consent."
        )
