"""SensorAdapter interface + implementations (Task 7, Req 6).

A `SensorAdapter` abstracts the *source* of physiological readings from the rest
of the system, so the data source can change without rewriting the app. The MVP
ships `SimulatedSensorAdapter` (backed by the SimulatorService); real-hardware
adapters are interface-only stubs that raise NotImplementedError until built.

Readings are represented by the existing ``Measurement`` dataclass.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable

from ..db.models import Measurement
from ..services.simulator import DEFAULT_STEP, SimulatorService


@runtime_checkable
class SensorAdapter(Protocol):
    """Protocol every sensor data source implements."""

    def read_batch(
        self, start: datetime, end: datetime, step: timedelta = DEFAULT_STEP
    ) -> list[Measurement]:
        """Return readings spanning [start, end] at the given cadence."""
        ...

    def capabilities(self) -> set[str]:
        """Metric types this adapter can provide (e.g. {'hr', 'hrv', ...})."""
        ...


class SimulatedSensorAdapter:
    """Implemented adapter — sources readings from the SimulatorService (Req 6.2).

    Fully functional without real hardware; this is the MVP's data source.
    """

    def __init__(self, simulator: SimulatorService | None = None) -> None:
        self._simulator = simulator or SimulatorService()

    def read_batch(
        self, start: datetime, end: datetime, step: timedelta = DEFAULT_STEP
    ) -> list[Measurement]:
        if end < start:
            raise ValueError("end must be >= start")
        # Number of inclusive steps between start and end.
        span = end - start
        steps = int(span / step) + 1
        return self._simulator.generate(
            steps=steps, start_ts=start, step=step, persist=False
        )

    def capabilities(self) -> set[str]:
        return {"hr", "hrv", "spo2", "rhythm", "activity", "sleep"}


# ---------------------------------------------------------------------------
# Interface-only, future adapters (Req 6.3). These exist to document the
# integration surface; they intentionally raise until real integrations land.
# ---------------------------------------------------------------------------

class _FutureSensorAdapter:
    """Shared base for not-yet-implemented real-hardware adapters."""

    source_name = "future"

    def read_batch(
        self, start: datetime, end: datetime, step: timedelta = DEFAULT_STEP
    ) -> list[Measurement]:
        raise NotImplementedError(
            f"{self.source_name} sensor integration is not implemented in the MVP."
        )

    def capabilities(self) -> set[str]:
        return set()


class AppleHealthAdapter(_FutureSensorAdapter):  # pragma: no cover - future
    source_name = "Apple Health"


class HealthConnectAdapter(_FutureSensorAdapter):  # pragma: no cover - future
    source_name = "Android Health Connect"


class BluetoothSensorAdapter(_FutureSensorAdapter):  # pragma: no cover - future
    source_name = "Bluetooth"
