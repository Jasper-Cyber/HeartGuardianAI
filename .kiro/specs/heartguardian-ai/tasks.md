# Implementation Plan — HeartGuardian AI

Each phase leaves the app runnable. Check off tasks as they are completed.

## Phase 0 — Project scaffolding

- [ ] 1. Initialize repository structure
  - Create `backend/` (FastAPI) and `mobile/` (Expo) folders and root `README.md`.
  - Add root `.gitignore` (Python, Node, Expo, SQLite db files, `.env`).
  - _Requirements: 7, 8_

- [ ] 2. Scaffold FastAPI backend skeleton
  - Create `backend/pyproject.toml` (fastapi, uvicorn, sqlalchemy, numpy, pandas, scikit-learn, pytest, httpx).
  - Add `backend/app/main.py` with `/health` and CORS for the Expo dev client.
  - _Requirements: 7.1, 7.5_

- [ ] 3. Scaffold Expo mobile app skeleton
  - Create Expo + TypeScript + Expo Router app in `mobile/` with tab layout and placeholder screens.
  - Add `theme.ts` dark-blue token set and a `SimulatedDataRibbon` placeholder.
  - _Requirements: 1.7, 8.5_

## Phase 1 — Data layer & SQLite

- [ ] 4. Implement SQLite schema and repository layer
  - Create schema/migrations for `users`, `measurements`, `baselines`, `anomaly_findings`, `alerts`, `sim_state`.
  - Implement repository functions (insert/query readings, upsert baseline, store findings/alerts, read/update sim_state).
  - _Requirements: 7.2, 7.3, 2.9_

- [ ] 5. Seed synthetic sample history
  - Add a `seed_data.py` script that generates a labeled synthetic dataset for demos.
  - _Requirements: 5.4, 8.4_

## Phase 2 — Simulator

- [ ] 6. Implement SimulatorService with seedable RNG
  - Scenario A (Normal), B (Gradual Deviation), C (Rhythm Irregularity) generators; occasional missing/low-quality samples.
  - Start / Pause / Reset / Scenario-select operations persisted to `sim_state`.
  - _Requirements: 2.1–2.9_

- [ ] 7. Implement SensorAdapter interface + SimulatedSensorAdapter
  - Define `SensorAdapter` protocol; implement `SimulatedSensorAdapter`.
  - Add interface-only `AppleHealthAdapter`, `HealthConnectAdapter`, `BluetoothSensorAdapter` stubs.
  - _Requirements: 6.1–6.4_

- [ ] 8. Wire simulator + scenario endpoints
  - `GET/POST /scenario`, `POST /simulator/{start|pause|reset}`, `GET /measurements`.
  - _Requirements: 2.6, 7.1, 7.4_

## Phase 3 — Analysis engine

- [ ] 9. Implement baseline + rolling statistics
  - `compute_baseline`, `rolling_stats`; persist baselines.
  - _Requirements: 3.1, 3.2_

- [ ] 10. Implement anomaly detectors
  - persistent_shift, combination (HR↑ & HRV↓), rhythm_irregularity, data_quality.
  - Thresholds centralized in `analysis_config.py`; reproducible outputs.
  - _Requirements: 3.3–3.8_

- [ ] 11. Expose analysis endpoints
  - `POST /analysis/run`, `GET /trends?range=daily|weekly|monthly`.
  - _Requirements: 7.1, 5.1, 5.2, 5.3_

## Phase 4 — Alerts

- [ ] 12. Implement AlertService
  - Map findings → `normal | trend_review | attention`; build explanation + next steps.
  - Always attach emergency guidance and experimental label; expose `GET /insights`.
  - _Requirements: 4.1–4.5_

## Phase 5 — Mobile UI

- [ ] 13. API client + React Query hooks
  - Typed `api/client.ts`, `api/types.ts`; hooks with polling while simulator runs.
  - _Requirements: 7.5, 1.1_

- [ ] 14. Dashboard screen
  - Metric cards (HR, HRV, SpO2, rhythm), activity/sleep, monitoring status, wearable badge, mini trends.
  - Always-visible simulated-data ribbon; explicit no-data state.
  - _Requirements: 1.1–1.7_

- [ ] 15. Insights/Alerts screen
  - State banner, explanation, next steps, emergency guidance card, experimental label.
  - _Requirements: 4.1–4.5_

- [ ] 16. History screen
  - Daily/weekly/monthly toggle, baseline overlay, anomaly markers, past alerts, empty states.
  - _Requirements: 5.1–5.5_

- [ ] 17. Simulator screen
  - Scenario picker (A/B/C) + Start/Pause/Reset wired to backend.
  - _Requirements: 2.6_

## Phase 6 — Tests & docs

- [ ] 18. Python tests (pytest)
  - Simulator determinism, baseline math, each detector, missing-data, alert mapping, scenario transitions, API routes.
  - _Requirements: 9.1, 9.2_

- [ ] 19. TypeScript tests (Jest + RN Testing Library)
  - Formatting utils, API parsing, rendering of labels/emergency guidance, chart transforms.
  - _Requirements: 9.1, 9.2_

- [ ] 20. README, demo script, screenshots
  - Install/config/run for backend and mobile; demo walkthrough; screenshot references.
  - Verify demo runs with no real sensors or paid APIs.
  - _Requirements: 9.3, 9.4, 9.5_
```
