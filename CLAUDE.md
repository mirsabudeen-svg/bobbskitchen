# BOBB AI Platform — CLAUDE.md

## Project Overview

BOBB AI is a multi-agent retail kiosk system that converts customer stories into personalized custom-printed apparel in real-time. A customer speaks or types a personal story; the platform generates unique artwork, recommends a product, and fulfills a physical print on-site.

**Business Context**: Kerala-based roaming retail van. 40–60 customers/day. 10–14 minutes total customer journey.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11, async) |
| Frontend | React 18 + TypeScript (tablet-optimized) |
| Database | PostgreSQL 15 |
| AI Orchestration | Anthropic Claude API (`claude-sonnet-4-6`) |
| Image Generation | fal.ai (hosted, MVP) → ComfyUI (future) |
| Real-time | WebSockets (via FastAPI) |
| ORM | SQLAlchemy 2.0 (async) + Alembic migrations |
| Validation | Pydantic v2 |

---

## Repository Layout

```
bobbskitchen/
├── backend/
│   ├── app/
│   │   ├── agents/            # Claude-powered agent implementations
│   │   │   ├── conversation.py
│   │   │   ├── design.py
│   │   │   ├── product.py
│   │   │   └── orchestrator.py
│   │   ├── api/
│   │   │   ├── sessions.py
│   │   │   ├── designs.py
│   │   │   ├── products.py
│   │   │   ├── orders.py
│   │   │   └── ws.py          # WebSocket endpoint
│   │   ├── services/
│   │   │   ├── image_gen.py   # fal.ai integration (ComfyUI adapter later)
│   │   │   ├── session_manager.py
│   │   │   └── product_recommender.py
│   │   ├── models/
│   │   │   ├── db.py          # SQLAlchemy ORM models
│   │   │   └── schemas.py     # Pydantic schemas
│   │   ├── db/
│   │   │   └── migrations/    # Alembic migration files
│   │   ├── prompts/           # Claude system prompts (text files)
│   │   └── main.py
│   ├── tests/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── screens/           # 13 tablet UI screens
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/          # API + WebSocket clients
│   │   ├── store/             # Zustand state
│   │   └── types/
│   ├── public/
│   └── package.json
│
├── docs/                      # Original product research (read-only reference)
├── CLAUDE.md
├── architecture.md
├── database_schema.md
├── api_contracts.md
└── sprint_plan.md
```

---

## Core Vertical Slice (MVP)

The single end-to-end flow to deliver first:

```
Customer Story (text/voice)
        │
        ▼
[Conversation Agent — Claude]
  Extract: themes, emotions, keywords, cultural_refs
        │
        ▼
[Design Agent — Claude]
  Translate story → image generation prompt
  Output: 4 variant prompts with style/mood
        │
        ▼
[Image Generation — fal.ai]
  Generate 4 PNG variants (1024×1024)
  Present 2×2 grid to customer
        │
        ▼
[Product Agent — Claude]
  Analyze design complexity + customer context
  Recommend top 3 products with fit scores
        │
        ▼
Customer selects product → Cart → Checkout
```

---

## Agent Design Principles

All agents use the Anthropic `tool_use` API to emit structured outputs — **never parse Claude text with regex or string matching**. Each agent defines a single tool (e.g. `submit_story`, `submit_design_strategy`, `submit_recommendations`); Claude is instructed to call it with the required JSON. The tool's `input_schema` is the authoritative contract for that agent's output.

- **Conversation Agent**: Uses `claude-sonnet-4-6`. System prompt in `prompts/conversation.txt`. Extracts structured `Story` JSON from free-form customer input. Kerala cultural themes are injected into system context.
- **Design Agent**: Uses `claude-sonnet-4-6`. Translates `Story` into a `DesignStrategy` (4 `VariantPrompt` objects, each with `prompt`, `negative_prompt`, `color_palette`, `mood`, `width`, `height`). Enforces print-safe color palettes.
- **Product Agent**: Uses `claude-haiku-4-5-20251001` (fast, cheaper). Scores product catalog against design complexity + story themes. Returns top-3 `ProductRecommendation` objects with `ScoreBreakdown`.

### Variant Styles (definitive — do not change without updating all 3 agents + frontend)

