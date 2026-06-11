# BOBB AI Platform — Architecture

## System Overview

4-tier architecture: Tablet UI ↔ FastAPI Backend ↔ AI Agents + Services ↔ Data Layer.

```
┌─────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                             │
│  React + TypeScript (Samsung Tab S9 Ultra, 2960×1848px)        │
│  • 13 screen states (IDLE → SUCCESS)                            │
│  • WebSocket client (real-time state updates)                   │
│  • REST client (session init, product catalog)                  │
│  • Touch-first UI, 60fps animations                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │  WebSocket /ws/{session_id}
                              │  REST     /api/v1/*
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  APPLICATION LAYER (FastAPI — Python 3.11)                      │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  REST API   │  │  WebSocket   │  │  Agent Orchestrator  │   │
│  │  /api/v1/   │  │  Handler     │  │  (state machine)     │   │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         └────────────────┴──────────────────────┘               │
│                          │                                       │
│  ┌───────────────────────┼──────────────────────────────┐       │
│  │           AGENTS (Claude API)                        │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │       │
│  │  │ Conversation │  │   Design     │  │  Product  │  │       │
│  │  │    Agent     │  │    Agent     │  │   Agent   │  │       │
│  │  │ (Sonnet 4.6) │  │ (Sonnet 4.6) │  │(Haiku 4.5)│  │       │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           SERVICES                                   │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │       │
│  │  │  Image Gen   │  │   Session    │  │  Product  │  │       │
│  │  │  (fal.ai)    │  │   Manager   │  │ Recommender│  │       │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                     │
│  • PostgreSQL 15 (primary store — sessions, designs, orders)   │
│  • Local filesystem cache (design images /cache/designs/)      │
│  • Optional: Redis (session hot-cache, WebSocket pub/sub)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  EXTERNAL SERVICES                                              │
│  • Anthropic API (Claude — conversation, design, product)      │
│  • fal.ai (image generation — FLUX / SDXL)                     │
│  • (Future) ComfyUI local server                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Architecture

### Conversation Agent
- **Model**: `claude-sonnet-4-6`
- **Input**: New customer text + full prior conversation history from `conversation_logs`
- **Output**: Structured `Story` JSON
- **System prompt**: `backend/app/prompts/conversation.txt`
- **Responsibilities**:
  - Extract themes, emotions, keywords from free-form story
  - Detect Kerala cultural references
  - Classify design complexity (simple / medium / complex)
  - Flag if clarification is needed (max 2 clarification turns)

**FIX ISSUE-01 — Multi-turn context threading**:

Claude has no memory between calls. Every agent call must reconstruct the full
conversation history from `conversation_logs` and pass it as a `messages` array.

```python
# Method signature (replaces the single-text version):
async def extract_story(
    self,
    new_input: str,
    session_id: str,
    prior_turns: list[ConversationTurn],  # fetched from conversation_logs by session_id
) -> Story:
    messages = []
    for turn in prior_turns:
        messages.append({"role": "user",      "content": turn.customer_input})
        if turn.agent_response:
            messages.append({"role": "assistant", "content": turn.agent_response})
    messages.append({"role": "user", "content": new_input})
    # Call Claude with full messages array
    response = await self.client.messages.create(
        model=self.model,
        system=self.system_prompt,
        messages=messages,
        ...
    )
```

`conversation_logs.agent_response` stores the exact text of any clarification
question Claude asked, so it can be replayed as an assistant turn on the next
call. Without this, the second clarification turn is incoherent.

### Design Agent
- **Model**: `claude-sonnet-4-6`
- **Input**: `Story` JSON + target product type (optional)
- **Output**: 4 image generation prompts (one per variant style)
- **System prompt**: `backend/app/prompts/design.txt`
- **Responsibilities**:
  - Translate story themes → visual design language
  - Respect product-specific print area constraints (from docs)
  - Generate 4 variant strategies: `illustration`, `geometric`, `watercolor`, `minimalist`
  - Inject Kerala cultural elements and BOBB brand color palette
  - Enforce print-safe specifications (DPI, bleed, color count)

### Product Agent
- **Model**: `claude-haiku-4-5-20251001`
- **Input**: `Story` JSON + selected design metadata
- **Output**: Top-3 product recommendations with scores and reasons
- **System prompt**: `backend/app/prompts/product.txt`
- **Responsibilities**:
  - Match design complexity/type to product print area capability
  - Score products using: design fit (40%), complexity match (30%), demographics (15%), budget (10%), inventory (5%)
  - Return ranked recommendations with mockup hints

### Agent Orchestrator
- Manages agent call sequence and context threading
- Passes `Story` from Conversation → Design → Product
- Handles retries and fallbacks
- Emits WebSocket progress events between agent calls

---

## Image Generation Service

### Interface (Abstract)

```python
class ImageGenerationService(Protocol):
    async def generate(
        self, 
        prompts: list[str],          # 4 variant prompts
        session_id: str,
        product_type: str | None,
    ) -> list[ImageResult]:
        ...
