"""Experimental disclaimer copy as a shared constant (Task 21, Owner: maiabrunne).

Plain-language product notice required by Requirement 12. Lives here as the single
source so the backend (``/settings/disclaimer-ack`` surface, dispatch payloads) and
docs reference the same wording. The mobile client mirrors the concise notice.

This is a product notice for an experimental prototype, not legal advice (Req 12.7).
"""
from __future__ import annotations

from typing import Final

# Full first-launch disclaimer (Req 12.1–12.4).
DISCLAIMER_TEXT: Final[str] = (
    "HeartGuardian AI is an experimental, non-clinical prototype. It does not diagnose "
    "any medical condition and does not guarantee the accuracy, reliability, or timeliness "
    "of its warnings. Warnings are generated from synthetic data and may be false alarms or "
    "may be missed entirely.\n\n"
    "The application and its authors are not responsible or liable for false alarms, missed "
    "events, or any outcome arising from use of the app. Any decision to act on a warning — "
    "including whether to enable warnings, contact anyone, or trigger a dispatch — is solely "
    "your decision and responsibility.\n\n"
    "For any real medical need, contact qualified medical professionals and your local "
    "emergency services. This app does not replace professional medical evaluation.\n\n"
    "This notice is for an experimental prototype and is not legal advice."
)

# Concise banner shown on alert/insight and dispatch surfaces (Req 12.6).
EXPERIMENTAL_NOTICE: Final[str] = (
    "Experimental prototype — not medical advice, not a diagnosis. Warnings may be wrong or "
    "missed; acting on them is your decision."
)
