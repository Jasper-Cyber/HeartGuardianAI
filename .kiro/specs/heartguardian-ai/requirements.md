# Requirements Document — HeartGuardian AI

## Introduction

HeartGuardian AI is a cross-platform mobile application prototype that demonstrates how
wearable physiological data can be continuously analyzed to identify personalized health
trends and provide explainable, non-diagnostic alerts. It is a **hackathon prototype**, not
a clinically validated medical device. All physiological data in the MVP is **synthetic**
and must be clearly labeled as experimental.

The system is composed of:
- An Expo / React Native (TypeScript) mobile client with a dark-blue healthcare UI.
- A FastAPI (Python) backend exposing measurement, trend, analysis, insight, and scenario endpoints.
- A SQLite datastore for synthetic time-series measurements, baselines, anomalies, and alerts.
- A physiological data simulator with three selectable scenarios.
- A transparent, configurable anomaly-detection engine built on NumPy / Pandas / Scikit-learn.

### Non-Goals
- No hardware manufacturing.
- No clinically validated disease prediction or diagnosis.
- No collection or transmission of real patient data.
- No arbitrary numeric score presented as a validated cardiovascular risk.

---

## Glossary

- **Reading / Measurement**: A single timestamped physiological sample (HR, HRV, SpO2, etc.).
- **Baseline**: A per-metric personal reference learned from historical readings.
- **Deviation**: How far a current rolling statistic sits from the baseline.
- **Anomaly finding**: A structured record describing a detected deviation or unusual signal combination.
- **Alert**: A user-facing message derived from findings, with explanation and next steps.
- **Scenario**: A simulator mode (Normal, Gradual Deviation, Rhythm Irregularity).

---

## Requirements

### Requirement 1 — Mobile Dashboard

**User Story:** As a user, I want a modern dashboard that shows my current cardiovascular
metrics and trends at a glance, so that I can understand my status quickly.

#### Acceptance Criteria
1. WHEN the dashboard loads THEN the system SHALL display current heart rate (bpm),
   heart rate variability (ms), blood oxygen saturation (%), and a simulated heart rhythm status.
2. WHEN the dashboard loads THEN the system SHALL display daily activity and sleep indicators.
3. WHEN the dashboard loads THEN the system SHALL display historical trend charts for each primary metric.
4. WHEN the dashboard loads THEN the system SHALL display a personalized monitoring status and the wearable connection status.
5. WHERE any value originates from the simulator THE system SHALL visibly label it as simulated/experimental data.
6. WHEN metric data is unavailable THEN the system SHALL show an explicit "no data / low quality" state rather than a misleading value.
7. THE dashboard SHALL use a dark-blue healthcare theme with accessible color contrast (WCAG AA for text) and clear typography.

### Requirement 2 — Wearable Data Simulator

**User Story:** As a demonstrator, I want to generate realistic synthetic physiological data
under different scenarios, so that I can show the app's behavior without real hardware.

#### Acceptance Criteria
1. THE simulator SHALL produce timestamped readings for HR, HRV, SpO2, rhythm flag, activity, and sleep.
2. THE simulator SHALL provide three scenarios: Normal (A), Gradual Deviation (B), and Rhythm Irregularity (C).
3. WHEN Scenario A is active THEN measurements SHALL fluctuate within a simulated personal baseline.
4. WHEN Scenario B is active THEN resting HR SHALL trend upward, HRV SHALL trend downward, and sleep duration SHALL decline over simulated weeks.
5. WHEN Scenario C is active THEN the simulator SHALL inject a synthetic irregular-rhythm pattern.
6. THE simulator SHALL expose Start, Pause, Reset, and Scenario Selection controls via the API and UI.
7. WHEN Reset is invoked THEN the simulator SHALL clear generated session data and return to the selected scenario's start state.
8. THE simulator SHALL use a seedable random generator so runs are reproducible.
9. ALL simulated measurements SHALL be stored and labeled as synthetic.

### Requirement 3 — Personalized AI Analysis

**User Story:** As a user, I want the app to learn what is normal for me and flag meaningful
changes, so that alerts are personalized rather than generic.

