"""Transparent, configurable thresholds for the AnalysisEngine (Tasks 9-10, Req 3).

All detection behavior is driven by these constants so results are transparent
and reproducible (Req 3.6, 3.7). These are DEMONSTRATION thresholds, not clinical
cut-offs, and none of them produce a validated "risk score".
"""
from __future__ import annotations

# --- Baseline ---------------------------------------------------------------
# How many of the earliest readings per metric define the personal baseline.
BASELINE_WINDOW: int = 72        # e.g. first ~3 days at hourly cadence
MIN_BASELINE_SAMPLES: int = 12   # below this, baseline is considered unreliable

# --- Rolling statistics -----------------------------------------------------
ROLLING_WINDOW: int = 24         # samples per rolling window (~1 day hourly)

# --- persistent_shift detector ---------------------------------------------
# Rolling mean must deviate more than K_SIGMA * baseline_std from baseline mean,
# sustained over at least SUSTAINED_WINDOWS consecutive rolling points.
PERSISTENT_K_SIGMA: float = 2.0
SUSTAINED_WINDOWS: int = 6

# --- combination detector (HR up AND HRV down together) --------------------
COMBO_HR_UP_SIGMA: float = 1.5   # HR rolling mean this many std above baseline
COMBO_HRV_DOWN_SIGMA: float = 1.5  # HRV rolling mean this many std below baseline

# --- rhythm_irregularity detector ------------------------------------------
# Fraction of irregular-rhythm flags within the trailing window that trips review.
RHYTHM_IRREGULAR_FRACTION: float = 0.08
RHYTHM_WINDOW: int = 48

# --- data_quality detector --------------------------------------------------
# Fraction of missing/low-quality samples above which a metric window is flagged
# as a data-quality issue rather than a physiological trend (Req 3.4).
DATA_QUALITY_BAD_FRACTION: float = 0.30
DATA_QUALITY_WINDOW: int = 48

# --- severity banding -------------------------------------------------------
# Standardized deviation bands used to label findings (info < review < attention).
SEVERITY_REVIEW_SIGMA: float = 2.0
SEVERITY_ATTENTION_SIGMA: float = 3.0
