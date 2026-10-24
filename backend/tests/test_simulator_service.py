"""Tests for SimulatorService (Task 6, Req 2) and the start-generation seam."""
import importlib

import pytest


@pytest.fixture()
def ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "sim.db"))

    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.services import simulator as sim_mod

    importlib.reload(sim_mod)

    conn_mod.init_db()
    return sim_mod, repo_mod


def test_generate_is_deterministic_for_fixed_seed(ctx):
    sim_mod, _ = ctx
    svc1 = sim_mod.SimulatorService()
    r1 = svc1.generate(steps=24, scenario="A", seed=7, persist=False)
    svc2 = sim_mod.SimulatorService()
    r2 = svc2.generate(steps=24, scenario="A", seed=7, persist=False)
    v1 = [(m.metric_type, m.value) for m in r1]
    v2 = [(m.metric_type, m.value) for m in r2]
    assert v1 == v2  # reproducible (Req 2.8)


def test_generate_persists_readings(ctx):
    sim_mod, repo_mod = ctx
    svc = sim_mod.SimulatorService()
    svc.generate(steps=10, scenario="A", seed=1)
    # 6 metrics per step (hr, hrv, spo2, activity, sleep, rhythm) x 10 steps.
    assert repo_mod.count_measurements() == 60


def test_all_metrics_present(ctx):
    sim_mod, repo_mod = ctx
    svc = sim_mod.SimulatorService()
    svc.generate(steps=5, scenario="A", seed=1)
    metrics = {m.metric_type for m in repo_mod.query_measurements()}
    assert metrics == {"hr", "hrv", "spo2", "activity", "sleep", "rhythm"}


def test_scenario_b_drifts_hr_up_and_hrv_down(ctx):
    sim_mod, _ = ctx
    svc = sim_mod.SimulatorService()
    readings = svc.generate(steps=200, scenario="B", seed=3, persist=False)

    def avg(metric, sl):
        vals = [m.value for m in readings if m.metric_type == metric and m.value is not None]
        return sum(sl(vals)) / len(sl(vals))

    hr = [m.value for m in readings if m.metric_type == "hr" and m.value is not None]
    hrv = [m.value for m in readings if m.metric_type == "hrv" and m.value is not None]
    # First quarter vs last quarter.
    q = len(hr) // 4
    assert sum(hr[-q:]) / q > sum(hr[:q]) / q      # HR trends up
    assert sum(hrv[-q:]) / q < sum(hrv[:q]) / q    # HRV trends down


def test_scenario_c_has_more_irregular_rhythm_than_a(ctx):
    sim_mod, _ = ctx
    svc = sim_mod.SimulatorService()
    a = svc.generate(steps=300, scenario="A", seed=5, persist=False)
    c = svc.generate(steps=300, scenario="C", seed=5, persist=False)
    a_irr = sum(1 for m in a if m.metric_type == "rhythm" and m.value == 1.0)
    c_irr = sum(1 for m in c if m.metric_type == "rhythm" and m.value == 1.0)
    assert c_irr > a_irr  # scenario C injects irregular-rhythm flags (Req 2.5)


def test_emits_some_missing_quality(ctx):
    sim_mod, _ = ctx
    svc = sim_mod.SimulatorService()
    readings = svc.generate(steps=500, scenario="A", seed=9, persist=False)
    missing = [m for m in readings if m.quality == "missing"]
    assert len(missing) > 0  # data-quality handling exercised (Req 3.4)
    assert all(m.value is None for m in missing)  # missing => NULL value


def test_values_clipped_to_physiological_range(ctx):
    sim_mod, _ = ctx
    svc = sim_mod.SimulatorService()
    readings = svc.generate(steps=300, scenario="C", seed=2, persist=False)
    spo2 = [m.value for m in readings if m.metric_type == "spo2" and m.value is not None]
    assert all(85.0 <= v <= 100.0 for v in spo2)


def test_reset_clears_readings(ctx):
    sim_mod, repo_mod = ctx
    svc = sim_mod.SimulatorService()
    svc.generate(steps=10, scenario="A", seed=1)
    assert repo_mod.count_measurements() == 60
    svc.reset()
    assert repo_mod.count_measurements() == 0


def test_select_scenario_validates(ctx):
    sim_mod, _ = ctx
    svc = sim_mod.SimulatorService()
    with pytest.raises(ValueError):
        svc.select_scenario("Z")


def test_start_endpoint_generates_data(ctx, monkeypatch):
    # Reload the router + app against the same temp DB, then hit /simulator/start.
    import importlib

    from fastapi.testclient import TestClient

    from app.routers import simulator as sim_router

    importlib.reload(sim_router)
    from app import main as main_mod

    importlib.reload(main_mod)

    _, repo_mod = ctx
    client = TestClient(main_mod.app)
    assert repo_mod.count_measurements() == 0
    resp = client.post("/simulator/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
    assert repo_mod.count_measurements() > 0  # start generated a batch
