# BOBB AI Platform

Multi-agent retail kiosk that converts customer stories into personalized custom-printed apparel in real-time. A customer types a personal story; the platform generates unique Kerala-themed artwork, recommends a product, and queues a DTF print job — all within a 14-minute customer journey.

**Stack**: FastAPI · React 18 + TypeScript · PostgreSQL 15 · Anthropic Claude · fal.ai · WebSockets · APScheduler

---

## Quick Start

### One command (Docker)

```bash
cp backend/.env.example .env
# Edit .env — fill in ANTHROPIC_API_KEY and FAL_API_KEY at minimum
docker compose up
```

| Service   | URL                          |
|-----------|------------------------------|
| App (nginx) | http://localhost            |
| Backend API | http://localhost/api/v1     |
| Health      | http://localhost/health     |
| Staff queue | http://localhost/staff      |
| Analytics   | http://localhost/analytics  |

On first boot: migrations run automatically, then the app starts.

---

### Local development

**Backend**

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in DATABASE_URL, ANTHROPIC_API_KEY, FAL_API_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8420
```

**Frontend**

```bash
cd frontend
npm install
# For local dev, the Vite proxy (vite.config.ts) forwards /api and /ws to localhost:8420
npm run dev               # http://localhost:3000
```

**Tests**

```bash
cd backend && pytest -v
cd frontend && npm run type-check && npm run lint
```

---

## Environment Variables

Copy `backend/.env.example` to `.env` in the repo root (Docker reads it) and to `backend/.env` (local dev).

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key (story + design agents) |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host/bobb` |
| `FAL_API_KEY` | Yes* | fal.ai key for image generation (*mock used if unset) |
| `IMAGE_GEN_PROVIDER` | No | `fal` (default) or `comfyui` |
| `TWILIO_ACCOUNT_SID` | No | WhatsApp delivery — leave blank to disable |
| `TWILIO_AUTH_TOKEN` | No | |
| `TWILIO_WHATSAPP_FROM` | No | Sender number e.g. `whatsapp:+14155238886` |
| `TWILIO_TEMPLATE_SID_EN` | No | Approved Meta template SID (English) |
| `TWILIO_TEMPLATE_SID_ML` | No | Approved Meta template SID (Malayalam) |
| `PUBLIC_MEDIA_BASE_URL` | No | Public HTTPS base URL for WhatsApp image links |
| `DEBUG` | No | `false` in production |
| `CACHE_DIR` | No | Path for generated images (default: `cache/designs`) |
| `PORT` | No | Backend port (default: `8420`) |

---

## Architecture

```
Customer Story (text)
        │
        ▼
[Conversation Agent — claude-sonnet-4-6]
  Extracts: themes, emotions, keywords, Kerala cultural refs
        │
        ▼
[Design Agent — claude-sonnet-4-6]
  Generates 4 variant prompts (illustration, geometric, watercolor, minimalist)
        │
        ▼
[Image Generation — fal.ai flux/dev]
  4 PNG variants (1024×1024), cached to /cache/designs/{session_id}/
        │
        ▼
[Product Agent — claude-haiku-4-5-20251001]
  Scores catalog → top-3 recommendations with fit scores
        │
        ▼
Customer selects → Cart → Order placed → Staff prints → WhatsApp delivery
```

**Real-time**: WebSocket at `/ws/{session_id}` pushes state changes and generation progress to the tablet UI.

**Analytics**: Event stream (`analytics_events`) with nightly pre-aggregation (`analytics_daily`). Dashboard at `/analytics`.

---

## Key Constraints

- **Single worker required** (`--workers 1`): the WebSocket active-sessions registry is an in-process dict. Adding workers would break WS routing.
- **Monetary values in paise** (integer): ₹1 = 100 paise. Never store rupees as floats.
- **DTF print styles**: `illustration | geometric | watercolor | minimalist` only. `photorealistic` is excluded — colour banding on DTF film.
- **WhatsApp delivery is fire-and-log**: the HTTP response never waits on Twilio. Status always logged to `whatsapp_logs`.

---

## Staff Interfaces

Both are PIN-protected (same PIN gate).

- **`/staff`** — Order queue: view pending/printing/ready orders, update status, record payment, look up orders by short ref (B-001…B-060), daily reconciliation.
- **`/analytics`** — Four panels: Today Live, 14-day Trend, Product Intelligence, Operational latency. Auto-refreshes every 5 minutes. `POST /api/v1/analytics/rebuild` triggers a manual daily summary rebuild after downtime.

---

## API Summary

```
POST   /api/v1/sessions                          Create session
GET    /api/v1/sessions/{id}                     Get session state
POST   /api/v1/sessions/{id}/abandon             Mark abandoned

POST   /api/v1/sessions/{id}/story               Extract Story from text (Claude)
POST   /api/v1/sessions/{id}/design              Generate DesignStrategy (Claude)
POST   /api/v1/sessions/{id}/generate            Generate 4 image variants (fal.ai)
POST   /api/v1/sessions/{id}/recommendations     Product recommendations (Claude)

GET    /api/v1/products                          Product catalog
GET    /api/v1/designs/{id}                      Design + variants
PATCH  /api/v1/designs/{id}/variants/{vid}/select Mark variant selected

POST   /api/v1/orders                            Place order
GET    /api/v1/orders                            List orders (staff)
GET    /api/v1/orders/{id}                       Get order
PATCH  /api/v1/orders/{id}/status                Update order status
PATCH  /api/v1/orders/{id}/payment               Record payment
GET    /api/v1/orders/{id}/whatsapp-log          WhatsApp delivery log
POST   /api/v1/whatsapp/retry/{id}               Retry WhatsApp send
GET    /api/v1/orders/lookup?ref=B-001           Look up by short ref
GET    /api/v1/orders/reconciliation?date=…      Daily reconciliation

GET    /api/v1/analytics/today                   Live today stats
GET    /api/v1/analytics/daily?days=14           14-day daily summaries
GET    /api/v1/analytics/product?days=14         Style + product intelligence
GET    /api/v1/analytics/funnel?days=14          Conversion funnel
GET    /api/v1/analytics/hourly                  Hourly order heatmap
POST   /api/v1/analytics/rebuild                 Trigger manual rebuild

WS     /ws/{session_id}                          Real-time pipeline events

GET    /health                                   Liveness check
```

---

## Database Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration after changing models/db.py
alembic revision --autogenerate -m "describe_change"
```

Migration chain: `f0d86e4e7bcc` → `a3f5c8e2b1d4` → `b7d2e9f4c1a8` → `c9e1f2a3b4d5`

---

## Project Layout

```
bobbskitchen/
├── backend/
│   ├── app/
│   │   ├── agents/          # Claude-powered agents (conversation, design, product)
│   │   ├── api/             # FastAPI routers
│   │   ├── core/            # Settings, logging
│   │   ├── db/              # Engine, session factory, Alembic migrations
│   │   ├── models/          # SQLAlchemy ORM + Pydantic schemas
│   │   ├── prompts/         # Agent system prompts (SHA-1 versioned)
│   │   ├── providers/       # Anthropic SDK wrapper
│   │   └── services/        # image_gen, analytics, whatsapp, scheduler, …
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── screens/         # 13 tablet UI screens + staff + analytics
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/        # API + WebSocket clients
│   │   ├── store/           # Zustand session state
│   │   └── types/
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
└── CLAUDE.md
```
