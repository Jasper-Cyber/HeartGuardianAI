"""Insights endpoint (Task 12) — current alert state + history (Req 4)."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from .. import emergency_config as cfg
from ..db import repository as repo
from ..db.models import Alert
from ..services.alerts import EXPERIMENTAL_LABEL, AlertService

router = APIRouter(prefix="/insights", tags=["insights"])
_service = AlertService()


class AlertOut(BaseModel):
    id: Optional[int]
    state: str
    title: str
    explanation: str
    nextSteps: str
    findingIds: list[int]
    emergencyGuidance: str = cfg.EMERGENCY_GUIDANCE
    experimentalLabel: str = EXPERIMENTAL_LABEL
    isExperimental: bool = True
    createdAt: Optional[str] = None

    @classmethod
    def from_model(cls, a: Alert) -> "AlertOut":
        try:
            ids = json.loads(a.finding_ids)
        except (ValueError, TypeError):
            ids = []
        return cls(
            id=a.id,
            state=a.state,
            title=a.title,
            explanation=a.explanation,
            nextSteps=a.next_steps,
            findingIds=ids,
            createdAt=a.created_at,
        )


class InsightsResponse(BaseModel):
    current: Optional[AlertOut]
    history: list[AlertOut]


@router.get("", response_model=InsightsResponse)
def get_insights() -> InsightsResponse:
    """Return the latest alert and recent alert history.

    If no alert exists yet, generate one from current findings so the client
    always has a state to display.
    """
    current = _service.current()
    if current is None:
        current = _service.evaluate_and_store(run_analysis=True)

    history = repo.list_alerts(limit=20)
    return InsightsResponse(
        current=AlertOut.from_model(current),
        history=[AlertOut.from_model(a) for a in history],
    )
