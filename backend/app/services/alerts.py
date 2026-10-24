"""AlertService — turn anomaly findings into an explainable alert (Task 12, Req 4).

Maps the engine's findings to one of three interface states and builds a
human-readable explanation + next steps. Every alert carries the static
emergency guidance and an experimental/not-medical-advice label. The service
never diagnoses a condition.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from .. import emergency_config as cfg
from ..db import repository as repo
from ..db.connection import DEMO_USER_ID
from ..db.models import Alert, AnomalyFinding
from .analysis import AnalysisEngine

# Severity band -> alert state precedence (higher index = more serious).
_STATE_FOR_BAND = {
    "info": "normal",
    "review": "trend_review",
    "attention": "attention",
}
_STATE_RANK = {"normal": 0, "trend_review": 1, "attention": 2}

EXPERIMENTAL_LABEL = (
    "Experimental prototype — not medical advice. This does not diagnose any condition."
)

_METRIC_LABEL = {
    "hr": "heart rate",
    "hrv": "heart rate variability",
    "spo2": "blood oxygen",
    "activity": "activity",
    "sleep": "sleep",
    "rhythm": "heart rhythm",
}

_FINDING_PHRASES = {
    "persistent_shift": "a sustained change from your personal baseline",
    "combination": "heart rate trending up while HRV trends down together",
    "rhythm_irregularity": "a higher-than-usual rate of irregular-rhythm flags",
    "data_quality": "missing or low-quality data (treated as a data issue, not a trend)",
}


@dataclass(slots=True)
class AlertResult:
    state: str
    title: str
    explanation: str
    next_steps: str
    finding_ids: list[int]
    emergency_guidance: str
    is_experimental: bool = True


class AlertService:
    def __init__(self) -> None:
        self._engine = AnalysisEngine()

    def build_from_findings(self, findings: list[AnomalyFinding]) -> AlertResult:
        """Produce an alert from a set of findings (does not persist)."""
        # Data-quality findings don't raise the state on their own.
        trend_findings = [f for f in findings if f.finding_type != "data_quality"]

        state = "normal"
        for f in trend_findings:
            candidate = _STATE_FOR_BAND.get(f.severity_band, "normal")
            if _STATE_RANK[candidate] > _STATE_RANK[state]:
                state = candidate

        title = {
            "normal": "Normal monitoring",
            "trend_review": "Trend review recommended",
            "attention": "Potentially concerning measurement — further assessment advised",
        }[state]

        explanation = self._build_explanation(state, findings)
        next_steps = self._build_next_steps(state)

        return AlertResult(
            state=state,
            title=title,
            explanation=explanation,
            next_steps=next_steps,
            finding_ids=[f.id for f in findings if f.id is not None],
            emergency_guidance=cfg.EMERGENCY_GUIDANCE,
        )

    def _build_explanation(self, state: str, findings: list[AnomalyFinding]) -> str:
        if state == "normal" and not findings:
            return "Your recent measurements are within your personal baseline."
        parts: list[str] = []
        for f in findings:
            metric = _METRIC_LABEL.get(f.metric_type, f.metric_type)
            phrase = _FINDING_PHRASES.get(f.finding_type, f.finding_type)
            detail = ""
            try:
                supporting = json.loads(f.supporting)
                if f.finding_type == "persistent_shift" and "latest_rolling_mean" in supporting:
                    detail = (
                        f" (recent average {supporting['latest_rolling_mean']} vs baseline "
                        f"{supporting['baseline_mean']})"
                    )
                elif f.finding_type == "rhythm_irregularity" and "irregular_fraction" in supporting:
                    detail = f" ({supporting['irregular_fraction']:.0%} of recent readings)"
            except (ValueError, KeyError, TypeError):
                detail = ""
            parts.append(f"In {metric}: {phrase}{detail}.")
        return " ".join(parts)

    def _build_next_steps(self, state: str) -> str:
        if state == "normal":
            return "Keep monitoring. No action needed based on these experimental signals."
        if state == "trend_review":
            return (
                "Consider reviewing the trend over the next few days and discussing it with a "
                "healthcare professional if it persists."
            )
        return (
            "Consider contacting a healthcare professional to review these signals. "
            "If you have symptoms of a possible emergency, contact local emergency services now."
        )

    def evaluate_and_store(self, *, user_id: int = DEMO_USER_ID, run_analysis: bool = True) -> Alert:
        """Run analysis (optional), build the alert, persist it, and return it."""
        if run_analysis:
            findings = self._engine.run(user_id=user_id, persist=True)
        else:
            findings = repo.list_findings(user_id=user_id)

        result = self.build_from_findings(findings)
        alert = Alert(
            user_id=user_id,
            state=result.state,
            title=result.title,
            explanation=result.explanation,
            next_steps=result.next_steps,
            finding_ids=json.dumps(result.finding_ids),
        )
        alert.id = repo.insert_alert(alert)
        return alert

    def current(self, *, user_id: int = DEMO_USER_ID) -> Optional[Alert]:
        return repo.latest_alert(user_id=user_id)
