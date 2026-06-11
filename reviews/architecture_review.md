# BOBB AI Platform — Architecture Review

**Reviewer**: Principal Architect / Technical Lead  
**Date**: 2026-06-11  
**Documents Reviewed**: CLAUDE.md, architecture.md, database_schema.md, api_contracts.md, sprint_plan.md  
**Scope**: Critical design review before any application code is written

---

## Executive Summary

The planning documents establish a solid MVP foundation with well-scoped deferrals and a reasonable tech stack. However, **8 blocking issues** must be resolved before Sprint 1 begins — they will cause runtime failures or force rework of already-built components if discovered later. A further 16 issues are significant enough to address within the current sprint plan. 10 observations are lower priority but should be tracked.

**Overall verdict**: Do not begin Sprint 0 scaffolding until the CRITICAL and HIGH issues are resolved in these planning documents. The cost of fixing a schema constraint is zero now; it is a migration + code change later.

---

## Severity Classification

| Level | Meaning |
|---|---|
| **CRITICAL** | Will cause runtime failures or data corruption as designed |
| **HIGH** | Will require rework of built components; fix before writing code |
| **MEDIUM** | Causes technical debt, UX degradation, or blocked future work |
| **LOW** | Architectural smell; track and address when convenient |

---

## Section 1: Agent Architecture

---

### ISSUE-01 — No multi-turn context threading in Conversation Agent
**Severity**: CRITICAL  
**Component**: `agents/conversation.py`, `CLAUDE.md` agent design  

**Problem**: The Conversation Agent is defined as a single stateless Claude call: `extract_story(text: str, session_id: str) -> Story`. Claude has no memory. When the flow enters `CLARIFYING` state and the customer answers a clarifying question, the agent receives only the new answer — it has no record of what was said before. The clarification will be incoherent: Claude cannot correlate the answer with the question it doesn't remember asking.

**Risk**: Clarification turns produce nonsensical Story extractions. Customers who need clarification get a worse experience than customers who don't, which is the opposite of the intended behaviour.

**Recommendation**: Pass the full conversation history array to Claude on every turn. The `conversation_logs` table already stores turn-by-turn history — use it.

**Proposed fix**:
```python
# Replace this:
async def extract_story(self, text: str, session_id: str) -> Story: ...

# With this:
async def extract_story(
    self,
    new_input: str,
    session_id: str,
    prior_turns: list[ConversationTurn],  # fetched from conversation_logs
) -> Story: ...
```
Build the Claude `messages` array from `prior_turns` before each call, with alternating user/assistant turns. Update the `conversation_logs` schema to store `agent_response` (the clarification question) as a proper assistant turn, not just a raw field.

---

### ISSUE-02 — Design Agent produces generic prompts; no product-context at design time
**Severity**: HIGH  
**Component**: `agents/design.py`, core vertical slice flow  

**Problem**: The Design Agent receives only `Story` JSON and an optional `product_type`. The actual product is not selected until `PRODUCT_SELECTION`, *after* the design is locked. This means a 1024×1024 generic prompt is generated, but then the customer selects a curved snapback cap (3.5×2.5 inches, embroidery-style) or a cylindrical water bottle (4×6 wrap). The design is architecturally decoupled from its physical constraints at the point where those constraints matter most.

**Risk**: Designs look great on-screen but are unprintable or aesthetically wrong on the chosen product. The docs (`BOBB_Product_Design_Thinking_Research.md`) explicitly state different composition strategies per product (e.g., "horizontal bands" for water bottles, "icon-level simplicity" for keychains). Ignoring these at design time wastes the entire knowledge base.

**Recommendation**: Two options:
1. **Preferred**: Ask the customer "what product are you thinking?" *before* design generation. Add a lightweight product pre-selection step (show 3 category tiles: Apparel, Accessories, Home). Feed this into DesignAgent as a mandatory `product_category` parameter.
2. **Alternative**: After `PRODUCT_SELECTION`, add a "design optimisation" step that re-runs DesignAgent with the exact product's print area constraints, generating a product-specific final variant without showing it to the customer as a new choice.

**Proposed fix** to Design Agent interface:
```python
async def generate_prompts(
    self,
    story: Story,
    session_id: str,
    product_hint: ProductHint | None,  # print_area, aspect_ratio, print_method
) -> list[VariantPrompt]: ...
```
Add `ProductHint` to the schema. Inject product-specific print constraints from `/docs/` into the design system prompt when `product_hint` is provided.

---

### ISSUE-03 — Product Agent using Claude for a deterministic scoring problem
**Severity**: HIGH  
**Component**: `agents/product.py`, sprint_plan.md Sprint 4  

**Problem**: The product scoring algorithm is fully defined in the docs with exact weights: design fit (40%), complexity match (30%), demographics (15%), budget (10%), inventory (5%). This is a pure function with no ambiguity. Using Claude (even Haiku) for this introduces: non-determinism (different scores on identical inputs), added latency (~800ms–1.5s), additional cost, and an extra failure mode. The docs' `ProductRecommendationEngine` Python class already implements this exactly.

**Risk**: Non-deterministic product rankings erode customer trust. Claude failing during product recommendation (API error, rate limit) blocks the checkout flow unnecessarily.

**Recommendation**: Use the deterministic `ProductRecommendationEngine` (from docs) as the *primary* scorer. Claude's role should be limited to generating the human-readable `reasons` copy for each recommendation — a separate, optional enrichment call that can degrade gracefully to template strings.

