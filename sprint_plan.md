# BOBB AI Platform — Sprint Plan

**Goal**: Working vertical slice: Story → Design → Artwork → Product Recommendation  
**Stack**: FastAPI · React + TypeScript · PostgreSQL · Anthropic API · fal.ai  
**Methodology**: 1-week sprints, each ending with a runnable demo checkpoint

---

## Milestones

| Milestone | Sprint | Deliverable |
|---|---|---|
| M0 | Pre-work | Repo scaffold, env, CI |
| M1 | Sprint 1 | Backend skeleton + DB + health API |
| M2 | Sprint 2 | Conversation Agent (Story extraction) |
| M3 | Sprint 3 | Design Agent + Image Generation (fal.ai) |
| M4 | Sprint 4 | Product Agent + Recommendations |
| M5 | Sprint 5 | WebSocket orchestration + state machine |
| M6 | Sprint 6 | React tablet UI — core screens |
| M7 | Sprint 7 | Integration: full vertical slice E2E |
| M8 | Sprint 8 | Cart, Checkout, Production tracking UI |
| M9 | Sprint 9 | Polish, error handling, performance |

---

## Sprint 0 — Scaffold & Infra (Day 1–2, pre-sprint)

**Goal**: Runnable empty project. `GET /health` returns 200.

### Backend
- [ ] Create `backend/` directory with FastAPI skeleton
- [ ] `requirements.txt` with all dependencies:
  - `fastapi`, `uvicorn`, `pydantic>=2`, `sqlalchemy[asyncio]`, `asyncpg`
  - `alembic`, `anthropic`, `httpx`, `python-dotenv`, `websockets`
- [ ] `.env.example` with all variables documented
- [ ] PostgreSQL connection via SQLAlchemy async engine
- [ ] Alembic initialized; first migration creates all tables from `database_schema.md`
- [ ] `GET /api/v1/health` endpoint checking DB + Anthropic API + fal.ai reachability
- [ ] CORS middleware (allow all for LAN dev)
- [ ] Static file mount for `/cache/designs/`
- [ ] Pytest configured; 1 smoke test passes

### Frontend
- [ ] Vite + React + TypeScript scaffold (`npm create vite@latest`)
- [ ] Tailwind CSS configured with BOBB design tokens
- [ ] `src/types/` with TypeScript types mirroring Pydantic schemas
- [ ] `src/services/api.ts` — typed REST client (axios or fetch)
- [ ] `src/services/ws.ts` — WebSocket client with reconnect logic
- [ ] `src/store/session.ts` — Zustand store for session state
- [ ] Root router: renders screen component based on `session.currentState`

### Infra
- [ ] Git branch `claude/inspiring-albattani-ladj5g` confirmed
- [ ] `docker-compose.yml` with PostgreSQL service (for local dev)
- [ ] README with setup instructions

**Done when**: `uvicorn app.main:app --reload` starts, `GET /health` returns `{"status":"healthy"}`, `npm run dev` shows blank BOBB-branded screen.

---

## Sprint 1 — Database + Session API (Days 3–5)

**Goal**: Full session CRUD. State machine transitions validated server-side.

### Backend
- [ ] SQLAlchemy ORM models for all tables (`backend/app/models/db.py`)
- [ ] Pydantic schemas for all entities (`backend/app/models/schemas.py`)
- [ ] `SessionState` enum + `STATE_TRANSITIONS` dict (valid next-states per state)
- [ ] `SessionManager` service:
  - `create_session()` → creates DB row, returns session dict
  - `get_session(id)` → fetch with 404 handling
  - `transition_state(id, new_state)` → validates transition, updates DB, raises `InvalidStateTransition` if illegal
- [ ] REST routes:
  - `POST /api/v1/sessions`
  - `GET /api/v1/sessions/{id}`
  - `POST /api/v1/sessions/{id}/abandon`
- [ ] Inventory seed script: inserts 10 products from docs product catalog
- [ ] `GET /api/v1/products` endpoint

### Tests
- [ ] `test_sessions.py`: create, get, valid transition, invalid transition
- [ ] `test_inventory.py`: seed + list

**Done when**: All session CRUD endpoints work, invalid state transitions return 422, product catalog returns 10 items.

---

## Sprint 2 — Conversation Agent (Days 6–9)

