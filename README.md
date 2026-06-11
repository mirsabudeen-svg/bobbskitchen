# BOBB AI Platform

Multi-agent retail kiosk that converts customer stories into personalized custom-printed apparel in real-time. See `CLAUDE.md`, `architecture.md`, `database_schema.md`, `api_contracts.md`, and `sprint_plan.md` for full specifications.

## Quick Start

### Docker (everything)

```bash
docker-compose up
# Backend:  http://localhost:8420/health
# Frontend: http://localhost:3000
```

### Backend (local)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in DATABASE_URL etc.
alembic upgrade head
uvicorn app.main:app --reload --port 8420   # production: add --workers 1 (required)
```

### Frontend (local)

```bash
cd frontend
npm install
cp .env.example .env          # set VITE_API_BASE_URL to the PC's LAN IP — never localhost
npm run dev                   # Vite dev server on :3000
```

### Tests / Checks

```bash
cd backend && pytest -v && ruff check app tests && mypy app tests
cd frontend && npm run type-check && npm run lint
```

## Notes

- Backend **must** run single-worker (`--workers 1`): the WebSocket registry is an in-process dict.
- Monetary values are stored in **paise** (integer). ₹1 = 100 paise.
- Sprint 0 status: scaffold only — all AI agents, image generation, and checkout are stubbed.