**Proposed fix**: 
```python
# Deterministic scorer (always runs)
scores = ProductRecommendationEngine.rank(design, story, inventory)

# Claude enrichment (optional, with fallback)
try:
    enriched = await claude_haiku.enrich_reasons(scores[:3], story)
except Exception:
    enriched = [generate_template_reason(r) for r in scores[:3]]
```
Remove `ProductAgent` as a Claude agent. Rename to `ProductRecommendationService` with a pure-Python implementation.

---

### ISSUE-04 — Demographics used in scoring are never collected
**Severity**: HIGH  
**Component**: `agents/product.py`, `models/schemas.py`, core data flow  

**Problem**: The product recommendation scoring uses `customer_data.get("age_group")` (15% weight) and `customer_data.get("budget")` (10% weight) — together 25% of the score. The `Story` schema has no demographic fields. There is no step in the flow that collects age group or budget. The Conversation Agent does not infer these. The `ProductRecommendationEngine.recommend()` signature takes `customer_data` but it is never populated.

**Risk**: 25% of the scoring weights always fall to the else branch (score += 0.03 or 0.05), making the scoring effectively deterministic-but-wrong. Every customer is scored as if they have unknown demographics. The algorithm is silently broken.

**Recommendation** (pick one):
1. **Remove demographic scoring** from MVP. Score is: design fit (57%), complexity (43%), inventory check (pass/fail). Simple and correct.
2. **Infer from story**: Add `inferred_budget: str | None` and `inferred_age_group: str | None` to `Story` schema. The Conversation Agent infers these from language cues ("gift for my kid", "something cheap", "premium quality"). Document confidence ranges.
3. **Explicit lightweight collection**: After story submission, show 2 quick-tap questions ("Who is this for?" + "Budget?"). Simple, transparent, fast.

**Proposed fix to Story schema**:
```python
class Story(BaseModel):
    ...
    inferred_budget: Literal["low", "medium", "high"] | None = None
    inferred_recipient: Literal["self", "child", "adult", "family"] | None = None
```

---

### ISSUE-05 — Orchestrator is tightly coupled to WebSocket transport
**Severity**: MEDIUM  
**Component**: `agents/orchestrator.py`, Sprint 5  

**Problem**: The orchestrator's `run_story_pipeline(text, session_id, ws_send)` takes a `ws_send` callable directly. This means: (a) unit tests require a mock WebSocket, (b) the orchestrator cannot be used from REST endpoints without wrapping, (c) migrating to Server-Sent Events or polling requires changing orchestrator signatures.

**Recommendation**: Use a `ProgressCallback` Protocol or an async event queue. The orchestrator emits typed events; the WebSocket handler subscribes to them.

**Proposed fix**:
```python
class ProgressEvent(BaseModel):
    type: str
    payload: dict

ProgressCallback = Callable[[ProgressEvent], Awaitable[None]]

async def run_story_pipeline(
    self,
    text: str,
    session_id: str,
    on_progress: ProgressCallback,  # injected, not a WS reference
) -> PipelineResult: ...
```
The WebSocket handler provides a `ws_send`-wrapped callback. Tests provide a list-appending mock.

---

### ISSUE-06 — No circuit breaker for Anthropic API failures
**Severity**: MEDIUM  
**Component**: All agents  

**Problem**: The plan specifies "1 retry, then raise" for Anthropic errors. This is insufficient for a physical retail kiosk with a 10-14 minute customer journey. If Anthropic returns a 529 (overloaded) or rate-limit, the customer sees an error after 30+ seconds of waiting. There is no fallback behaviour defined for any agent beyond "raise."

**Risk**: On a busy market day with internet instability, the kiosk could become unusable for extended periods.

**Recommendation**: Define fallback behaviours per agent:
- **Conversation Agent fail**: Fall back to a guided structured input form (4 tappable theme cards + mood selector). No Claude needed.
- **Design Agent fail**: Use pre-written prompts from the Kerala theme matrix (from docs). Each theme has a canonical prompt.
- **Product Agent fail**: Rule-based scorer always works offline (as per ISSUE-03 fix).
- **Image gen fail**: Pre-cached example designs per theme (10 stored locally). Show with a "similar design" label.

Document these fallbacks explicitly in `CLAUDE.md`.

---

## Section 2: Database Schema

---

### ISSUE-07 — `design_variants.variant_number` CHECK constraint breaks for refinements
**Severity**: CRITICAL  
**Component**: `database_schema.md`, `design_variants` table  

**Problem**: The schema defines `variant_number SMALLINT NOT NULL CHECK (variant_number BETWEEN 1 AND 4)`. Refined designs create new rows in `design_variants` (the `is_refined = true` and `parent_variant_id` fields confirm this). When a refinement is applied to variant 2, what `variant_number` does the new row get? If it gets 2 (replacing), the CHECK is fine but you can't distinguish original from refined. If it gets 5+, the CHECK constraint violates and the INSERT fails.

**Risk**: Every single design refinement operation will throw a PostgreSQL CHECK violation. The entire refinement feature is broken as currently designed.

**Proposed fix**: 
```sql
-- Remove the CHECK constraint:
variant_number  SMALLINT NOT NULL,  -- original variants: 1-4, refined: 5+

-- Add a sequence column instead:
display_order   SMALLINT NOT NULL DEFAULT 1,  -- for UI ordering

-- And a separate flag:
is_initial_set  BOOLEAN NOT NULL DEFAULT true,  -- false for refinements
```
Update `designs.selected_variant` (ISSUE-08 below) accordingly.

---