**Goal**: Submit story text → receive structured `Story` JSON from Claude.

### Backend
- [ ] `backend/app/prompts/conversation.txt` — system prompt for Conversation Agent:
  - Context: BOBB retail kiosk, Kerala cultural themes
  - Kerala themes reference table injected (from docs)
  - Output: strict JSON schema for `Story`
  - Handles: short inputs, unclear inputs, clarification detection
- [ ] `ConversationAgent` class in `backend/app/agents/conversation.py`:
  - `extract_story(text: str, session_id: str) -> Story`
  - Uses `anthropic` SDK with `claude-sonnet-4-6`
  - Structured output via `response_format` or prompt-enforced JSON
  - Logs to `agent_logs` table
  - Handles `anthropic.APIError` with retry (1 retry, then raise)
- [ ] `POST /api/v1/sessions/{id}/story` REST endpoint
- [ ] State transition: `listening` → `thinking` on success
- [ ] State transition: `listening` → `clarifying` if `needs_clarification=true`

### Tests
- [ ] `test_conversation_agent.py`:
  - Mock Anthropic API with `pytest-mock`
  - Test story extraction with Kerala-themed input
  - Test clarification detection
  - Test empty/invalid input handling

**Done when**: POST `/story` with "I love the beaches of Kannur" returns structured Story JSON with `themes: ["beach", "Kannur"]` and cultural refs detected.

---

## Sprint 3 — Design Agent + Image Generation (Days 10–14)

**Goal**: Story → 4 design image variants displayed.

### Backend — Design Agent
- [ ] `backend/app/prompts/design.txt` — system prompt for Design Agent:
  - Input: Story JSON
  - Output: 4 variant objects each with `style`, `prompt_used`, `mood`, `color_palette`
  - Enforces print constraints (DPI, color count, bleed from docs)
  - Kerala cultural elements injected per design
  - BOBB brand color palette enforced
- [ ] `DesignAgent` class in `backend/app/agents/design.py`:
  - `generate_prompts(story: Story, session_id: str) -> list[VariantPrompt]`
  - Returns 4 prompts: illustration, geometric, watercolor, minimalist
  - Also handles refinement: `apply_refinement(prompt, type, value) -> str`
  - Logs to `agent_logs`

### Backend — Image Generation
- [ ] `ImageGenerationService` abstract interface (Protocol class)
- [ ] `FalAIImageService` implementation:
  - `generate(prompts: list[str], session_id: str) -> list[ImageResult]`
  - 4 concurrent `httpx.AsyncClient` requests to fal.ai
  - Poll for completion (fal.ai async mode)
  - Download images, save to `cache/designs/{session_id}/v{1-4}.png`
  - Timeout: 30s per image
  - Partial failure: return what succeeded (min 2 variants required)
- [ ] Factory function: `get_image_service()` reads `IMAGE_GEN_PROVIDER` env var
- [ ] `designs` + `design_variants` DB rows created after generation
- [ ] `GET /api/v1/sessions/{id}/designs/latest` endpoint
- [ ] `POST /api/v1/sessions/{id}/designs/{id}/select` endpoint
- [ ] `POST /api/v1/sessions/{id}/designs/{id}/refine` endpoint

### Tests
- [ ] `test_design_agent.py`: mock Claude, verify 4 prompts returned with correct styles
- [ ] `test_image_gen.py`: mock fal.ai responses, verify images saved to cache

**Done when**: Full backend flow works: story in → Claude generates 4 prompts → fal.ai generates 4 images → images accessible at `/cache/designs/{sess}/v1.png`.

---

## Sprint 4 — Product Agent + Recommendations (Days 15–18)

**Goal**: Locked design → top-3 product recommendations from Claude.

### Backend
- [ ] `backend/app/prompts/product.txt` — system prompt for Product Agent:
  - Input: Story + design metadata (style, complexity, cultural_refs)
  - Full product catalog injected as context
  - Scoring factors from docs: design fit (40%), complexity (30%), demographics (15%), budget (10%), inventory (5%)
  - Output: JSON array of top-3 recommendations
- [ ] `ProductAgent` class in `backend/app/agents/product.py`:
  - `recommend(story: Story, design_metadata: dict, session_id: str) -> list[ProductRecommendation]`
  - Uses `claude-haiku-4-5-20251001` (fast, cheaper for this task)
  - Falls back to rule-based scorer if Claude fails
