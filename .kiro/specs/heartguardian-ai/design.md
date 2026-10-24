# Design Document — HeartGuardian AI

## Overview

HeartGuardian AI is a two-tier prototype: an Expo/React Native (TypeScript) mobile client and
a FastAPI (Python) backend backed by SQLite. The backend owns the simulator, the analysis
engine, and persistence. The client renders a dark-blue healthcare dashboard, trend charts,
and explainable alerts. Everything runs locally; all data is synthetic and labeled experimental.

Design principles:
- **Transparency over black-box scoring.** Thresholds live in one config; findings carry their supporting values.
- **Separation of concerns.** Simulation, analysis, and persistence are independent, testable modules.
- **Pluggable sensors.** A `SensorAdapter` interface isolates data source from the rest of the system.
- **Safety-first UI.** Emergency guidance and "experimental, not medical advice" labels are always present.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Mobile Client (Expo / RN / TS)          │
│                                                          │
│  Expo Router screens                                     │
│   ├─ Dashboard   ├─ Insights/Alerts  ├─ History          │
│   └─ Simulator controls   └─ Profile/Settings            │
│                                                          │
│  State: React Query (server cache) + Zustand (UI state)  │
│  Charts: react-native-gifted-charts / Skia               │
│  API client: typed fetch wrapper (generated from OpenAPI)│
└───────────────────────────┬──────────────────────────────┘
                            │ HTTP (JSON, localhost / LAN)
┌───────────────────────────▼──────────────────────────────┐
│                   FastAPI Backend (Python)                │
│                                                          │
│  Routers:  /measurements  /trends  /analysis             │
│            /insights      /scenario                       │
│                                                          │
│  Services:                                               │
│   ├─ SimulatorService  (scenarios A/B/C, seedable)        │
│   ├─ SensorAdapter      (SimulatedSensorAdapter)          │
│   ├─ AnalysisEngine     (baseline, rolling stats, finds)  │
│   └─ AlertService       (findings → states + guidance)    │
│                                                          │
│  Repository layer (SQLAlchemy Core / sqlite3)             │
└───────────────────────────┬──────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  SQLite (file) │
                    └────────────────┘
```

### Why these technology choices
- **Expo Router**: file-based navigation, required by the brief, fast to scaffold.
- **React Query + Zustand**: React Query caches server data and handles polling for live simulator
  updates; Zustand holds light UI state (selected range, scenario toggle) without boilerplate.
- **react-native-gifted-charts**: pure RN charts (line/area/bar) that render the trend cards in the
  mockups without native build friction; works in Expo Go.
- **FastAPI**: async, typed, auto OpenAPI — the client's API types are generated from it.
- **SQLite**: embedded, zero-config, file-based; ideal for a reproducible single-user demo. See
  "Database Design" for the rationale and scale-up path.

---

## Database Design

### Choice: SQLite (with a documented scale-up path to TimescaleDB/Postgres)

SQLite is selected because the MVP is single-user, local-first, and demo-oriented. It needs no
server process, ships with Python, and stores everything in one portable file — which directly
serves "store data locally when practical" and "reproducible demo." Physiological data is
naturally relational time-series, and SQLite with proper indexes handles the demo's volume
(thousands of rows) comfortably. If the system ever needed many concurrent users or
high-frequency streaming, the migration target is **TimescaleDB** (a Postgres time-series
extension); the repository layer abstracts SQL access so that swap stays localized.

### Schema

```sql
-- One synthetic user for the MVP (no real PII).
CREATE TABLE users (
    id            INTEGER PRIMARY KEY,
    display_name  TEXT NOT NULL DEFAULT 'Demo User',
    created_at    TEXT NOT NULL            -- ISO-8601 UTC
);

-- Normalized time-series of readings. metric_type keys the physiological signal.
CREATE TABLE measurements (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    timestamp     TEXT NOT NULL,           -- ISO-8601 UTC
    metric_type   TEXT NOT NULL,           -- 'hr' | 'hrv' | 'spo2' | 'rhythm' | 'activity' | 'sleep'
    value         REAL,                    -- NULL => missing/low-quality sample
    quality       TEXT NOT NULL DEFAULT 'ok', -- 'ok' | 'low' | 'missing'
    is_synthetic  INTEGER NOT NULL DEFAULT 1, -- always 1 in MVP
    scenario      TEXT NOT NULL            -- 'A' | 'B' | 'C'
);
CREATE INDEX idx_meas_user_metric_ts ON measurements(user_id, metric_type, timestamp);
CREATE INDEX idx_meas_ts            ON measurements(timestamp);

