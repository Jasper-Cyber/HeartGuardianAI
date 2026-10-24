"""Tests for AlertService + /insights, /analysis/run, /trends (Tasks 11-12)."""
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "al.db"))

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
    from app.services import alerts as alerts_mod

    importlib.reload(alerts_mod)
    from app.routers import insights as ins_router

    importlib.reload(ins_router)
    from app.routers import analysis as an_router

    importlib.reload(an_router)
    from app import main as main_mod

    importlib.reload(main_mod)

    conn_mod.init_db()
    return {
        "client": TestClient(main_mod.app),
        "sim": sim_mod,
        "alerts": alerts_mod,
        "repo": repo_mod,
    }


# ------------------------------ AlertService ------------------------------ #

def test_no_findings_gives_normal_state(ctx):
    svc = ctx["alerts"].AlertService()
    result = svc.build_from_findings([])
    assert result.state == "normal"
    assert result.is_experimental is True
    assert "emergency" in result.emergency_guidance.lower()


def test_attention_finding_raises_state(ctx):
    from app.db.models import AnomalyFinding

    svc = ctx["alerts"].AlertService()
    finding = AnomalyFinding(
        metric_type="hr",
        finding_type="persistent_shift",
        severity_band="attention",
        window_start="t1",
        window_end="t2",
        supporting='{"baseline_mean": 62, "latest_rolling_mean": 85}',
        deviation=3.5,
    )
    result = svc.build_from_findings([finding])
    assert result.state == "attention"
    assert "heart rate" in result.explanation


def test_data_quality_alone_stays_normal(ctx):
    from app.db.models import AnomalyFinding

    svc = ctx["alerts"].AlertService()
    dq = AnomalyFinding(
        metric_type="hr",
        finding_type="data_quality",
        severity_band="info",
        window_start="t1",
        window_end="t2",
        supporting='{"reason": "50% missing"}',
    )
    result = svc.build_from_findings([dq])
    assert result.state == "normal"  # data quality doesn't raise the state


def test_scenario_b_produces_elevated_alert(ctx):
    ctx["sim"].SimulatorService().generate(steps=400, scenario="B", seed=71)
    svc = ctx["alerts"].AlertService()
    alert = svc.evaluate_and_store(run_analysis=True)
    assert alert.state in ("trend_review", "attention")


# ------------------------------- endpoints -------------------------------- #

def test_insights_endpoint_generates_when_empty(ctx):
    client = ctx["client"]
    resp = client.get("/insights")
    assert resp.status_code == 200
    body = resp.json()
    assert body["current"] is not None
    assert body["current"]["state"] in ("normal", "trend_review", "attention")
    assert body["current"]["isExperimental"] is True
    assert body["current"]["emergencyGuidance"]


def test_analysis_run_endpoint(ctx):
    ctx["sim"].SimulatorService().generate(steps=200, scenario="A", seed=81)
    resp = ctx["client"].post("/analysis/run")
    assert resp.status_code == 200
    body = resp.json()
    assert "findingsCount" in body
    assert body["alertState"] in ("normal", "trend_review", "attention")


def test_trends_daily(ctx):
    ctx["sim"].SimulatorService().generate(steps=200, scenario="A", seed=91)
    resp = ctx["client"].get("/trends", params={"range": "daily"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["range"] == "daily"
    hr = next(s for s in body["series"] if s["metric"] == "hr")
    assert len(hr["points"]) > 0
    assert hr["points"][0]["count"] > 0


def test_trends_single_metric(ctx):
    ctx["sim"].SimulatorService().generate(steps=100, scenario="A", seed=92)
    resp = ctx["client"].get("/trends", params={"range": "weekly", "metric": "hrv"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["series"]) == 1
    assert body["series"][0]["metric"] == "hrv"


def test_trends_invalid_range_422(ctx):
    resp = ctx["client"].get("/trends", params={"range": "hourly"})
    assert resp.status_code == 422


def test_trends_empty_has_empty_points(ctx):
    # No data generated.
    resp = ctx["client"].get("/trends", params={"range": "daily", "metric": "hr"})
    assert resp.status_code == 200
    assert resp.json()["series"][0]["points"] == []