### ISSUE-08 — `designs.selected_variant` integer FK to variant_number is semantically wrong
**Severity**: CRITICAL  
**Component**: `database_schema.md`, `designs` table  

**Problem**: `designs.selected_variant SMALLINT CHECK (selected_variant BETWEEN 1 AND 4)` stores the variant *number* not the variant *ID*. This is not a proper foreign key — it's a loose coupling by integer position. When a customer selects a refined variant (which by ISSUE-07's fix has a number > 4), this CHECK fails. Even fixing the CHECK, you can't JOIN from `designs` to `design_variants` on this column alone without also knowing the `design_id`.

**Risk**: Cannot reliably identify which `design_variants` row is the customer's selected design. Order creation will reference the wrong variant.

**Proposed fix**:
```sql
ALTER TABLE designs
  DROP COLUMN selected_variant,
  ADD COLUMN selected_variant_id UUID REFERENCES design_variants(id);
```
Remove the `BETWEEN 1 AND 4` check entirely. Add a `NOT NULL` constraint after the customer selects one (via application-level trigger or deferred constraint).

---

### ISSUE-09 — `inventory` table conflates static catalog with mutable stock
**Severity**: HIGH  
**Component**: `database_schema.md`, `inventory` table  

**Problem**: `inventory` holds both static product configuration (`print_area`, `design_fit_scores`, `production_time_min`, `min_complexity`, `max_complexity`) and volatile stock data (`units_sold`, `units_reserved`). These have fundamentally different update frequencies and access patterns. Stock is updated on every order. Config is updated when the product line changes. Storing them together means every stock update (high frequency) writes to the same row as config reads (high frequency), causing lock contention.

Additionally, `units_remaining` is not a column — it must be computed as `units_total - units_sold - units_reserved`. There's no DB-level constraint enforcing `units_remaining >= 0`.

**Proposed fix**: Split into two tables:
```sql
CREATE TABLE products (           -- static, rarely changes
    product_id          VARCHAR(50) PRIMARY KEY,
    product_name        VARCHAR(100) NOT NULL,
    category            VARCHAR(30),
    price_paise         INT NOT NULL,
    print_area_width_in  NUMERIC(4,2),
    print_area_height_in NUMERIC(4,2),
    print_method        VARCHAR(20),  -- dtf | sublimation | uv | vinyl
    min_complexity      VARCHAR(10),
    max_complexity      VARCHAR(10),
    production_time_min SMALLINT,
    design_fit_scores   JSONB,
    is_active           BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE product_stock (      -- dynamic, updated per order
    product_id      VARCHAR(50) PRIMARY KEY REFERENCES products(product_id),
    size_or_variant VARCHAR(10),  -- XS/S/M or one_size
    units_total     INT NOT NULL DEFAULT 0,
    units_sold      INT NOT NULL DEFAULT 0,
    units_reserved  INT NOT NULL DEFAULT 0,
    -- Computed/enforced:
    CONSTRAINT stock_non_negative CHECK (units_total - units_sold - units_reserved >= 0)
);
```

---

### ISSUE-10 — Regeneration count not tracked; infinite "try different" loops possible
**Severity**: HIGH  
**Component**: `database_schema.md`, state machine  

**Problem**: The architecture allows `PREVIEW → THINKING` ("try different") up to 3 times. The `designs` table has `refinements_count` but no `regenerations_count`. There is nowhere to persist how many times the customer has asked to regenerate entirely. After server restart or reconnect, the count is lost. The 3-regeneration limit is unenforced.

**Risk**: A customer can hammer "try different" indefinitely, consuming fal.ai API credits without limit.

**Proposed fix**:
```sql
ALTER TABLE designs
  ADD COLUMN regenerations_count SMALLINT NOT NULL DEFAULT 0;
```
Increment on every `PREVIEW → THINKING` transition. Enforce the limit in `SessionManager.transition_state()`.

---

### ISSUE-11 — `production_jobs` has no queue ordering mechanism
**Severity**: MEDIUM  
**Component**: `database_schema.md`, `production_jobs` table  

**Problem**: The `GET /orders/{id}/production` response includes `queue_position` and `estimated_wait_minutes`. Queue position is computed by `COUNT(*)` of jobs created before this one with non-complete status. This works, but: (a) there's no `priority` field for rush orders or staff overrides, (b) there's no `scheduled_at` for estimated time calculations, (c) the count query is a table scan without an appropriate index.

**Proposed fix**:
```sql
ALTER TABLE production_jobs
  ADD COLUMN queue_priority SMALLINT NOT NULL DEFAULT 5,  -- 1=urgent, 5=normal
  ADD COLUMN scheduled_start_at TIMESTAMPTZ;

CREATE INDEX idx_jobs_queue ON production_jobs(print_status, queue_priority, created_at)
  WHERE print_status IN ('queued', 'printing');
```

---

### ISSUE-12 — Missing FK index on `order_items.design_variant_id`
**Severity**: MEDIUM  
**Component**: `database_schema.md`, `order_items` table  

**Problem**: `order_items` has a FK to `design_variants(id)` but no index on this column. Any query joining `order_items` to `design_variants` does a sequential scan on `order_items`. This also means the FK enforcement itself (which PostgreSQL checks on DELETE) does a scan.

**Proposed fix**:
```sql
CREATE INDEX idx_order_items_variant ON order_items(design_variant_id);
```

---

### ISSUE-13 — `product_recommendations` is a separate table for data that belongs on `designs`
**Severity**: LOW  
**Component**: `database_schema.md`  