```
illustration | geometric | watercolor | minimalist
```

`photorealistic` is explicitly excluded: DTF printing has colour banding and gradient issues with photorealistic images. Kerala illustration and geometric styles produce cleaner prints.

### Pipeline Correlation

Every invocation of the AI pipeline generates a `pipeline_run_id` (UUID) at orchestrator entry. This UUID is written to:
- `agent_logs.pipeline_run_id` for every agent call in the pipeline run
- `designs.pipeline_run_id` for the design created in that run

This allows full trace reconstruction: given any `pipeline_run_id`, you can retrieve every agent call, timing, token count, and output for that single customer's generation attempt.

### Prompt Versioning

System prompt files (`prompts/*.txt`) are SHA-1 hashed at application startup. The hash is stored in `agent_logs.prompt_version` on every call. This makes it possible to determine exactly which system prompt version produced any given output, enabling regression detection and rollback attribution.

### Product Config Registry

Per-product design constraints (print dimensions, negative prompt additions, complexity range, design fit scores) are loaded at startup from `prompts/products/{product_id}.txt` into a `PRODUCT_REGISTRY` dict. Adding a new product requires only a new DB row and a new text file — no code changes.

---

## Image Generation

**MVP (hosted)**: fal.ai with `fal-ai/flux/dev` or `stable-diffusion-xl`.
- POST request with prompt → poll for completion → return image URLs.
- Images stored to local cache (`/cache/designs/{session_id}/`).

**Future (ComfyUI)**: Adapter class implementing the same `ImageGenerationService` interface. Switch via `IMAGE_GEN_PROVIDER=comfyui` env var. No application-layer code changes needed.

---

## State Machine

Session states (stored in PostgreSQL `sessions.current_state`):

```
IDLE → GREETING → LISTENING → THINKING → GENERATING → PREVIEW
                                                          ↓
                                               REFINING (optional, max 3x)
                                                          ↓
                                              PRODUCT_SELECTION → CART → CHECKOUT
                                                                             ↓
                                                                       PRODUCTION → SUCCESS
                                                                                      ↓
                                                                                     IDLE
```

Error states: `ERROR`, `HELP` — can transition to `IDLE` or prior state.

---

## Development Commands

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in ANTHROPIC_API_KEY, DATABASE_URL, FAL_API_KEY
alembic upgrade head          # run migrations
uvicorn app.main:app --reload --port 8420

# Frontend
cd frontend
npm install
npm run dev                   # Vite dev server on :3000

# Tests
cd backend && pytest -v
```

---

## Key Environment Variables

```
ANTHROPIC_API_KEY=         # Claude API key
DATABASE_URL=              # postgresql+asyncpg://user:pass@host/bobb
FAL_API_KEY=               # fal.ai API key
IMAGE_GEN_PROVIDER=fal     # fal | comfyui
COMFYUI_URL=               # http://localhost:8188 (when using local)
REDIS_URL=                 # optional, for session caching
DEBUG=true
PORT=8420
```

---

## Source of Truth for Decisions

All product specifications, Kerala cultural themes, print area constraints, design thinking research, and quality standards live in `/docs/`. Before modifying any agent prompt or product catalog data, read the relevant docs files. The docs represent validated product knowledge and must not be overridden without explicit approval.

---

## Cultural Context

BOBB operates in Kerala, India. The product designs draw heavily from Kerala cultural themes:
- **8 primary themes**: backwaters, Theyyam, kathakali, monsoon, fishing heritage, coconut palms, spice trade, temple architecture
- **Color palette**: warm gold (#E8C547), deep navy (#0A1A3F), cream (#FAF7F0), saffron (#E8833A), Kerala green (#2D6A4F)
- Designs should feel **locally authentic** while remaining commercially wearable.
- All agent prompts must include Kerala cultural context injection.

---

## What NOT to Build (MVP Scope)

- No voice/audio input in MVP (text input only; voice is Phase 2)
- No payment processing in MVP (checkout UI only, no gateway integration)
- No DTF printer integration in MVP (production queue is manual)
- No ComfyUI local inference in MVP (fal.ai only)
- No staff/admin dashboard in MVP
- No offline mode in MVP
