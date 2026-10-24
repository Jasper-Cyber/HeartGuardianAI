"""Tests for AnalysisEngine (Tasks 9-10, Req 3)."""
import importlib

import pytest


@pytest.fixture()
def ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "an.db"))

    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.services import simulator as sim_mod

    importlib.reload(sim_mod)
    from app import analysis_config as cfg_mod

    importlib.reload(cfg_mod)
    from app.services import analysis as an_mod

    importlib.reload(an_mod)

    conn_mod.init_db()
    return an_mod, sim_mod, repo_mod


def _finding_types(findings):
    return {f.finding_type for f in findings}


# --------------------------- baseline + rolling --------------------------- #

def test_compute_baseline_from_readings(ctx):
    an_mod, sim_mod, _ = ctx
    sim = sim_mod.SimulatorService()
    hr = [m for m in sim.generate(steps=100, scenario="A", seed=1, persist=False) if m.metric_type == "hr"]
    engine = an_mod.AnalysisEngine()
    baseline = engine.compute_baseline(hr)
    assert baseline is not None
    assert baseline.metric_type == "hr"
    assert baseline.std > 0
    assert baseline.sample_count > 0


def test_compute_baseline_insufficient_returns_none(ctx):
    an_mod, _, _ = ctx
    from app.db.models import Measurement

    engine = an_mod.AnalysisEngine()
    few = [Measurement(timestamp=f"2026-01-01T00:0{i}:00+00:00", metric_type="hr", value=60.0) for i in range(3)]
    assert engine.compute_baseline(few) is None


def test_rolling_stats_handles_none(ctx):
    an_mod, _, _ = ctx
    engine = an_mod.AnalysisEngine()
    stats = engine.rolling_stats([60.0, None, 62.0, 61.0, None, 63.0], window=3)
    assert not (stats.mean != stats.mean)  # not NaN


# ------------------------------- detectors -------------------------------- #

def test_normal_scenario_has_no_persistent_shift(ctx):
    an_mod, sim_mod, repo_mod = ctx
    sim = sim_mod.SimulatorService()
    sim.generate(steps=200, scenario="A", seed=11)  # persisted
    engine = an_mod.AnalysisEngine()
    findings = engine.run(persist=False)
    assert "persistent_shift" not in _finding_types(findings)


def test_scenario_b_produces_persistent_shift(ctx):
    an_mod, sim_mod, repo_mod = ctx
    sim = sim_mod.SimulatorService()
    sim.generate(steps=400, scenario="B", seed=21)  # strong drift over many steps
    engine = an_mod.AnalysisEngine()
    findings = engine.run(persist=False)
    assert "persistent_shift" in _finding_types(findings)


def test_scenario_c_produces_rhythm_irregularity(ctx):
    an_mod, sim_mod, repo_mod = ctx
    sim = sim_mod.SimulatorService()
    sim.generate(steps=300, scenario="C", seed=31)
    engine = an_mod.AnalysisEngine()
    findings = engine.run(persist=False)
    assert "rhythm_irregularity" in _finding_types(findings)


def test_data_quality_detected_when_many_missing(ctx):
    an_mod, _, repo_mod = ctx
    from app.db.models import Measurement

    # Fill a window of mostly-missing hr samples.
    rows = []
    for i in range(50):
        q = "missing" if i % 2 == 0 else "ok"
        rows.append(
            Measurement(
                timestamp=f"2026-02-01T{i:02d}:00:00+00:00",
                metric_type="hr",
                value=None if q == "missing" else 62.0,
                quality=q,
            )
        )
    repo_mod.insert_measurements(rows)
    engine = an_mod.AnalysisEngine()
    findings = engine.run(persist=False)
    hr_findings = [f for f in findings if f.metric_type == "hr"]
    assert any(f.finding_type == "data_quality" for f in hr_findings)


def test_run_persists_findings_and_baselines(ctx):
    an_mod, sim_mod, repo_mod = ctx
    sim = sim_mod.SimulatorService()
    sim.generate(steps=300, scenario="B", seed=41)
    engine = an_mod.AnalysisEngine()
    findings = engine.run(persist=True)
    # Baselines persisted for numeric metrics.
    assert repo_mod.get_baseline("hr") is not None
    # Findings persisted.
    stored = repo_mod.list_findings()
    assert len(stored) >= 1
    assert len(stored) == len(findings)


def test_run_is_deterministic(ctx):
    an_mod, sim_mod, _ = ctx
    sim = sim_mod.SimulatorService()
    sim.generate(steps=300, scenario="B", seed=51)
    engine = an_mod.AnalysisEngine()
    f1 = engine.run(persist=False)
    f2 = engine.run(persist=False)
    key = lambda fs: sorted((f.metric_type, f.finding_type, f.deviation) for f in fs)
    assert key(f1) == key(f2)  # reproducible (Req 3.7)


def test_findings_carry_supporting_values(ctx):
    an_mod, sim_mod, _ = ctx
    sim = sim_mod.SimulatorService()
    sim.generate(steps=400, scenario="B", seed=61)
    engine = an_mod.AnalysisEngine()
    findings = engine.run(persist=False)
    import json

    for f in findings:
        parsed = json.loads(f.supporting)  # supporting is valid JSON with context
        assert isinstance(parsed, dict)
        assert f.severity_band in ("info", "review", "attention")