- [ ] Rule-based `ProductRecommender` fallback in `backend/app/services/product_recommender.py` (from docs algorithm)
- [ ] `product_recommendations` DB row saved
- [ ] `POST /api/v1/sessions/{id}/recommendations` endpoint
- [ ] State transition: `refining` → `product_selection` on design accept

### Tests
- [ ] `test_product_agent.py`: mock Claude, verify 3 recommendations with scores
- [ ] `test_product_recommender.py`: rule-based fallback with various story/design combos

**Done when**: POST `/recommendations` returns 3 ranked products with fit scores and human-readable reasons.

---

## Sprint 5 — WebSocket Orchestrator (Days 19–23)

**Goal**: Single WebSocket connection drives the full Story → Design → Artwork → Recommendations flow in real-time.

### Backend
- [ ] `AgentOrchestrator` in `backend/app/agents/orchestrator.py`:
  - Manages the full multi-agent pipeline sequence
  - Takes WebSocket send function to emit progress events
  - `run_story_pipeline(text, session_id, ws_send)`:
    1. Emit `state_change: thinking`
    2. Call `ConversationAgent.extract_story()` → emit `story_extracted`
    3. Emit `state_change: generating`, `progress: 0%`
    4. Call `DesignAgent.generate_prompts()` → emit `progress: 25%`
    5. Call `ImageGenerationService.generate()` with progress callbacks → emit `progress: 25-90%`
    6. Save to DB → emit `design_variants_ready`
    7. Emit `state_change: preview`
- [ ] WebSocket endpoint `ws://host/ws/{session_id}` in `backend/app/api/ws.py`:
  - Connection lifecycle (accept, active sessions dict, disconnect cleanup)
  - Message routing to handlers by `type` field
  - Handler for each client message type
  - `text_input` → `orchestrator.run_story_pipeline()`
  - `design_select` → `session.transition(REFINING)`, save selection
  - `design_refine` → `design_agent.apply_refinement()` + `image_gen.generate_single()`
  - `design_accept` → lock design, `product_agent.recommend()`, emit `product_recommendations`
  - `regenerate` → `session.transition(THINKING)`, re-run pipeline
  - `ping` → `pong`
- [ ] Global error handler: catch all agent/service errors, emit `error` message, transition to `ERROR` state

### Tests
- [ ] `test_ws.py`: use `fastapi.testclient.TestClient` WebSocket support
  - Happy path: text → story → variants → select → accept → recommendations
  - Error path: mock image gen failure → error message received

**Done when**: Connect WebSocket, send `text_input`, receive: `story_extracted` → `progress` (4x) → `design_variants_ready` → send `design_accept` → receive `product_recommendations`. All in one connection.

---

## Sprint 6 — React Tablet UI (Days 24–28)

**Goal**: All 7 core screens rendering with real backend data.

### Frontend

#### Screens to implement
- [ ] `IdleScreen` — BOBB logo + pulsing ring, tap anywhere to start
- [ ] `GreetingScreen` — animated wave + "Tell me your story" text + text input area
- [ ] `ListeningScreen` — textarea for story input, character counter, submit button
- [ ] `ThinkingScreen` — spinner + "Crafting your design…" copy
- [ ] `GeneratingScreen` — animated progress bar + rotating substatus messages
- [ ] `PreviewScreen` — 2×2 grid of 4 design variants, "Select" + "Try Different" actions
- [ ] `RefiningScreen` — selected design (640px) + 6 refinement pill groups, "Perfect, move on" CTA
- [ ] `ProductSelectionScreen` — 3 product cards with design mockup hint, size/color selectors

#### Shared components
- [ ] `SessionProvider` — wraps app, initializes WS on mount
- [ ] `useWebSocket` hook — connect, send, onMessage, reconnect
- [ ] `ProgressBar` component
- [ ] `DesignVariantCard` component
- [ ] `ProductCard` component
- [ ] `RefinementPills` component (6 groups × 6 options)
- [ ] BOBB design tokens applied globally (colors, fonts, spacing)

### Tests
- [ ] React Testing Library: render each screen with mock store state
- [ ] WS hook test: mock server sends messages, verify store updates

