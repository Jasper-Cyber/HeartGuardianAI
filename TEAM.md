# Team & Workflow — HeartGuardian AI

This file is the team's coordination guide. The single source of truth for *what to build* is
[`.kiro/specs/heartguardian-ai/tasks.md`](.kiro/specs/heartguardian-ai/tasks.md); this file says
*who* does it and *how* we work together without stepping on each other.

## Getting started

### Prerequisites
Install these once. Versions below are what the project is scaffolded against (newer minor versions are usually fine):

| Tool | Version used | Notes |
|------|--------------|-------|
| Git | 2.5+ | — |
| Python | 3.11–3.13 | `python` on Windows (there is no `python3` alias here) |
| Node.js | 20 LTS or newer | project scaffolded with Node 26 / npm 11 |
| Expo | via `npx expo` | no global install needed |
| Expo Go app | latest | on your phone, to run the mobile app without a native build |

### 1. Clone and enter the repo
```bash
git clone https://github.com/Jasper-Cyber/HeartGuardianAI.git
cd HeartGuardianAI
```

### 2. Run the backend (FastAPI)
```bash
cd backend
python -m venv .venv
# Windows (bash/Git Bash):
source .venv/Scripts/activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Verify: open http://localhost:8000/health (should return `{"status":"ok",...}`) and
http://localhost:8000/docs for the interactive API.
Run backend tests with `pytest` from the `backend/` directory.

### 3. Run the mobile app (Expo)
In a second terminal:
```bash
cd mobile
npm install
npm start          # opens Expo; scan the QR code with Expo Go, or press w for web
```
The app launches to a dark-blue Dashboard with placeholder screens and a "SIMULATED DATA" ribbon.

> The mobile app talks to the backend at `http://localhost:8000`. On a physical phone, replace
> `localhost` with your computer's LAN IP (the API base URL is configured in `mobile/api/` — Task 13).

### First task per person
Start here (full details in `tasks.md`). Open a branch per task (see Git workflow below).

| Member | Start with | Then |
|--------|-----------|------|
| Jasper-Cyber | Task 4 (SQLite schema + repository) | 5, 8, 11 |
| Raffy | Task 6 (SimulatorService) | 7, 9, 10, 12 |
| maiabrunne | Task 18 (care/settings data layer) — after Task 4 lands | 19, 20, 21, 24, 25 |
| Helenawai | Task 13 (API client + hooks) | 14, 15, 16, 17, 22, 23 |

Tasks 1–3 (scaffolding) are **already done**, so everyone is unblocked. Jasper-Cyber's Task 4 is the
next backend dependency; maiabrunne's Task 18 builds on it, so maiabrunne can begin with the provider
directory seed / mock while Task 4 is in review.

## Team

| Member | GitHub | Role (reference only — work is not limited to role) |
|--------|--------|------------------------------------------------------|
| Jasper-Cyber | `Jasper-Cyber` | Founder / project lead |
| Raffy | `Raffy` | Bio specialist |
| maiabrunne | `maiabrunne` | Data specialist 1 |
| Helenawai | `Helenawai` | Data specialist 2 |

Work is allocated to **balance coding load and avoid overlap**, not by role. Everyone writes code
across the stack as the task requires.

## Work allocation

Tasks reference the numbered list in `tasks.md`. Each person owns a set of files/folders so two
people rarely touch the same file.

### Jasper-Cyber — Backend backbone & integration (Tasks 1, 2, 4, 5, 8, 11, 28)
- Repo structure, FastAPI skeleton, SQLite schema + repository layer, seed data.
- Simulator/scenario endpoint wiring and analysis endpoints (the API surface others call).
- Coordinates the README/demo (task 28); everyone contributes their section.
- **Owns:** `backend/app/main.py`, `backend/app/db/`, `backend/app/routers/` (scenario, analysis wiring), `seed_data.py`, root `README.md`.

### Raffy — Analytics & simulation engine (Tasks 6, 7, 9, 10, 12, 26)
- SimulatorService (scenarios A/B/C), SensorAdapter + SimulatedSensorAdapter.
- AnalysisEngine: baseline, rolling stats, anomaly detectors; AlertService.
- Python test suite (task 26).
- **Owns:** `backend/app/services/{simulator,analysis,alerts}.py`, `backend/app/adapters/sensor*.py`, `backend/app/analysis_config.py`, `backend/tests/`.

