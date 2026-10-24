"""Emergency-routing configuration (Task 20/21, Owner: maiabrunne).

Single source of truth for the transparent, configurable rules used by
:class:`~app.services.emergency.EmergencyService`. Keeping every threshold and
the copy here (rather than inline) makes routing decisions auditable and keeps
results deterministic/reproducible for a fixed config (Req 11.3, 11.10).
"""
from __future__ import annotations

from typing import Final

# --- Routing -------------------------------------------------------------
# If the user's preferred doctor is within this great-circle distance, prefer
# them; otherwise route to the nearest cardiac-capable hospital (Req 11.3).
MAX_REACHABLE_KM: Final[float] = 15.0

# Alert states that may trigger the emergency-response flow (Req 11.2). The flow
# still only runs when the feature is enabled AND the user confirms.
EMERGENCY_TRIGGER_STATES: Final[frozenset[str]] = frozenset({"attention"})

# --- Dispatch channels ---------------------------------------------------
CHANNEL_SIMULATED: Final[str] = "simulated"
CHANNEL_REAL: Final[str] = "real"

# A real outbound channel is OFF unless this opt-in flag is explicitly enabled
# AND a working NotifierAdapter is configured. The MVP keeps this False so the
# default path is always a recorded, no-contact simulated dispatch (Req 11.6).
REAL_DISPATCH_ENABLED: Final[bool] = False

# --- Routing reasons (stable identifiers surfaced to the client) ---------
REASON_PREFERRED_REACHABLE: Final[str] = "preferred_doctor_reachable"
REASON_NEAREST_CAPABLE: Final[str] = "nearest_capable_hospital"

# --- Copy ----------------------------------------------------------------
# Always shown alongside any dispatch, independent of automated routing (Req 11.8).
STATIC_EMERGENCY_GUIDANCE: Final[str] = (
    "If you may be having a heart attack or stroke — e.g. chest pain or pressure, "
    "shortness of breath, face drooping, arm weakness, or slurred speech — call your "
    "local emergency services number immediately. Do not wait for this app."
)

# Non-diagnostic framing for the dispatch finding summary (Req 11.4, 11.9).
FINDING_SUMMARY_PREFIX: Final[str] = (
    "Experimental, non-diagnostic summary of synthetic monitoring signals (not a "
    "diagnosis of any condition): "
)
