# HeartGuardian AI

An AI-assisted cardiovascular monitoring and early-warning **prototype**. HeartGuardian AI
demonstrates how wearable physiological data can be continuously analyzed to surface personalized
health trends and explainable, non-diagnostic alerts.

> **Experimental prototype — not a medical device.** All physiological data is **synthetic** and
> labeled experimental. The app does not diagnose conditions, makes no reliability guarantees, is
> not responsible for false alarms or missed events, and does not replace professional medical
> evaluation. Acting on any warning is solely the user's decision.

## Stack
- **Mobile:** React Native + Expo + TypeScript + Expo Router
- **Backend:** Python + FastAPI
- **Database:** SQLite (local, synthetic data)
- **Analytics:** NumPy, Pandas, scikit-learn
- **Charts:** react-native-gifted-charts

## Repository layout
```
backend/     FastAPI service (API, simulator, analysis, alerts, care-network, emergency)
mobile/      Expo React Native app (dashboard, insights, history, simulator, settings)
.kiro/specs/heartguardian-ai/   requirements.md · design.md · tasks.md  (the spec)
TEAM.md      team roles, work allocation, git workflow, and getting-started guide
```

## Quick start
See **[TEAM.md → Getting started](TEAM.md#getting-started)** for full prerequisites and steps.

Backend:
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash); use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # http://localhost:8000/docs
```

Mobile (second terminal):
```bash
cd mobile
npm install
npm start     # scan the QR code with Expo Go, or press w for web
```

## Development
This project is built with Amazon Kiro using spec-driven development. The requirements, design, and
task plan live in `.kiro/specs/heartguardian-ai/`. Work is tracked as numbered tasks in
`tasks.md`; see `TEAM.md` for ownership and the branch-per-task workflow.

## Status
Scaffolding complete (Tasks 1–3): the backend `/health` service runs and passes its smoke test, and
the Expo app launches to a dark-blue dashboard with placeholder screens. Feature implementation
(Tasks 4+) is in progress.