```

### fal.ai Implementation (MVP)

- Endpoint: `fal-ai/flux/dev` or `fal-ai/stable-diffusion-xl`
- 4 concurrent requests (one per variant)
- Image size: 1024×1024 (square, crop-safe)
- Stored to: `cache/designs/{session_id}/v{1-4}.png`
- Timeout: 30s per image, 60s total
- Fallback: if 1 variant fails, deliver 3; if 2+ fail → retry once then error

### ComfyUI Implementation (Future)

- Same interface, different transport (HTTP to localhost:8188)
- Workflow JSON sent to ComfyUI API
- Same output contract
- Enabled via `IMAGE_GEN_PROVIDER=comfyui`

---

## WebSocket Protocol

Single WebSocket connection per tablet session at `/ws/{session_id}`.

> **Source of truth**: `api_contracts.md` is the canonical definition for all
> WebSocket message payloads. The tables below are a summary only. In case of
> any discrepancy, `api_contracts.md` wins.

### Client → Server Message Types

| type | payload | description |
|---|---|---|
| `text_input` | `{ text: string }` | Customer story text |
| `design_select` | `{ design_id, variant_id: UUID }` | Choose design variant — UUID of design_variants row |
| `design_refine` | `{ type, value }` | Refinement pill selection |
| `product_select` | `{ product_id, size?, color, qty }` | Product selection |
| `checkout_submit` | `{ name, phone, name_tag }` | Checkout form |
| `ping` | `{}` | Keepalive |

### Server → Client Message Types

| type | payload | description |
|---|---|---|
| `state_change` | `{ state, prev_state }` | Session state transition |
| `progress` | `{ percent, substatus }` | Generation progress |
| `story_extracted` | `{ story }` | Conversation agent output |
| `design_variants_ready` | `{ design_id, variants[] }` | 4 images ready |
| `product_recommendations` | `{ recommendations[] }` | Top-3 products |
| `design_refined` | `{ image_url, refinements_left }` | Refinement complete |
| `error` | `{ code, message, recoverable }` | Error with recovery hint |
| `pong` | `{}` | Keepalive response |

---

## Session State Machine

Valid transitions only; any invalid transition raises `InvalidStateTransition` error.

```
IDLE
  └─→ GREETING                    (tap to start)

GREETING
  └─→ LISTENING                   (customer begins input)

LISTENING
  ├─→ THINKING                    (story complete, no clarification needed)
  └─→ CLARIFYING                  (agent needs more info)

CLARIFYING
  ├─→ LISTENING                   (customer answers)
  └─→ THINKING                    (enough info gathered, max 2 turns)

THINKING
  └─→ GENERATING                  (design prompt ready)

GENERATING
  └─→ PREVIEW                     (4 variants ready)

PREVIEW
  ├─→ REFINING                    (customer selects variant)
  └─→ THINKING                    ("try different" — regenerate all)

REFINING
  ├─→ GENERATING                  (apply refinement, max 3x)
  └─→ PRODUCT_SELECTION           ("perfect, move on")

PRODUCT_SELECTION
  └─→ CART                        (product selected)

CART
  ├─→ PRODUCT_SELECTION           (change selection)
  └─→ CHECKOUT                    (proceed)

CHECKOUT
  └─→ PRODUCTION                  (payment confirmed / cash)

PRODUCTION
  ├─→ SUCCESS                     (all stages complete)
  └─→ ERROR                       (printer/system failure)

SUCCESS
  └─→ IDLE                        (auto-reset after 10s or "make another")

ERROR
  ├─→ IDLE                        (abort)
  └─→ HELP                        (escalate to staff)

HELP
  └─→ IDLE                        (staff resolves)
```

---

## Frontend Architecture

### Screen Components (13 states)

```
src/screens/
├── IdleScreen.tsx           # IDLE — BOBB logo, pulsing ring
├── GreetingScreen.tsx       # GREETING — wave animation
├── ListeningScreen.tsx      # LISTENING — text input + waveform
├── ClarifyingScreen.tsx     # CLARIFYING — Q&A cards
├── ThinkingScreen.tsx       # THINKING — spinner
├── GeneratingScreen.tsx     # GENERATING — progress bar + substatus
├── PreviewScreen.tsx        # PREVIEW — 2×2 variant grid
├── RefiningScreen.tsx       # REFINING — 6 refinement pills
├── ProductSelectionScreen.tsx # PRODUCT_SELECTION — 3 product cards
├── CartScreen.tsx           # CART — item list + discounts
├── CheckoutScreen.tsx       # CHECKOUT — form + payment options
├── ProductionScreen.tsx     # PRODUCTION — 4-stage progress
└── SuccessScreen.tsx        # SUCCESS — checkmark + QR
```

### State Management

- **Zustand** for global session state
- `useWebSocket` hook manages connection, reconnect, and message dispatch
- Screen routing driven purely by `session.currentState`

### Design Tokens (BOBB Brand)

```ts
const tokens = {
  colors: {
    gold:    '#E8C547',
    navy:    '#0A1A3F',
    cream:   '#FAF7F0',
    saffron: '#E8833A',
    green:   '#2D6A4F',
  },
  typography: {
    display: 'Playfair Display',
    body:    'Inter',
  },
  spacing: { base: 8 },  // 8px grid
  radius:  { card: 16, button: 12 },
}
```

---

## Deployment (MVP)

```
Windows PC (RTX 3060, 16GB RAM) — LAN IP e.g. 192.168.1.10
├── PostgreSQL 15 (local, port 5432)
├── FastAPI backend (port 8420, uvicorn --workers 1)  ← single worker required
├── React frontend (port 3000, served via nginx or vite preview)
└── (optional) Redis (port 6379)

Samsung Tab S9 Ultra
└── Browser pointing to http://192.168.1.10:3000
    VITE_API_BASE_URL=http://192.168.1.10:8420  (set in frontend/.env)
```

**Constraints (document in CLAUDE.md)**:
- Backend **must** run as `--workers 1`. The in-process `active_sessions` WebSocket
  registry is not shared across worker processes. Multi-worker requires Redis (Phase 2).
- Never use `localhost` in any client-side URL. Configure `VITE_API_BASE_URL` in the
  frontend `.env` file with the PC's actual LAN IP.
- `cache/designs/` is local filesystem. Containerised deploys must mount it as a
  persistent volume. Object storage migration is a Phase 2 concern.

Future: Docker Compose wrapping all services for easier deployment.