-- Learned per-metric baseline (recomputed by the analysis engine).
CREATE TABLE baselines (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    metric_type   TEXT NOT NULL,
    mean          REAL NOT NULL,
    std           REAL NOT NULL,
    sample_count  INTEGER NOT NULL,
    computed_at   TEXT NOT NULL,
    UNIQUE(user_id, metric_type)
);

-- Structured anomaly findings produced by the engine.
CREATE TABLE anomaly_findings (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    metric_type   TEXT NOT NULL,
    finding_type  TEXT NOT NULL,           -- 'persistent_shift' | 'combination' | 'rhythm_irregularity' | 'data_quality'
    severity_band TEXT NOT NULL,           -- 'info' | 'review' | 'attention'
    window_start  TEXT NOT NULL,
    window_end    TEXT NOT NULL,
    deviation     REAL,                    -- standardized deviation from baseline
    supporting    TEXT NOT NULL,           -- JSON: raw supporting values
    created_at    TEXT NOT NULL
);
CREATE INDEX idx_find_user_ts ON anomaly_findings(user_id, created_at);

-- User-facing alerts derived from findings.
CREATE TABLE alerts (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    state         TEXT NOT NULL,           -- 'normal' | 'trend_review' | 'attention'
    title         TEXT NOT NULL,
    explanation   TEXT NOT NULL,           -- human-readable supporting-data summary
    next_steps    TEXT NOT NULL,
    finding_ids   TEXT NOT NULL,           -- JSON array of anomaly_findings.id
    is_experimental INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

-- Simulator session state (single row updated in place).
CREATE TABLE sim_state (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    scenario      TEXT NOT NULL DEFAULT 'A',
    status        TEXT NOT NULL DEFAULT 'paused', -- 'running' | 'paused'
    seed          INTEGER NOT NULL DEFAULT 42,
    cursor_ts     TEXT,                    -- next timestamp to generate
    updated_at    TEXT NOT NULL
);
```

Design notes:
- `value` is nullable and paired with `quality` so missing/low-quality data is first-class and
  distinguishable from a physiological trend (Req 3.4).
- `supporting` and `finding_ids` are JSON text columns — pragmatic for SQLite and enough for the demo.
- `sim_state` is a single-row table (`CHECK id=1`) representing the current simulator session.

---

## Components and Interfaces

### Backend

#### SensorAdapter (Req 6)
```python
class SensorAdapter(Protocol):
    def read_batch(self, start: datetime, end: datetime, step: timedelta) -> list[Reading]: ...
    def capabilities(self) -> set[str]: ...

class SimulatedSensorAdapter:        # implemented
    def __init__(self, simulator: SimulatorService): ...

# Interface-only stubs for the future (raise NotImplementedError):
class AppleHealthAdapter(SensorAdapter): ...
class HealthConnectAdapter(SensorAdapter): ...
class BluetoothSensorAdapter(SensorAdapter): ...
```

#### SimulatorService (Req 2)
- `select_scenario(s)`, `start()`, `pause()`, `reset()`.
- Seedable `numpy.random.default_rng(seed)` for reproducibility.
- Scenario generators:
  - **A Normal**: sample each metric from `N(baseline_mean, baseline_std)`, clipped to physiological ranges.
  - **B Gradual Deviation**: apply a slow linear drift over simulated weeks (HR ↑, HRV ↓, sleep ↓).
  - **C Rhythm Irregularity**: inject intermittent `rhythm=irregular` flags and correlated HR spikes.
- Occasionally emits `quality='missing'` samples to exercise data-quality handling.

#### AnalysisEngine (Req 3)
- `compute_baseline(readings) -> Baseline` (mean/std over a trailing window).
- `rolling_stats(series, window)` via Pandas.
- `detect(findings)` pipeline:
  - **persistent_shift**: rolling mean deviates > `k·std` from baseline for ≥ `W` windows.
  - **combination**: HR up AND HRV down simultaneously beyond thresholds.
  - **rhythm_irregularity**: density of irregular flags exceeds threshold in window.
  - **data_quality**: fraction of missing/low samples exceeds threshold → tag, do not treat as trend.
- All thresholds in `analysis_config.py` (single source), making results transparent and reproducible.
- Returns `AnomalyFinding` objects; never emits a "risk %" as validated.

#### AlertService (Req 4)
- Maps findings → one of three states (`normal`, `trend_review`, `attention`).
- Builds `explanation` from supporting values and `next_steps` text.
- Always attaches static **emergency guidance** and **experimental** label.

#### API Endpoints (Req 7)
| Method | Path                         | Purpose                                  |
|--------|------------------------------|------------------------------------------|
| GET    | `/measurements`              | Latest / ranged readings (query: metric, from, to) |
| GET    | `/trends?range=daily|weekly|monthly` | Aggregated trend series + baseline |
| POST   | `/analysis/run`              | Recompute baselines + findings           |
| GET    | `/insights`                  | Current alert state + history            |
| GET/POST | `/scenario`                | Get or set scenario (A/B/C)              |
| POST   | `/simulator/{start|pause|reset}` | Control the simulator                |
| GET    | `/health`                    | Liveness                                 |

### Frontend

#### Screens (Expo Router)
- `app/(tabs)/index.tsx` — **Dashboard**: metric cards (HR, HRV, SpO2, rhythm), activity/sleep,
  monitoring status, wearable connection badge, mini trend charts. "SIMULATED DATA" ribbon.
- `app/(tabs)/insights.tsx` — **Insights/Alerts**: current state banner, explanation, next steps,
  always-visible emergency guidance card.
- `app/(tabs)/history.tsx` — **History**: daily/weekly/monthly toggle, baseline overlay, anomaly markers, past alerts.
- `app/(tabs)/simulator.tsx` — **Simulator**: scenario picker (A/B/C), Start/Pause/Reset.
- `app/(tabs)/profile.tsx` — **Settings**: synthetic profile, data-privacy notes.

#### Shared UI
- `MetricCard`, `TrendChart`, `AlertBanner`, `EmergencyGuidanceCard`, `SimulatedDataRibbon`, `ScenarioPicker`.
- Theme tokens in `theme.ts` (dark-blue palette, spacing, typography) with AA-contrast colors.

#### Data layer
- `api/client.ts` typed wrapper; `api/types.ts` generated from OpenAPI.
- React Query hooks: `useMeasurements`, `useTrends`, `useInsights`, `useScenario`, with polling while simulator runs.

---

## Data Models (shared shapes)

```ts
type MetricType = 'hr' | 'hrv' | 'spo2' | 'rhythm' | 'activity' | 'sleep';
type AlertState = 'normal' | 'trend_review' | 'attention';

interface Reading { timestamp: string; metricType: MetricType; value: number | null;
                    quality: 'ok' | 'low' | 'missing'; isSynthetic: true; scenario: 'A'|'B'|'C'; }

interface Alert { state: AlertState; title: string; explanation: string;
                  nextSteps: string; isExperimental: true; emergencyGuidance: string; }
```

---

## Error Handling

- **Backend**: FastAPI exception handlers return structured JSON `{ error, detail }`;
  invalid scenario/range → `422`; missing resource → `404`; simulator misuse → `409`.
- **Analysis**: insufficient data → returns a `data_quality` finding, not an exception.
- **Frontend**: React Query error/loading/empty states; network failure shows a retry card;
  empty ranges show explicit empty states (Req 5.5, 1.6).

---

## Testing Strategy (Req 9)

- **Python (pytest)**: simulator determinism per scenario; baseline math; each anomaly detector;
  missing-data classification; alert-state mapping; scenario transitions; API route responses (httpx/TestClient).
- **TypeScript (Jest + RN Testing Library)**: metric/alert formatting utilities, API client parsing,
  component rendering of simulated-data labels and emergency guidance, chart data transforms.
- **Reproducibility**: fixed seed + fixed config asserts identical findings across runs (Req 3.7).
- **Fixtures**: a seeded synthetic dataset doubles as the demo's sample history.

---

## Safety & Privacy Design (Req 8)
- No credentials or API keys anywhere in the client; backend reads any config from env/local file.
- All outputs labeled experimental; emergency guidance always visible on the Insights screen.
- No third-party LLM calls in the MVP; if added later, gated behind explicit consent.
- Data stays in the local SQLite file; synthetic-only.