### maiabrunne — Care network & emergency (full stack) (Tasks 18, 19, 20, 21, 24, 25)
- Care profile / contacts / settings data layer + provider directory seed.
- ProviderService (distance ranking) and EmergencyService + NotifierAdapter (routing, payload, simulated dispatch).
- The matching mobile screens: nearby-provider suggestions and the emergency-response flow.
- **Owns:** `backend/app/services/{provider,emergency}.py`, `backend/app/adapters/notifier*.py`, `backend/app/emergency_config.py`, `mobile/app/emergency.tsx`, `mobile/components/{ProviderSuggestionCard,NearbyProvidersSheet,EmergencyConfirmDialog,DispatchHistoryList}.tsx`.

### Helenawai — Mobile app & UI (Tasks 3, 13, 14, 15, 16, 17, 22, 23, 27)
- Expo scaffold + theme, API client + React Query hooks (the shared data layer other screens use).
- Core screens: Dashboard, Insights/Alerts, History, Simulator, Care-profile/Settings, Disclaimer.
- TypeScript test suite (task 27).
- **Owns:** `mobile/app/(tabs)/`, `mobile/app/disclaimer.tsx`, `mobile/api/`, `mobile/theme.ts`, `mobile/components/` (shared, except maiabrunne's care/emergency ones), `mobile/__tests__/`.

### Load balance (approx. coding weight)
| Member | Tasks | Notes |
|--------|-------|-------|
| Jasper-Cyber | 7 | Smaller-but-foundational tasks; also owns demo coordination |
| Raffy | 6 | Logic-heavy engine + Python tests |
| maiabrunne | 6 | Full-stack feature (backend services + 2 mobile screens) |
| Helenawai | 9 | Many screens but each is UI-focused; includes TS tests |

## Build order (dependencies)

```
Phase 0 (1–3)  scaffold          → do FIRST, ideally together (touches shared files)
Phase 1 (4–5)  DB + seed         → unblocks everything backend
Phase 2 (6–8)  simulator         ─┐
Phase 3 (9–11) analysis           ├→ backend feature-complete
Phase 4 (12)   alerts            ─┘
Phase 5 (13–17) core mobile      → build against mock data early, real API once above lands
Phase 6 (18–25) care + emergency → depends on alerts (12) + mobile data layer (13)
Phase 7 (26–28) tests + docs     → ongoing; finalize last
```

Front-end owners (Helenawai, maiabrunne) should work against **mock API responses** early so they
are never blocked waiting on the backend.

> **Unblock note:** Tasks 1–3 (scaffolding) are already done and committed — `backend/` and
> `mobile/` exist and run. All four members can start their first task now (see "First task per
> person" in Getting Started below).

## Git workflow (one branch per task)

Never commit directly to `main`.

```bash
git checkout main
git pull                                   # always start from latest
git checkout -b feat/<area>-<short-desc>   # e.g. feat/backend-measurements-endpoint
# ... code + commit ...
git push -u origin feat/<area>-<short-desc>
# open a Pull Request on GitHub → 1 review → merge
```

Branch naming: `feat/...` (new work), `fix/...` (bug fixes). Keep branches small and short-lived.
Reference the task number in the PR title, e.g. `Task 14: Dashboard screen`.

### Stay in sync (do this daily)
```bash
git checkout main && git pull
git checkout your-branch
git merge main        # pick merge OR rebase as a team and stick with it
```

## Shared files — edit carefully (conflict magnets)

These get touched by many tasks; keep edits **small and additive** so git auto-merges:
- `backend/app/main.py` (router registration) — append one line per router.
- `mobile/app/(tabs)/_layout.tsx` (tab nav) — append one tab at a time.
- `.kiro/specs/heartguardian-ai/tasks.md` (the checklist) — only check off your own task.
- Dependency files: `backend/pyproject.toml`, `mobile/package.json`.

Claim a task (check it off / assign on GitHub) **before** starting so two people don't pick the same one.

## Recommended GitHub settings (repo admin)

Configure on GitHub.com → Settings → Branches → add a ruleset for `main`:
- Require a pull request before merging (≥ 1 approval).
- Require branches to be up to date before merging.
- Block force pushes.

## Definition of done (per task)
- Code compiles / app runs; no new linter errors.
- Tests added or updated where the task calls for it; existing tests pass.
- PR reviewed and merged to `main`; the app is still runnable.