**Done when**: Can run full flow in browser: type story → watch generation → see 4 variants → select → refine → see product recommendations.

---

## Sprint 7 — Integration: Full Vertical Slice E2E (Days 29–32)

**Goal**: Demo-ready end-to-end with real Anthropic API + fal.ai.

- [ ] Run full flow with real API keys (staging keys)
- [ ] Fix any timing/UX issues (progress bar feels accurate)
- [ ] Image loading states (skeleton screens while images load)
- [ ] WebSocket reconnection: tablet goes to sleep → reconnects → resumes state
- [ ] Error screen with retry/help options
- [ ] `CLAUDE.md` updated with any architecture decisions made during sprints
- [ ] Latency audit: ensure total Story → Variants time < 30s
- [ ] API key errors → graceful "system unavailable" message

**Done when**: Walk a colleague through the flow without any crashes. Story to product recommendations in < 35 seconds.

---

## Sprint 8 — Cart, Checkout, Production UI (Days 33–37)

**Goal**: Full order path through to production tracking.

### Backend
- [ ] `POST /api/v1/orders` endpoint with discount calculation
- [ ] `GET /api/v1/orders/{id}/production` endpoint
- [ ] Background task: simulate production stage progression (for demo)
- [ ] WebSocket `production_update` events emitted every 30s

### Frontend
- [ ] `CartScreen` — item list, discount display, total, "Checkout" CTA
- [ ] `CheckoutScreen` — name, phone, name tag form, payment method selector (no gateway, just UI)
- [ ] `ProductionScreen` — 4-stage progress visualization with live WebSocket updates
- [ ] `SuccessScreen` — animated checkmark, order summary, "Make another one?" loop

**Done when**: Full flow from IDLE to SUCCESS runs with simulated production progress.

---

## Sprint 9 — Polish & Production Readiness (Days 38–42)

**Goal**: Ready for first real customers.

- [ ] Performance: image caching headers, lazy load off-screen variants
- [ ] Tablet viewport: test on 2960×1848 resolution, touch targets ≥ 48px
- [ ] Session timeout: if no activity for 3 min → auto-abandon + reset to IDLE
- [ ] Logging: all agent calls, errors, and state transitions logged to DB
- [ ] Analytics endpoint: `GET /api/v1/analytics/today`
- [ ] Inventory check: prevent ordering out-of-stock products
- [ ] Load test: simulate 5 concurrent sessions
- [ ] Security: validate all inputs, sanitize name tag text
- [ ] `docker-compose.yml` with backend + postgres + nginx for production deploy
- [ ] Final README with one-command setup

---

## Out of Scope (Post-MVP)

These are documented for future sprints but not included in this plan:

| Feature | Reason deferred |
|---|---|
| Voice input (Whisper) | Requires audio pipeline; text input sufficient for MVP |
| Payment gateway (UPI/Razorpay) | Requires merchant registration; manual cash works for launch |
| ComfyUI local inference | Hardware setup complexity; fal.ai proves the flow first |
| Admin/staff dashboard | Not customer-facing; can use DB directly initially |
| Loyalty/repeat customer tracking | Nice-to-have post-launch |
| Offline mode | Requires service worker + local model; Phase 2 |
| Multi-language (Malayalam) | Phase 2 localisation |
| DTF printer API integration | Hardware integration Phase 2 |

---

## Definition of Done (All Sprints)

- [ ] Feature works end-to-end in browser
- [ ] Unit tests written and passing (`pytest -v`)
- [ ] No TypeScript `any` types added without comment explaining why
- [ ] No hardcoded API keys (all via `.env`)
- [ ] New DB columns have migrations
- [ ] PR merged to `claude/inspiring-albattani-ladj5g`

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| fal.ai rate limits hit during demo | Medium | High | Pre-cache 10 example designs; add retry with exponential backoff |
| Claude generates non-JSON output | Low | High | Use structured output mode; add JSON parse fallback with retry |
| PostgreSQL connection pool exhausted | Low | Medium | Set pool size to 10, add connection timeout |
| Image gen > 30s for all 4 variants | Medium | Medium | Start polling UI after 5s; show partial results as they arrive |
| Sprint scope creep | High | Medium | Each sprint has a hard "Done when" checkpoint; defer to backlog |
