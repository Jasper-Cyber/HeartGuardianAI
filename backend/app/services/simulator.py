"""SimulatorService — synthetic physiological data generator (Task 6, Req 2).

Produces timestamped readings for HR, HRV, SpO2, rhythm, activity, and sleep
under three scenarios:
  A Normal            — fluctuate within a personal baseline
  B Gradual Deviation — resting HR drifts up, HRV down, sleep down over weeks
  C Rhythm Irregularity — intermittent irregular-rhythm flags + correlated HR spikes

All output is synthetic and labeled. Generation is driven by a seedable NumPy
RNG so a given (scenario, seed, step count) is fully reproducible (Req 2.8).
The service persists readings via the repository and tracks progress in sim_state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np

from ..db import repository as repo
from ..db.models import Measurement

# Per-metric personal baseline (mean, std) and physiological clip ranges.
# These are demonstration values, not clinical references.
@dataclass(frozen=True)
class MetricSpec:
    mean: float
    std: float
    lo: float
    hi: float


BASELINES: dict[str, MetricSpec] = {
    "hr": MetricSpec(mean=62.0, std=4.0, lo=40.0, hi=180.0),       # bpm (resting-ish)
    "hrv": MetricSpec(mean=55.0, std=8.0, lo=10.0, hi=150.0),      # ms
    "spo2": MetricSpec(mean=98.0, std=0.6, lo=85.0, hi=100.0),     # %
    "activity": MetricSpec(mean=6000.0, std=1500.0, lo=0.0, hi=25000.0),  # steps/day
    "sleep": MetricSpec(mean=7.5, std=0.7, lo=0.0, hi=12.0),       # hours
}

# Fraction of samples emitted as missing/low quality, to exercise data-quality handling.
MISSING_RATE = 0.03
LOW_QUALITY_RATE = 0.04

# Default cadence between generated readings.
DEFAULT_STEP = timedelta(hours=1)


class SimulatorService:
    """Generates and persists synthetic readings per scenario."""

    def __init__(self) -> None:
        self._state = repo.get_sim_state()

    # --------------------------------------------------------------------- #
    # Controls (mirror the API; persist to sim_state)
    # --------------------------------------------------------------------- #

    def select_scenario(self, scenario: str) -> None:
        if scenario not in ("A", "B", "C"):
            raise ValueError("scenario must be A, B, or C")
        self._state = repo.update_sim_state(scenario=scenario)

    def start(self) -> None:
        self._state = repo.update_sim_state(status="running")

    def pause(self) -> None:
        self._state = repo.update_sim_state(status="paused")

    def reset(self) -> None:
        repo.clear_measurements()
        self._state = repo.update_sim_state(status="paused", cursor_ts=None)

    # --------------------------------------------------------------------- #
    # Generation
    # --------------------------------------------------------------------- #

    def generate(
        self,
        *,
        steps: int,
        scenario: Optional[str] = None,
        seed: Optional[int] = None,
        start_ts: Optional[datetime] = None,
        step: timedelta = DEFAULT_STEP,
        persist: bool = True,
    ) -> list[Measurement]:
        """Generate `steps` timestamped readings for each metric.

        Deterministic for a fixed (scenario, seed, steps, start_ts). Returns the
        generated Measurements and, when persist=True, stores them.
        """
        scenario = scenario or self._state.scenario
        seed = seed if seed is not None else self._state.seed
        rng = np.random.default_rng(seed)
        start_ts = start_ts or datetime(2026, 1, 1, tzinfo=timezone.utc)

        readings: list[Measurement] = []
        for i in range(steps):
            ts = (start_ts + i * step).isoformat()
            progress = i / max(steps - 1, 1)  # 0..1 across the run
            for metric, spec in BASELINES.items():
                value = self._sample_metric(metric, spec, scenario, progress, rng)
                quality, value = self._apply_quality(value, rng)
                readings.append(
                    Measurement(
                        timestamp=ts,
                        metric_type=metric,  # type: ignore[arg-type]
                        value=value,
                        quality=quality,  # type: ignore[arg-type]
                        scenario=scenario,  # type: ignore[arg-type]
                    )
                )
            # Rhythm is a categorical flag: 0.0 = normal, 1.0 = irregular.
            rhythm_val, rhythm_q = self._sample_rhythm(scenario, progress, rng)
            readings.append(
                Measurement(
                    timestamp=ts,
                    metric_type="rhythm",
                    value=rhythm_val,
                    quality=rhythm_q,  # type: ignore[arg-type]
                    scenario=scenario,  # type: ignore[arg-type]
                )
            )

        if persist and readings:
            repo.insert_measurements(readings)
            last_ts = (start_ts + (steps - 1) * step).isoformat()
            self._state = repo.update_sim_state(cursor_ts=last_ts)
        return readings

    # --------------------------------------------------------------------- #
    # Per-scenario sampling
    # --------------------------------------------------------------------- #

    def _sample_metric(
        self, metric: str, spec: MetricSpec, scenario: str, progress: float, rng
    ) -> float:
        mean = spec.mean
        if scenario == "B":
            # Gradual deviation over the run: HR up, HRV down, sleep down.
            if metric == "hr":
                mean += 18.0 * progress
            elif metric == "hrv":
                mean -= 22.0 * progress
            elif metric == "sleep":
                mean -= 2.0 * progress
        elif scenario == "C" and metric == "hr":
            # Occasional correlated HR spikes accompany irregular rhythm.
            if rng.random() < 0.15:
                mean += rng.uniform(25.0, 45.0)
        value = float(rng.normal(mean, spec.std))
        return float(np.clip(value, spec.lo, spec.hi))

    def _sample_rhythm(self, scenario: str, progress: float, rng) -> tuple[float, str]:
        """Return (value, quality). value 1.0 => irregular flag."""
        if scenario == "C":
            p_irregular = 0.12
        elif scenario == "B":
            p_irregular = 0.01 + 0.03 * progress
        else:
            p_irregular = 0.005
        value = 1.0 if rng.random() < p_irregular else 0.0
        return value, "ok"

    def _apply_quality(self, value: float, rng) -> tuple[str, Optional[float]]:
        """Occasionally mark a sample missing (value None) or low quality (Req 2 / 3.4)."""
        r = rng.random()
        if r < MISSING_RATE:
            return "missing", None
        if r < MISSING_RATE + LOW_QUALITY_RATE:
            return "low", value
        return "ok", value