**Problem**: `product_recommendations` is a standalone table requiring a JOIN for every design fetch. Recommendations are generated exactly once per design, never updated, and consumed only in the context of a design. There is no use case for querying recommendations independent of their design.

**Proposed fix**: Fold into `designs` table:
```sql
ALTER TABLE designs
  ADD COLUMN recommendations_json JSONB,
  ADD COLUMN recommendations_generated_at TIMESTAMPTZ,
  ADD COLUMN recommendations_model VARCHAR(50);
```
Remove the `product_recommendations` table. Simplifies the schema by one table and eliminates the JOIN.

---

## Section 3: API Contracts

---

### ISSUE-14 — `ws_url` hardcodes `localhost` — will never work from tablet
**Severity**: CRITICAL  
**Component**: `api_contracts.md`, `POST /sessions` response  

**Problem**: The session creation response includes:
```json
{ "ws_url": "ws://localhost:8420/ws/..." }
```
The tablet is a separate physical device on the LAN. `localhost` from the tablet's perspective is the tablet itself, not the Windows PC running the backend. The WebSocket will connect to nothing.

**Proposed fix**: Return a relative WebSocket path only; let the client construct the full URL from the current connection's host:
```json
{ "ws_path": "/ws/550e8400-e29b-41d4-a716-446655440000" }
```
Or construct the URL server-side from the `Host` request header:
```python
ws_url = f"ws://{request.headers['host']}/ws/{session_id}"
```
Document this as a required pattern in `CLAUDE.md`.

---

### ISSUE-15 — WebSocket `design_select` has field name inconsistency across documents
**Severity**: CRITICAL  
**Component**: `architecture.md` vs `api_contracts.md`  

**Problem**:
- `architecture.md` WebSocket table: `design_select` payload is `{ variant_id: 1-4 }`
- `api_contracts.md` WebSocket contract: `design_select` payload is `{ design_id, variant_number }`

These are different field names. A frontend developer using `architecture.md` will send `variant_id`; a backend developer implementing `ws.py` from `api_contracts.md` will look for `variant_number`. This will silently fail at runtime.

**Proposed fix**: Canonicalize `api_contracts.md` as the single source of truth for message shapes. Remove all message payload examples from `architecture.md`; replace with a reference: "See `api_contracts.md` for all WebSocket message definitions."

---

### ISSUE-16 — REST story endpoint and WebSocket `text_input` create two divergent code paths
**Severity**: HIGH  
**Component**: `api_contracts.md`, `POST /sessions/{id}/story`  

**Problem**: `POST /sessions/{id}/story` is a synchronous REST endpoint. It calls `ConversationAgent.extract_story()` and returns the Story. `text_input` via WebSocket calls the orchestrator, which calls `ConversationAgent` *and* chains into design generation with progress events. These are two completely different execution paths for the same user action. The REST endpoint returns Story only (no images); the WebSocket path returns Story + 4 images + recommendations.

