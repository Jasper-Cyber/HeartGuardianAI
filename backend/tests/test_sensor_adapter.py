"""Tests for the SensorAdapter interface + adapters (Task 7, Req 6)."""
import importlib
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def mod(tmp_path, monkeypatch):
    monkeypatch.setenv("HEARTGUARDIAN_DB", str(tmp_path / "sensor.db"))

    from app.db import connection as conn_mod

    importlib.reload(conn_mod)
    from app.db import repository as repo_mod

    importlib.reload(repo_mod)
    from app.services import simulator as sim_mod

    importlib.reload(sim_mod)
    from app.adapters import sensor as sensor_mod

    importlib.reload(sensor_mod)

    conn_mod.init_db()
    return sensor_mod


def test_simulated_adapter_satisfies_protocol(mod):
    adapter = mod.SimulatedSensorAdapter()
    assert isinstance(adapter, mod.SensorAdapter)  # runtime_checkable Protocol


def test_capabilities_lists_metrics(mod):
    caps = mod.SimulatedSensorAdapter().capabilities()
    assert {"hr", "hrv", "spo2", "rhythm", "activity", "sleep"} == caps


def test_read_batch_returns_readings_over_range(mod):
    adapter = mod.SimulatedSensorAdapter()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=5)  # 6 inclusive hourly steps
    readings = adapter.read_batch(start, end, timedelta(hours=1))
    # 6 metrics per step * 6 steps = 36 readings.
    assert len(readings) == 36
    assert {r.metric_type for r in readings} == {"hr", "hrv", "spo2", "rhythm", "activity", "sleep"}
    # read_batch must NOT persist (it's a pure source read).
    from app.db import repository as repo

    assert repo.count_measurements() == 0


def test_read_batch_rejects_bad_range(mod):
    adapter = mod.SimulatedSensorAdapter()
    start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    end = start - timedelta(hours=1)
    with pytest.raises(ValueError):
        adapter.read_batch(start, end)


def test_read_batch_is_deterministic(mod):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=10)
    a = mod.SimulatedSensorAdapter(mod.SimulatorService())
    b = mod.SimulatedSensorAdapter(mod.SimulatorService())
    ra = [(m.metric_type, m.value) for m in a.read_batch(start, end)]
    rb = [(m.metric_type, m.value) for m in b.read_batch(start, end)]
    assert ra == rb  # same default seed => identical data


@pytest.mark.parametrize(
    "cls_name",
    ["AppleHealthAdapter", "HealthConnectAdapter", "BluetoothSensorAdapter"],
)
def test_future_adapters_raise(mod, cls_name):
    adapter = getattr(mod, cls_name)()
    assert adapter.capabilities() == set()
    with pytest.raises(NotImplementedError):
        adapter.read_batch(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