#### Acceptance Criteria
1. THE analysis engine SHALL compute a per-metric baseline from historical measurements.
2. THE engine SHALL compute rolling statistics (mean, std, trend) and deviations from baseline.
3. THE engine SHALL detect persistent changes (sustained over a configurable window) and unusual combinations of signals.
4. WHEN data is missing or low quality THEN the engine SHALL classify it as a data-quality issue rather than a physiological trend.
5. THE engine SHALL output structured anomaly findings (metric, type, window, severity-band, supporting values).
6. THE engine SHALL use transparent, configurable demonstration thresholds stored in a single config location.
7. THE engine SHALL produce reproducible results for a fixed input dataset and config.
8. THE engine SHALL NOT present any numeric score as a clinically validated cardiovascular risk.

### Requirement 4 — AI Insights and Alerts

**User Story:** As a user, I want clear, explainable alerts and emergency guidance, so that I
know what the data means and what to do next.

#### Acceptance Criteria
1. THE system SHALL support three interface states: Normal monitoring, Trend review recommended, and Potentially concerning measurement requiring further assessment.
2. WHEN an alert is shown THEN it SHALL explain the supporting data and indicate appropriate next steps.
3. THE system SHALL always display symptom-based emergency guidance instructing users to contact emergency services for possible heart attack or stroke symptoms, regardless of wearable readings.
4. THE system SHALL NOT claim to diagnose arrhythmia, heart attack, or stroke.
5. EVERY alert SHALL carry an "experimental / not medical advice" label.

### Requirement 5 — Historical Data and Visualization

**User Story:** As a user, I want to review my history across time ranges, so that I can see
how my metrics and baselines evolve.

#### Acceptance Criteria
1. THE system SHALL let users view daily, weekly, and monthly trends.
2. THE system SHALL display individual physiological baselines alongside trends.
3. THE system SHALL display detected anomalies and historical alerts.
4. THE system SHALL ship with sample historical data for demonstrations.
5. WHEN a time range has no data THEN the system SHALL display an explicit empty state.

### Requirement 6 — Device Integration Architecture

**User Story:** As a developer, I want a pluggable sensor interface, so that future adapters
can be added without rewriting the app.

#### Acceptance Criteria
1. THE system SHALL define a SensorAdapter interface.
2. THE system SHALL implement SimulatedSensorAdapter.
3. THE system SHALL define (interface-only, future) AppleHealthAdapter, HealthConnectAdapter, and BluetoothSensorAdapter.
4. THE MVP SHALL function fully without real wearable hardware.

### Requirement 7 — Backend and Data Storage

**User Story:** As the mobile client, I need backend endpoints and persistent storage, so
that data and analysis are served consistently.

#### Acceptance Criteria
1. THE backend SHALL expose endpoints to read measurements, retrieve historical trends, run anomaly analysis, retrieve insights, and select simulation scenarios.
2. THE backend SHALL persist synthetic data in SQLite.
3. THE backend SHALL NOT store real patient information.
4. THE backend SHALL return explicit error responses for invalid scenario or range requests.
5. THE backend SHALL expose an OpenAPI schema (FastAPI default) for the client.

### Requirement 8 — Privacy and Safety

**User Story:** As a user, I want my data handled safely and outputs clearly labeled, so that
I am not misled about the prototype's capabilities.

#### Acceptance Criteria
1. THE system SHALL store data locally when practical.
2. THE system SHALL NOT contain hardcoded credentials.
3. THE mobile application SHALL NOT embed API keys.
4. THE system SHALL use synthetic data for demonstration.
5. THE system SHALL label all medical outputs as experimental.
6. THE system SHALL NOT send real health data to third-party LLM services without consent and safeguards.
7. THE system SHALL make clear that alerts do not replace medical evaluation.

### Requirement 9 — Testing and Documentation

**User Story:** As a maintainer, I want automated tests and clear docs, so that the demo is
reproducible and the code is trustworthy.

#### Acceptance Criteria
1. THE project SHALL include tests for simulator behavior, baseline calculations, anomaly detection, missing-data handling, alert generation, API responses, and scenario transitions.
2. THE project SHALL include TypeScript tests for client logic and Python tests for backend/analytics.
3. THE project SHALL include a README with installation, configuration, and run instructions.
4. THE project SHALL include a short demonstration script and screenshot references.
5. WHEN the documented steps are followed THEN the demo SHALL run without real sensors or paid APIs.

---

## Acceptance (Project-Level)
- The mobile application launches successfully.
- Users can switch among all three scenarios.
- Simulated metrics and charts update correctly.
- The anomaly detector produces reproducible results.
- Alerts include understandable explanations.
- The demo works without real sensors or paid APIs.
- Automated tests pass.
- The README explains how to reproduce the demonstration.
- The interface clearly distinguishes simulated data from real medical measurements.