**Risk**: If a frontend developer uses REST for story submission (it's simpler), the customer sees no progress, no images, and no recommendations — just a JSON response with no next step. This is a silent UX failure.

**Proposed fix**: Mark `POST /sessions/{id}/story` as **test/debug only** in the contract. Add a clear warning:
```
⚠️ This endpoint is for testing only. Production UI must use the WebSocket 
   text_input message, which drives the full pipeline with progress events.
```
Do not implement this endpoint until Sprint 2's tests require it. The WS path is the only real path.

---

### ISSUE-17 — Order creation has no idempotency protection
**Severity**: HIGH  
**Component**: `api_contracts.md`, `POST /orders`  

**Problem**: A network timeout during checkout causes the frontend to retry `POST /orders`. Without an idempotency mechanism, two orders are created for the same customer. At ₹650+ per order, this is a real financial and operational problem even at MVP scale.

**Proposed fix**: Two options:
1. **Idempotency key**: Add `Idempotency-Key: {session_id}` header. Server checks if an order already exists for that session before creating a new one.
2. **Session-scoped check**: On `POST /orders`, first query `SELECT id FROM orders WHERE session_id = $1 AND order_status != 'cancelled'`. If exists, return the existing order (200, not 201) instead of creating a new one.

Option 2 is simpler for MVP. Add to the contract and implement in Sprint 8.

---

### ISSUE-18 — Production polling and WebSocket production_update are redundant and inconsistent
**Severity**: MEDIUM  
**Component**: `api_contracts.md`, PRODUCTION state  

**Problem**: Two mechanisms exist for production status:
1. `GET /orders/{id}/production` — polling endpoint
2. WebSocket `production_update` events — server-push every 30s

The WebSocket is active throughout the entire session. Using polling while a WebSocket is available is redundant and wastes bandwidth. The polling response and the WS message have different structures (`stages[].percent` vs `stages[].substatus`).

**Recommendation**: Remove the polling endpoint from the contract. Use WebSocket exclusively for production updates. The polling endpoint adds implementation cost without adding capability. If the WebSocket drops during production (tablet sleep), reconnect recovery (ISSUE-26 below) handles resuming state.

---

### ISSUE-19 — No `design_locked` validation before order creation
**Severity**: MEDIUM  
**Component**: `api_contracts.md`, `POST /orders`  

**Problem**: `POST /orders` accepts `design_variant_id` in items but does not specify server-side validation that the referenced `design.design_locked = true`. A client could theoretically submit an order with a preliminary (unlocked) design variant.

**Proposed fix**: Add to the order creation endpoint documentation:
```
Server validates:
- design.design_locked = true for all design_variant_ids in items
- Returns 400 "Design not locked" if validation fails
```
Implement this check in the order creation service.

---

## Section 4: State Machine

---

### ISSUE-20 — No state recovery protocol after WebSocket reconnect
**Severity**: CRITICAL  
**Component**: `architecture.md` state machine, `api_contracts.md`  

**Problem**: A Samsung tablet will go to sleep during the 20-25 second image generation wait. When it wakes, the WebSocket is disconnected. On reconnect, the tablet receives only `{ "type": "connected", "session_id": "...", "state": "greeting" }`. The `greeting` state in that message is the *initial* state from `POST /sessions`, not the *current* state of the session. The tablet has no mechanism to reconstruct the UI for mid-session reconnects.

**Risk**: After reconnecting, the tablet shows the Greeting screen instead of the Preview screen with 4 generated images. The customer loses their design.

**Proposed fix**: Add a `resume` endpoint and WS connect protocol:
```
On WS connect, server sends current session state snapshot:
{
  "type": "session_resumed",
  "state": "preview",           // current state from DB
  "session": { ... },
  "latest_design": { ... },     // null if not yet generated
  "recommendations": [ ... ],   // null if not yet generated
  "order": { ... }              // null if not yet created
}
```
The frontend handles `session_resumed` to reconstruct any in-progress screen. This requires the `GET /sessions/{id}` endpoint to return full nested data (design + recommendations + order) — update the REST contract accordingly.

---

### ISSUE-21 — `THINKING/GENERATING/CLARIFYING → ERROR` transitions are absent from state machine
**Severity**: HIGH  
**Component**: `architecture.md` state machine  

**Problem**: The state machine defines `PRODUCTION → ERROR` but does not define `THINKING → ERROR`, `GENERATING → ERROR`, or `CLARIFYING → ERROR`. The Sprint 5 plan says "Global error handler: catch all agent/service errors, emit `error` message, transition to `ERROR` state." But the `SessionManager.transition_state()` validates transitions — if `GENERATING → ERROR` is not in `STATE_TRANSITIONS`, the state manager will raise `InvalidStateTransition`, masking the original error and leaving the session stuck in `GENERATING` forever.

**Proposed fix**: Add these transitions explicitly:
```python
STATE_TRANSITIONS = {
    ...
    SessionState.THINKING:    [..., SessionState.ERROR],
    SessionState.CLARIFYING:  [..., SessionState.ERROR],
    SessionState.GENERATING:  [..., SessionState.ERROR],
    SessionState.REFINING:    [..., SessionState.ERROR],
    SessionState.CHECKOUT:    [..., SessionState.ERROR],
    ...
}
```
Every state that performs a network operation should be able to transition to `ERROR`.

---

### ISSUE-22 — `ERROR` state cannot transition back to the failing state for retries
**Severity**: HIGH  
**Component**: `architecture.md` state machine  

**Problem**: `ERROR` can only transition to `IDLE` (abort) or `HELP` (escalate). But the error contract defines `recoverable: true` errors with `suggested_action: "retry"`. How does a retry work? The tablet needs to go back to `GENERATING` to retry image generation, or `THINKING` to retry the design agent. The state machine has no path for this.

**Risk**: "Recoverable" errors are recoverable in name only. Every error forces the customer to restart from scratch.

**Proposed fix**: Add retry transitions from ERROR:
```
ERROR
  ├─→ IDLE          (abort)
  ├─→ HELP          (escalate)  
  ├─→ GENERATING    (retry image gen — only if last_state = GENERATING)
  └─→ THINKING      (retry design agent — only if last_state = THINKING/GENERATING)
```
Store `last_successful_state` on the session to know where to retry from. The WS error message should include `retry_state: "generating"` when applicable.

---

### ISSUE-23 — Session timeout deferred to Sprint 9 but is critical for kiosk operation from day 1
**Severity**: MEDIUM  
**Component**: `sprint_plan.md`, session management  

**Problem**: Session timeout is scheduled for Sprint 9 (days 38-42). A retail kiosk where customers walk away mid-session without a timeout will accumulate zombie sessions. More critically, a session stuck in `GENERATING` (image gen running) with a disconnected tablet will hold a fal.ai API request open indefinitely. At 40-60 customers/day, after 3-4 days without timeout cleanup, the system will have hundreds of open/stuck sessions.

**Recommendation**: Move session timeout to Sprint 1 alongside session CRUD. Implement as a background task that runs every 60 seconds:
- Sessions in `IDLE/GREETING/LISTENING` for > 5 min → abandon
- Sessions in `GENERATING/THINKING` for > 3 min → transition to `ERROR` with `AGENT_TIMEOUT` code
- Sessions in `PRODUCTION` are never timed out (they must complete)

---

### ISSUE-24 — `GREETING` and `LISTENING` are redundant states for text-only MVP
**Severity**: LOW  
**Component**: `architecture.md`, state machine, sprint_plan.md  

**Problem**: `GREETING` displays the welcome screen. `LISTENING` displays the text input area. The transition requires a tap/action to move from one to the other. With voice deferred, there is no functional difference in what these two states *do* — both show static UI. This doubles the sprint work (two screens, two states, two WS messages) for zero user value.

**Recommendation**: Merge `GREETING` and `LISTENING` into a single `INPUT` state for MVP. Restore the split when voice is implemented (Phase 2) — at which point, `LISTENING` will show the waveform visualiser while `INPUT` shows the text field, making the distinction meaningful. Note this as a planned split in `CLAUDE.md`.

---

## Section 5: Image Generation Abstraction

---

### ISSUE-25 — `ImageGenerationService` interface is insufficient for ComfyUI migration
**Severity**: HIGH  
**Component**: `architecture.md`, image generation service  

**Problem**: The current interface signature:
```python
async def generate(
    prompts: list[str],
    session_id: str,
    product_type: str | None,
) -> list[ImageResult]: ...
```
ComfyUI does not work this way. It takes a workflow JSON graph (not a text prompt), has its own queue, uses node-based parameters (sampler type, CFG scale, steps, LoRA weights, ControlNet), and outputs from a named node. A text prompt is just one parameter within one node. The `ComfyUIImageService` will need to:
1. Select a product-specific workflow JSON template
2. Inject the prompt into the appropriate text node
3. Set image dimensions matching the product's print area
4. Poll ComfyUI's queue status API (different from fal.ai's)
5. Map the output node's image to an `ImageResult`

