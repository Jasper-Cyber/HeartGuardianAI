"""AnalysisEngine — personalized baselines + anomaly detection (Tasks 9-10, Req 3).

Transparent and reproducible: all thresholds come from ``analysis_config.py`` and
every finding carries the supporting values that triggered it. The engine never
emits a numeric "risk score" presented as validated.

Detectors:
  - persistent_shift      : rolling mean deviates > k·std from baseline, sustained
  - combination           : HR up AND HRV down simultaneously
  - rhythm_irregularity   : density of irregular-rhythm flags exceeds threshold
  - data_quality          : too many missing/low samples -> tag, not a trend (Req 3.4)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .. import analysis_config as cfg
from ..db import repository as repo
from ..db.connection import DEMO_USER_ID, utc_now_iso
from ..db.models import AnomalyFinding, Baseline, Measurement

# Metrics the engine computes baselines + rolling stats for (rhythm handled separately).
NUMERIC_METRICS = ("hr", "hrv", "spo2", "activity", "sleep")


@dataclass(slots=True)
class RollingStats:
    mean: float
    std: float
    trend: float  # slope sign proxy: last rolling mean minus first


class AnalysisEngine:
    # ------------------------------------------------------------------ #
    # Baseline
    # ------------------------------------------------------------------ #

    def compute_baseline(self, readings: list[Measurement]) -> Optional[Baseline]:
        """Mean/std over the earliest BASELINE_WINDOW ok-quality samples of one metric.

        Returns None if there is not enough clean data to form a reliable baseline.
        Assumes all readings share one metric_type.
        """
        vals = [r.value for r in readings if r.quality == "ok" and r.value is not None]
        vals = vals[: cfg.BASELINE_WINDOW]
        if len(vals) < cfg.MIN_BASELINE_SAMPLES:
            return None
        arr = np.asarray(vals, dtype=float)
        metric = readings[0].metric_type
        return Baseline(
            metric_type=metric,
            mean=float(arr.mean()),
            std=float(arr.std(ddof=0)) or 1e-9,  # guard against zero std
            sample_count=len(vals),
            computed_at=utc_now_iso(),
        )

    def rolling_stats(self, series: list[Optional[float]], window: int = cfg.ROLLING_WINDOW) -> RollingStats:
        """Rolling mean/std/trend of a numeric series (NaN-aware via Pandas)."""
        s = pd.Series([np.nan if v is None else v for v in series], dtype=float)
        roll_mean = s.rolling(window, min_periods=1).mean()
        roll_std = s.rolling(window, min_periods=1).std()
        trend = float(roll_mean.iloc[-1] - roll_mean.dropna().iloc[0]) if roll_mean.notna().any() else 0.0
        return RollingStats(
            mean=float(roll_mean.iloc[-1]) if roll_mean.notna().any() else float("nan"),
            std=float(roll_std.iloc[-1]) if roll_std.notna().any() else float("nan"),
            trend=trend,
        )

    # ------------------------------------------------------------------ #
    # Full run: recompute baselines + run detectors for a user
    # ------------------------------------------------------------------ #

    def run(self, *, user_id: int = DEMO_USER_ID, persist: bool = True) -> list[AnomalyFinding]:
        """Recompute baselines and produce anomaly findings for all metrics."""
        findings: list[AnomalyFinding] = []
        series_by_metric: dict[str, list[Measurement]] = {}

        for metric in NUMERIC_METRICS:
            rows = repo.query_measurements(metric_type=metric, user_id=user_id)
            series_by_metric[metric] = rows
            if not rows:
                continue

            baseline = self.compute_baseline(rows)
            if baseline is not None and persist:
                baseline.user_id = user_id
                repo.upsert_baseline(baseline)

            # data_quality first: if the window is too dirty, tag it and skip trend claims.
            dq = self._detect_data_quality(metric, rows)
            if dq is not None:
                findings.append(dq)
                continue
            if baseline is None:
                findings.append(self._data_quality_finding(metric, rows, reason="insufficient baseline"))
                continue

            shift = self._detect_persistent_shift(metric, rows, baseline)
            if shift is not None:
                findings.append(shift)

        # combination uses HR + HRV baselines together.
        combo = self._detect_combination(series_by_metric, user_id=user_id)
        if combo is not None:
            findings.append(combo)

        # rhythm_irregularity from the rhythm flag series.
        rhythm_rows = repo.query_measurements(metric_type="rhythm", user_id=user_id)
        rhythm = self._detect_rhythm(rhythm_rows)
        if rhythm is not None:
            findings.append(rhythm)

        if persist:
            for f in findings:
                f.user_id = user_id
                repo.insert_finding(f)
        return findings

    # ------------------------------------------------------------------ #
    # Detectors
    # ------------------------------------------------------------------ #

    def _detect_data_quality(self, metric: str, rows: list[Measurement]) -> Optional[AnomalyFinding]:
        window = rows[-cfg.DATA_QUALITY_WINDOW :]
        if not window:
            return None
        bad = sum(1 for r in window if r.quality in ("missing", "low") or r.value is None)
        frac = bad / len(window)
        if frac >= cfg.DATA_QUALITY_BAD_FRACTION:
            return self._data_quality_finding(metric, window, reason=f"{frac:.0%} missing/low")
        return None

    def _data_quality_finding(self, metric: str, rows: list[Measurement], reason: str) -> AnomalyFinding:
        return AnomalyFinding(
            metric_type=metric,
            finding_type="data_quality",
            severity_band="info",
            window_start=rows[0].timestamp,
            window_end=rows[-1].timestamp,
            deviation=None,
            supporting=json.dumps({"reason": reason, "samples": len(rows)}),
        )

    def _detect_persistent_shift(
        self, metric: str, rows: list[Measurement], baseline: Baseline
    ) -> Optional[AnomalyFinding]:
        values = [r.value for r in rows]
        s = pd.Series([np.nan if v is None else v for v in values], dtype=float)
        roll_mean = s.rolling(cfg.ROLLING_WINDOW, min_periods=max(cfg.ROLLING_WINDOW // 2, 1)).mean()

        # Standardized deviation of each rolling point from the baseline.
        z = (roll_mean - baseline.mean) / baseline.std
        z = z.dropna()
        if z.empty:
            return None

        # Need SUSTAINED_WINDOWS consecutive points beyond K_SIGMA (same direction).
        exceed = z.abs() >= cfg.PERSISTENT_K_SIGMA
        run = 0
        best_run = 0
        for v in exceed:
            run = run + 1 if v else 0
            best_run = max(best_run, run)
        if best_run < cfg.SUSTAINED_WINDOWS:
            return None

        last_z = float(z.iloc[-1])
        return AnomalyFinding(
            metric_type=metric,
            finding_type="persistent_shift",
            severity_band=self._band(abs(last_z)),
            window_start=rows[0].timestamp,
            window_end=rows[-1].timestamp,
            deviation=round(last_z, 3),
            supporting=json.dumps(
                {
                    "baseline_mean": round(baseline.mean, 3),
                    "baseline_std": round(baseline.std, 3),
                    "latest_rolling_mean": round(float(roll_mean.dropna().iloc[-1]), 3),
                    "sustained_windows": best_run,
                }
            ),
        )

    def _detect_combination(
        self, series_by_metric: dict[str, list[Measurement]], *, user_id: int
    ) -> Optional[AnomalyFinding]:
        hr_rows = series_by_metric.get("hr", [])
        hrv_rows = series_by_metric.get("hrv", [])
        if not hr_rows or not hrv_rows:
            return None
        hr_base = self.compute_baseline(hr_rows)
        hrv_base = self.compute_baseline(hrv_rows)
        if hr_base is None or hrv_base is None:
            return None

        hr_stats = self.rolling_stats([r.value for r in hr_rows])
        hrv_stats = self.rolling_stats([r.value for r in hrv_rows])
        if np.isnan(hr_stats.mean) or np.isnan(hrv_stats.mean):
            return None

        hr_z = (hr_stats.mean - hr_base.mean) / hr_base.std
        hrv_z = (hrv_stats.mean - hrv_base.mean) / hrv_base.std

        if hr_z >= cfg.COMBO_HR_UP_SIGMA and hrv_z <= -cfg.COMBO_HRV_DOWN_SIGMA:
            combined = (abs(hr_z) + abs(hrv_z)) / 2
            return AnomalyFinding(
                metric_type="hr",  # primary metric
                finding_type="combination",
                severity_band=self._band(combined),
                window_start=hr_rows[0].timestamp,
                window_end=hr_rows[-1].timestamp,
                deviation=round(float(combined), 3),
                supporting=json.dumps(
                    {"hr_z": round(float(hr_z), 3), "hrv_z": round(float(hrv_z), 3)}
                ),
            )
        return None

    def _detect_rhythm(self, rhythm_rows: list[Measurement]) -> Optional[AnomalyFinding]:
        window = rhythm_rows[-cfg.RHYTHM_WINDOW :]
        if not window:
            return None
        flags = [r.value for r in window if r.value is not None]
        if not flags:
            return None
        frac = sum(1 for v in flags if v >= 1.0) / len(flags)
        if frac >= cfg.RHYTHM_IRREGULAR_FRACTION:
            return AnomalyFinding(
                metric_type="rhythm",
                finding_type="rhythm_irregularity",
                severity_band="review" if frac < 0.2 else "attention",
                window_start=window[0].timestamp,
                window_end=window[-1].timestamp,
                deviation=round(frac, 3),
                supporting=json.dumps({"irregular_fraction": round(frac, 3), "samples": len(flags)}),
            )
        return None

    def _band(self, abs_z: float) -> str:
        if abs_z >= cfg.SEVERITY_ATTENTION_SIGMA:
            return "attention"
        if abs_z >= cfg.SEVERITY_REVIEW_SIGMA:
            return "review"
        return "info"