None of this fits the current interface.

**Proposed fix**: Extend the interface to carry structured generation parameters:
```python
@dataclass
class GenerationParams:
    prompts: list[str]           # text prompts per variant
    negative_prompt: str | None
    width: int                   # product-specific
    height: int
    product_type: str | None
    workflow_overrides: dict     # arbitrary ComfyUI node overrides

class ImageGenerationService(Protocol):
    async def generate(
        self,
        params: GenerationParams,
        session_id: str,
        on_progress: ProgressCallback | None,
    ) -> list[ImageResult]: ...
    
    async def generate_single(
        self,
        params: GenerationParams,
        session_id: str,
    ) -> ImageResult: ...
```
The fal.ai implementation ignores `workflow_overrides`. The ComfyUI implementation uses them fully. The interface is stable across both.

---

### ISSUE-26 — Local filesystem image storage creates implicit single-worker constraint
**Severity**: MEDIUM  
**Component**: `architecture.md`, image gen service, deployment  

**Problem**: Images are written to `cache/designs/{session_id}/` on the local filesystem and served via `StaticFiles`. This works for single-process deployment. However, `uvicorn --workers N` (even 2 workers) means worker A writes the file, but worker B might receive the HTTP request for the static file before FastAPI's `StaticFiles` is aware (this is actually fine for static files on the same machine, but the design doesn't acknowledge it). More critically, if the backend is ever containerised, the cache directory must be a mounted volume.

**Recommendation**: Document this constraint explicitly in `CLAUDE.md`:
```
IMAGE STORAGE NOTE: Images are stored to local filesystem cache/designs/.
This requires single-machine deployment. Containerised deployments must 
mount cache/ as a persistent volume. Multi-machine deployments require 
migrating to object storage (S3-compatible). This is a known Phase 2 concern.
```

---

### ISSUE-27 — No image cleanup policy; disk space grows unbounded
**Severity**: MEDIUM  
**Component**: `architecture.md`, image gen service  

**Problem**: At 60 customers/day × 4 variants × ~2MB each = ~480MB/day. Plus refinements (max 3 each) = up to ~840MB/day. Over 7 days without cleanup: ~5.9GB. A 512GB NVMe has headroom, but there is no TTL or cleanup defined anywhere.

**Proposed fix**: Add to Sprint 9 (or Sprint 0 infra):
```python
# Scheduled cleanup (run hourly):
# Delete cache/designs/{session_id}/ where session.completed_at < now() - 7 days
# OR where session.abandoned = true and session.updated_at < now() - 1 day
```
Add `DESIGN_CACHE_TTL_DAYS=7` to env vars.

---

## Section 6: Session Management

---

### ISSUE-28 — In-memory `active_sessions` dict is not multi-worker safe
**Severity**: HIGH  
**Component**: `architecture.md` application layer, deployment  

**Problem**: The WebSocket handler (from `bobb_server.py` in docs) uses `active_sessions = {}` as an in-process dict. With `uvicorn --workers 4`, each worker has its own dict. A session connected to worker 1 is invisible to worker 2. If nginx round-robins WebSocket upgrade requests (it shouldn't, but could), or if a reconnect lands on a different worker, the session is lost.

**Risk**: Even on a single machine, running multiple workers for throughput will silently break WebSocket sessions.

**Proposed fix**: For MVP (single worker): document explicitly in `CLAUDE.md`:
```
DEPLOYMENT CONSTRAINT: Backend must run as a single uvicorn worker 
(uvicorn app.main:app --workers 1). Multi-worker requires Redis for 
WebSocket connection state. This is a Phase 2 concern.
```
For Phase 2: use Redis + `broadcast` pattern or `python-socketio` with Redis adapter.

---

### ISSUE-29 — Session created before WebSocket connection; orphan sessions possible
**Severity**: MEDIUM  
**Component**: `api_contracts.md`, `POST /sessions`  

**Problem**: The flow is: `POST /sessions` → get `session_id` → connect WebSocket. If the WebSocket connection fails (network, tablet app crash), the session row exists in PostgreSQL in `greeting` state with no active connection. It will never progress and never be cleaned up (until Sprint 9 timeout is added). With 60 customers/day and occasional connection failures, orphan sessions accumulate.

**Recommendation**: Either:
1. Create the session row *on WebSocket connect* (not before). The `POST /sessions` endpoint's sole job becomes: generate and return a UUID. The DB row is created in the WebSocket handler on first connect.
2. Keep current flow but add a short TTL (2 minutes) for sessions that never leave `GREETING` state. Add this to Sprint 1.

---

## Section 7: Sprint Plan

---

### ISSUE-30 — Agents are built in isolation (Sprints 2-4) before any UI; integration risk is high
**Severity**: MEDIUM  
**Component**: `sprint_plan.md`  

**Problem**: Sprints 2, 3, and 4 build three agents backend-only, tested only with mocks. Sprint 6 builds the frontend. Sprint 7 integrates them. This means 4 sprints of development (20+ days) before any human has seen the real data flow on a real screen. UX assumptions baked into Sprint 2-4 agent outputs (e.g., the shape of `story_extracted`, the loading experience during generation) are only validated in Sprint 7 — at which point rework is expensive.

**Recommendation**: Restructure as thinner vertical slices:
- Sprint 2: Conversation Agent + ListeningScreen (text in → Story JSON shown)
- Sprint 3: Design Agent + GeneratingScreen + PreviewScreen (full image flow)
- Sprint 4: Product Agent + ProductSelectionScreen
- Sprint 5: WebSocket orchestrator (replaces 3 separate REST calls with streaming)

Each sprint ends with a human-testable screen. Rework is smaller and earlier.

---

### ISSUE-31 — No performance budget for the Story → Variants pipeline
**Severity**: MEDIUM  
**Component**: `sprint_plan.md`, Sprint 7  

**Problem**: Sprint 7 says "ensure total Story → Variants time < 30s." But the performance target should be defined *before* building so that each component has a budget. The pipeline is: Conversation Agent (~1-2s) → Design Agent (~2-3s) → 4× fal.ai (~15-25s, parallel). Total: 18-30s. fal.ai is the dominant term.

The 30s target may be optimistic if fal.ai cold-starts (first request of the day can take 45-60s for FLUX models). No warm-up strategy is defined.

**Recommendation**: Add to `CLAUDE.md` performance section:
```
Pipeline latency budget:
- Conversation Agent: < 2s
- Design Agent: < 3s  
- Image generation (4 variants, parallel): < 25s
- Total Story → Preview: < 30s (P90 target)

Warm-up: Send a test generation request on backend startup to warm fal.ai connection.
Partial display: Show variants as they complete, not all 4 at once.
```

---

### ISSUE-32 — `fal-ai/flux/dev` model choice is undecided; "or stable-diffusion-xl" is not a decision
**Severity**: LOW  
**Component**: `CLAUDE.md`, architecture.md  

**Problem**: Both documents say "fal-ai/flux/dev or fal-ai/stable-diffusion-xl" without choosing. These produce very different outputs. FLUX/dev is newer, more photorealistic. SDXL is more stylistic, better for illustration/geometric styles. The Kerala cultural themes in the docs lean toward illustration and geometric — SDXL may produce better results for the design styles being requested. This must be decided before Sprint 3.

**Recommendation**: Choose FLUX/dev as default (it's the current fal.ai recommended model). But configure the model via `FAL_MODEL_ID` env var so it can be changed without code changes. Test both before Sprint 3 demo. Document the chosen model in `CLAUDE.md`.

---

## Section 8: Voice Support (Future)

---

### ISSUE-33 — Voice addition is not a simple "plug in Whisper" change
**Severity**: MEDIUM  
**Component**: `CLAUDE.md` future scope, `api_contracts.md`  

**Problem**: The plan defers voice as "requires audio pipeline." The full scope of changes is not documented. Voice support will require:
1. **API contract**: New WS message type `voice_input` with chunked audio (streaming) or base64 (non-streaming). The current `text_input` message type does not extend to audio.
2. **State machine**: `LISTENING` state needs end-of-speech detection, silence timeout, and a "recording" vs "processing" sub-state.
3. **Backend**: Whisper integration (local model loading at startup, ~1GB VRAM, ~2-4s transcription latency adds to pipeline).
4. **Schema**: `conversation_logs.input_type` already has `'voice'` as valid but no `audio_file_path` column to store the original audio.
5. **Fallback**: Text input must remain available when voice fails.

**Recommendation**: Add a section to `CLAUDE.md` — "Phase 2: Voice Integration" — listing these changes explicitly. This prevents voice from being treated as a trivial addition in a future sprint.

---

### ISSUE-34 — `conversation_logs.input_type` allows 'voice' but voice infrastructure doesn't exist
**Severity**: LOW  
**Component**: `database_schema.md`  

**Problem**: The CHECK constraint `input_type IN ('text', 'voice')` implies voice is already a supported input type. No voice audio is ever captured or stored in MVP. This creates false expectations when reading the schema.

**Proposed fix**: Change to `input_type IN ('text')` for MVP migration. Add 'voice' in a Phase 2 migration when Whisper is integrated. Also add an `audio_file_path TEXT` column in that Phase 2 migration for storing the original audio recording.

---

## Section 9: ComfyUI Migration (Future)

---

### ISSUE-35 — ComfyUI migration complexity is severely underestimated
**Severity**: MEDIUM  
**Component**: `CLAUDE.md`, architecture.md  

**Problem**: The architecture states "Same interface, different transport (HTTP to localhost:8188). No application-layer code changes needed." This is not true. Beyond the interface changes in ISSUE-25, ComfyUI requires:

1. **Product-specific workflows**: Each of the 10 products needs a custom ComfyUI workflow JSON (different resolution, negative prompts, LoRA weights for print-style outputs). This is a content/design job, not just engineering.
2. **Model management**: SDXL base (6.9GB), SDXL refiner (6.9GB), CLIP (1.7GB), VAE — total ~16GB. The RTX 3060 has 12GB VRAM. SDXL base + refiner cannot run simultaneously. Workflow must use base-only or implement disk offloading.
3. **Concurrent generation**: ComfyUI processes one job at a time in its queue. The current architecture generates 4 variants in parallel. With ComfyUI, they're sequential — generation time goes from ~25s to ~100s. This breaks the 30s target.
4. **LoRA for cultural themes**: Kerala-specific LoRA models would dramatically improve output quality but require training data curation and fine-tuning. Not a "just flip the env var" change.

**Recommendation**: Add an honest Phase 2 ComfyUI section to `CLAUDE.md`:
```
COMFYUI MIGRATION (Phase 2) — Realistic scope:
- Week 1: Interface extension (ISSUE-25 fix), workflow JSON templates per product
- Week 2: Sequential generation mode (accept 4× slower), update UI progress expectations
- Week 3: VRAM profiling, memory optimisation, warm-up strategy
- Week 4+: Optional LoRA training for Kerala cultural themes
NOTE: The "flip one env var" description is inaccurate. Treat as a 3-4 week project.
```

---

## Summary Table

| # | Issue | Severity | Component | Sprint Impact |
|---|---|---|---|---|
| 01 | No multi-turn context threading | CRITICAL | conversation.py | Fix before Sprint 2 |
| 02 | Design Agent lacks product context | HIGH | design.py | Fix before Sprint 3 |
| 03 | Claude for deterministic scoring | HIGH | product.py | Fix before Sprint 4 |
| 04 | Demographics never collected | HIGH | schemas, flow | Fix before Sprint 4 |
| 05 | Orchestrator WS tight coupling | MEDIUM | orchestrator.py | Fix in Sprint 5 |
| 06 | No circuit breaker / fallbacks | MEDIUM | all agents | Add in Sprint 2 |
| 07 | variant_number CHECK breaks refinements | CRITICAL | DB schema | Fix before Sprint 0 |
| 08 | selected_variant FK by integer, not UUID | CRITICAL | DB schema | Fix before Sprint 0 |
| 09 | inventory conflates config + stock | HIGH | DB schema | Fix before Sprint 0 |
| 10 | Regeneration count not tracked | HIGH | DB schema | Fix before Sprint 0 |
| 11 | production_jobs lacks queue ordering | MEDIUM | DB schema | Fix before Sprint 8 |
| 12 | Missing FK index order_items→variants | MEDIUM | DB schema | Fix before Sprint 0 |
| 13 | product_recommendations as separate table | LOW | DB schema | Fix before Sprint 0 |
| 14 | ws_url hardcodes localhost | CRITICAL | api_contracts | Fix before Sprint 5 |
| 15 | design_select field name inconsistency | CRITICAL | api_contracts | Fix before Sprint 5 |
| 16 | REST story endpoint vs WS divergence | HIGH | api_contracts | Fix before Sprint 2 |
| 17 | Order creation not idempotent | HIGH | api_contracts | Fix before Sprint 8 |
| 18 | Polling + WS both for production | MEDIUM | api_contracts | Remove polling |
| 19 | No design_locked validation at order | MEDIUM | api_contracts | Fix before Sprint 8 |
| 20 | No WS reconnect / resume protocol | CRITICAL | state machine | Fix before Sprint 5 |
| 21 | Error transitions missing from state machine | HIGH | state machine | Fix before Sprint 1 |
| 22 | ERROR has no retry-back transitions | HIGH | state machine | Fix before Sprint 5 |
| 23 | Session timeout deferred too late | MEDIUM | sprint plan | Move to Sprint 1 |
| 24 | GREETING + LISTENING redundant in MVP | LOW | state machine | Merge for MVP |
| 25 | ImageGenerationService interface too thin | HIGH | image gen | Fix before Sprint 3 |
| 26 | Local filesystem / single-worker constraint | MEDIUM | image gen, deployment | Document now |
| 27 | No image cleanup policy | MEDIUM | image gen | Add to Sprint 9 |
| 28 | active_sessions dict not multi-worker safe | HIGH | session mgmt | Document now |
| 29 | Orphan sessions from failed WS connect | MEDIUM | session mgmt | Fix in Sprint 1 |
| 30 | Agents in isolation before UI, late integration | MEDIUM | sprint plan | Restructure |
| 31 | No performance budget per component | MEDIUM | sprint plan | Add to CLAUDE.md |
| 32 | fal.ai model undecided | LOW | CLAUDE.md | Decide before Sprint 3 |
| 33 | Voice addition scope undocumented | MEDIUM | CLAUDE.md | Document Phase 2 |
| 34 | conversation_logs allows 'voice' prematurely | LOW | DB schema | Fix before Sprint 0 |
| 35 | ComfyUI migration complexity underestimated | MEDIUM | CLAUDE.md | Document Phase 2 |

---

## Required Actions Before Sprint 0

The following **must** be resolved in the planning documents (not code) before scaffolding begins:

1. **Fix DB schema**: Issues 07, 08, 09, 10, 12, 13, 34 — schema changes in `database_schema.md`
2. **Fix state machine**: Issue 21 (add all → ERROR transitions), 22 (add ERROR retry paths), 20 (define reconnect protocol)
3. **Fix API contract**: Issue 14 (ws_url), 15 (field name), 16 (REST vs WS ownership)
4. **Extend image interface**: Issue 25 — extend `ImageGenerationService` to carry `GenerationParams`
5. **Decide model**: Issue 32 — pick fal.ai model
6. **Document constraints**: Issues 26, 28 — single-worker and filesystem constraints in `CLAUDE.md`

Estimated time to update planning documents: **1 day**. Cost of discovering these in code: **3-5 days** of rework.

---

*End of Review — 35 issues documented across 9 categories*
