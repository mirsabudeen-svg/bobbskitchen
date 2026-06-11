# BOBB AI Platform — Database Schema

**Database**: PostgreSQL 15  
**ORM**: SQLAlchemy 2.0 (async) with Alembic migrations  
**Monetary values**: stored in paise (integer). ₹1 = 100 paise.

---

## Entity Relationship Overview

```
sessions ──────────────────────────────┐
    │                                  │
    ├── conversation_logs              │
    ├── designs ──── design_variants   │
    │       │                          │
    ├── orders ──── order_items ───────┘
    │       │           │
    │       │       designs (FK)
    │       │
    │   production_jobs
    │
    └── agent_logs

inventory (standalone, product catalog)
analytics (daily aggregates, standalone)
```

---

## Tables

### `sessions`

Represents one customer interaction on the tablet.

```sql
CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    current_state   VARCHAR(32) NOT NULL DEFAULT 'idle',
    -- Customer info (collected at checkout)
    customer_name   VARCHAR(100),
    customer_phone  VARCHAR(20),
    customer_email  VARCHAR(255),
    -- Session outcome
    duration_seconds    INT,
    completed           BOOLEAN NOT NULL DEFAULT false,
    abandoned           BOOLEAN NOT NULL DEFAULT false,
    satisfaction_score  SMALLINT CHECK (satisfaction_score BETWEEN 1 AND 5),
    -- Metadata
    notes           TEXT,
    device_id       VARCHAR(50),   -- tablet identifier
    prompt_variant  VARCHAR(20) NOT NULL DEFAULT 'v1'  -- prompt A/B variant assigned at session creation
);

CREATE INDEX idx_sessions_state     ON sessions(current_state);
CREATE INDEX idx_sessions_created   ON sessions(created_at);
CREATE INDEX idx_sessions_completed ON sessions(completed, created_at);
```

---

### `conversation_logs`

Each turn of the customer ↔ Conversation Agent exchange.

```sql
CREATE TABLE conversation_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    turn_number     SMALLINT NOT NULL,
    -- FIX ISSUE-34: 'voice' removed until Whisper integration is built (Phase 2).
    -- Phase 2 migration will add: ALTER TABLE ... ADD COLUMN audio_file_path TEXT;
    --                             ALTER TABLE ... DROP CONSTRAINT ...; ADD CONSTRAINT ... IN ('text','voice');
    input_type      VARCHAR(10) NOT NULL CHECK (input_type IN ('text')),
    customer_input  TEXT NOT NULL,
    agent_response  TEXT,               -- raw Claude JSON response (tool_use input blob)
    agent_text_reply TEXT,              -- conversational text shown to customer (clarification question or acknowledgement)
    story_extracted JSONB,              -- structured Story JSON (see below)
    clarification_needed BOOLEAN NOT NULL DEFAULT false,
    clarity_score   NUMERIC(4,3),       -- 0.000–1.000; how complete/unambiguous the story is
    confidence      NUMERIC(4,3),       -- 0.000–1.000; agent confidence in extracted story
    response_time_ms    INT,
    tokens_input    INT,
    tokens_output   INT,
    model_used      VARCHAR(50)
);

CREATE INDEX idx_conv_session ON conversation_logs(session_id, turn_number);
```

**`story_extracted` shape**:
```json
{
  "themes": ["beach", "Kannur"],
  "emotions": ["pride", "nostalgia"],
  "keywords": ["waves", "palm trees", "sunset"],
  "cultural_refs": ["Kerala backwaters", "fishing boats"],
  "design_complexity": "medium",
  "intent": "DESIGN_REQUEST",
  "needs_clarification": false
}
```

---

### `designs`

A design session — the prompt, generated image URLs, and selection state.

```sql
CREATE TABLE designs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    story_json          JSONB NOT NULL,          -- canonical Story (final, post-clarification)
    story_version       SMALLINT NOT NULL DEFAULT 1,  -- incremented if story re-extracted
    design_prompt_base  TEXT NOT NULL,           -- Master prompt from Design Agent
    design_strategy_json JSONB,                  -- full DesignStrategy (4 VariantPrompts) persisted BEFORE image gen
    design_metadata     JSONB,                   -- complexity, cultural_refs, color_count
    -- FIX ISSUE-08: FK to design_variants.id (UUID), not a positional integer.
    -- NULL until customer selects a variant; set to NOT NULL is enforced at
    -- design-lock time in application code, not via DB constraint, because the
    -- referenced row must exist before the FK can be set.
    selected_variant_id UUID REFERENCES design_variants(id) DEFERRABLE INITIALLY DEFERRED,
    refinements_count   SMALLINT NOT NULL DEFAULT 0,
    regenerations_count SMALLINT NOT NULL DEFAULT 0,  -- "try different" counter (max 3)
    design_locked       BOOLEAN NOT NULL DEFAULT false,
    locked_at           TIMESTAMPTZ,
    -- Observability
    pipeline_run_id     UUID,                    -- correlates all agent_logs for this pipeline run
    is_fallback         BOOLEAN NOT NULL DEFAULT false,  -- true if any agent used a fallback
    -- Recommendations stored here (no separate table needed — generated once per design)
    recommendations_json        JSONB,
    recommendations_generated_at TIMESTAMPTZ,
    recommendations_model       VARCHAR(50)
);

CREATE INDEX idx_designs_session ON designs(session_id);
-- Forward-declared FK; design_variants references designs, so this FK is circular.
-- PostgreSQL handles circular FKs via DEFERRABLE. No extra index needed here
-- because design_variants already has idx_variants_design on design_id.
```

---

### `design_variants`

Each of the 4 initial image variants for a design, plus any refined variants.

```sql
CREATE TABLE design_variants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    design_id       UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- FIX ISSUE-07: Removed CHECK (variant_number BETWEEN 1 AND 4).
    -- Initial variants are 1-4. Refined variants increment beyond 4 (5, 6, 7…).
    -- The CHECK constraint caused an INSERT violation on every refinement.
    variant_number  SMALLINT NOT NULL,
    is_initial_set  BOOLEAN NOT NULL DEFAULT true,  -- false for refinement-derived variants
    prompt_used     TEXT NOT NULL,               -- exact positive prompt sent to image gen
    negative_prompt TEXT,                        -- exact negative prompt sent to image gen
    style           VARCHAR(30),                 -- illustration | geometric | watercolor | minimalist
    -- image_url: local path served via /cache/ static mount (e.g. /cache/designs/sess/v1.png)
    -- Always a local path in MVP. Never an external URL — download on generation.
    image_url       TEXT,
    generation_time_ms  INT,
    model_used      VARCHAR(80),                 -- e.g. fal-ai/flux/dev
    fal_request_id  VARCHAR(100),               -- fal.ai's own request ID (for support/billing)
    generation_seed BIGINT,                      -- seed returned by fal.ai; enables exact replay
    is_fallback     BOOLEAN NOT NULL DEFAULT false,
    is_refined      BOOLEAN NOT NULL DEFAULT false,
    parent_variant_id UUID REFERENCES design_variants(id),  -- refinement chain; NULL for initial set
    refinement_type  VARCHAR(30),                -- color_scheme | style | mood | focus | elements | size
    refinement_value VARCHAR(100)
);

CREATE INDEX idx_variants_design   ON design_variants(design_id);
CREATE INDEX idx_variants_initial  ON design_variants(design_id, is_initial_set);
-- FK index for order_items → design_variants join (FIX ISSUE-12):
CREATE INDEX idx_order_items_variant ON order_items(design_variant_id);
```

**Variant numbering convention**:
- Initial generation: variant_number 1, 2, 3, 4 (is_initial_set = true)
- First refinement applied to variant 2: variant_number 5 (is_initial_set = false, parent_variant_id = id of variant 2)
- Second refinement: variant_number 6, and so on
- `designs.selected_variant_id` always points to the UUID of the currently chosen variant

---

### ~~`product_recommendations`~~ — Removed

Product recommendations are stored as JSONB on the `designs` table
(`designs.recommendations_json`). They are generated once per design, never
updated, and always consumed in the context of a design. A separate table added
an unnecessary JOIN. See the `designs` table definition above.

**`recommendations_json` element shape**:
```json
{
  "rank": 1,
  "product_id": "tshirt_premium",
  "score": 0.87,
  "reasons": ["Design fit: illustration", "Perfect complexity match: medium"],
  "price_paise": 65000,
  "print_area": "10x12 inches",
  "production_time_minutes": 7
}
```

---

### `orders`

A confirmed customer order (after checkout).

```sql
CREATE TABLE orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES sessions(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Customer
    customer_name   VARCHAR(100) NOT NULL,
    customer_phone  VARCHAR(20),
    name_tag_text   VARCHAR(15),             -- hand-stitched name tag, max 15 chars
    -- Financials (in paise)
    subtotal_paise  INT NOT NULL,
    discount_paise  INT NOT NULL DEFAULT 0,
    discount_type   VARCHAR(20),             -- quantity | student | promo
    tax_paise       INT NOT NULL DEFAULT 0,
    total_paise     INT NOT NULL,
    currency        CHAR(3) NOT NULL DEFAULT 'INR',
    -- Payment
    payment_method  VARCHAR(10) CHECK (payment_method IN ('upi', 'card', 'cash')),
    payment_status  VARCHAR(15) NOT NULL DEFAULT 'pending'
                        CHECK (payment_status IN ('pending', 'completed', 'failed', 'refunded')),
    payment_ref     VARCHAR(100),            -- gateway transaction ID
    -- Fulfillment
    order_status    VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (order_status IN (
                            'pending', 'queued', 'printing', 'pressing',
                            'stitching', 'complete', 'cancelled')),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_orders_session ON orders(session_id);
CREATE INDEX idx_orders_status  ON orders(order_status, created_at);
```

---

### `order_items`

Line items within an order (a customer can order multiple products).

```sql
CREATE TABLE order_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    design_variant_id UUID NOT NULL REFERENCES design_variants(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    product_id      VARCHAR(50) NOT NULL,    -- references inventory.product_id
    product_name    VARCHAR(100) NOT NULL,
    size            VARCHAR(5),              -- XS | S | M | L | XL | XXL
    color           VARCHAR(30) NOT NULL,
    quantity        SMALLINT NOT NULL DEFAULT 1,
    unit_price_paise INT NOT NULL,
    subtotal_paise  INT NOT NULL
);

CREATE INDEX idx_items_order ON order_items(order_id);
```

---

### `production_jobs`

Tracks the 4-stage physical production process per order item.

```sql
CREATE TABLE production_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID NOT NULL REFERENCES orders(id),
    order_item_id   UUID NOT NULL REFERENCES order_items(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    design_file_path TEXT,

    -- Stage: PRINT
    print_status    VARCHAR(15) NOT NULL DEFAULT 'queued'
                        CHECK (print_status IN ('queued','printing','complete','failed')),
    print_started_at    TIMESTAMPTZ,
    print_completed_at  TIMESTAMPTZ,
    print_duration_s    INT,

    -- Stage: PRESS
    press_status    VARCHAR(15) NOT NULL DEFAULT 'queued'
                        CHECK (press_status IN ('queued','pressing','complete','failed')),
    press_started_at    TIMESTAMPTZ,
    press_completed_at  TIMESTAMPTZ,

    -- Stage: STITCH (name tag)
    stitch_status   VARCHAR(15) NOT NULL DEFAULT 'queued'
                        CHECK (stitch_status IN ('queued','stitching','complete','skipped')),
    stitch_completed_at TIMESTAMPTZ,

    -- Stage: READY
    quality_check_passed BOOLEAN,
    completed_at    TIMESTAMPTZ,
    notes           TEXT
);

CREATE INDEX idx_jobs_order  ON production_jobs(order_id);
CREATE INDEX idx_jobs_status ON production_jobs(print_status, created_at);
```

---

### `inventory`

Product catalog and stock levels.

```sql
CREATE TABLE inventory (
    product_id          VARCHAR(50) PRIMARY KEY,
    product_name        VARCHAR(100) NOT NULL,
    category            VARCHAR(30),                 -- apparel | accessories | home
    price_paise         INT NOT NULL,
    print_area          VARCHAR(50),                 -- e.g. "10x12 inches"
    min_complexity      VARCHAR(10) DEFAULT 'simple',
    max_complexity      VARCHAR(10) DEFAULT 'complex',
    production_time_min SMALLINT,
    margin_percent      SMALLINT,
    -- Inventory
    units_total         INT NOT NULL DEFAULT 0,
    units_sold          INT NOT NULL DEFAULT 0,
    units_reserved      INT NOT NULL DEFAULT 0,
    reorder_level       INT NOT NULL DEFAULT 5,
    -- Design fit scores (JSON per style)
    design_fit_scores   JSONB,                       -- {"illustration": 0.95, "geometric": 0.85}
    -- Sizing (JSON)
    sizes               JSONB,                       -- {"XS": 20, "S": 30, ...}
    colors              JSONB,                       -- ["black", "white", ...]
    is_active           BOOLEAN NOT NULL DEFAULT true,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### `agent_logs`

Audit log for every Claude API call.

```sql
CREATE TABLE agent_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES sessions(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    agent_name      VARCHAR(30) NOT NULL,   -- conversation | design | product
    model_used      VARCHAR(50),
    state           VARCHAR(32),
    pipeline_run_id UUID,                  -- groups all agent calls for one pipeline invocation
    prompt_version  VARCHAR(40),           -- SHA-1 hash of system prompt file at call time
    is_fallback     BOOLEAN NOT NULL DEFAULT false,
    tokens_input    INT,
    tokens_output   INT,
    cost_microdollars INT,
    execution_ms    INT,
    success         BOOLEAN NOT NULL DEFAULT true,
    error_code      VARCHAR(50),
    error_message   TEXT
);

CREATE INDEX idx_agent_logs_session ON agent_logs(session_id, created_at);
CREATE INDEX idx_agent_logs_agent   ON agent_logs(agent_name, created_at);
```

---

### `analytics`

Daily aggregated metrics (populated by a nightly job or on-demand).

```sql
CREATE TABLE analytics (
    date                DATE PRIMARY KEY,
    total_sessions      INT NOT NULL DEFAULT 0,
    completed_sessions  INT NOT NULL DEFAULT 0,
    abandoned_sessions  INT NOT NULL DEFAULT 0,
    completed_orders    INT NOT NULL DEFAULT 0,
    failed_orders       INT NOT NULL DEFAULT 0,
    revenue_paise       BIGINT NOT NULL DEFAULT 0,
    avg_session_s       INT,
    avg_satisfaction    NUMERIC(3,2),
    top_product_id      VARCHAR(50),
    top_design_theme    VARCHAR(50),
    total_agent_calls   INT,
    total_tokens_used   BIGINT,
    total_images_gen    INT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Pydantic Schemas (Python)

Key schemas used throughout the backend:

```python
class SessionState(str, Enum):
    IDLE = "idle"
    GREETING = "greeting"
    LISTENING = "listening"
    CLARIFYING = "clarifying"
    THINKING = "thinking"
    GENERATING = "generating"
    PREVIEW = "preview"
    REFINING = "refining"
    PRODUCT_SELECTION = "product_selection"
    CART = "cart"
    CHECKOUT = "checkout"
    PRODUCTION = "production"
    SUCCESS = "success"
    ERROR = "error"
    HELP = "help"

class KeralaTheme(str, Enum):
    BACKWATERS       = "backwaters"
    THEYYAM          = "theyyam"
    KATHAKALI        = "kathakali"
    MONSOON          = "monsoon"
    FISHING_HERITAGE = "fishing_heritage"
    COCONUT_PALMS    = "coconut_palms"
    SPICE_TRADE      = "spice_trade"
    TEMPLE_ARCH      = "temple_architecture"
    BEACH            = "beach"
    BOAT_RACE        = "boat_race"
    NONE             = "none"

class Story(BaseModel):
    themes: list[KeralaTheme]   # controlled vocabulary; validated by KeralaTheme enum
    emotions: list[str]
    keywords: list[str]
    cultural_refs: list[str]
    design_complexity: Literal["simple", "medium", "complex"]
    intent: str
    raw_customer_text: str      # original unmodified input; passed to Design Agent for grounding
    needs_clarification: bool = False
    clarification_questions: list[str] = []
    clarity_score: float = 1.0  # 0.0–1.0; how complete/unambiguous the story is
    confidence: float = 1.0     # 0.0–1.0; agent confidence in extraction

class ConversationTurn(BaseModel):
    turn_number: int
    customer_input: str
    agent_text_reply: str | None  # conversational response (clarification Q or ack); replayed as assistant turn

class VariantStyle(str, Enum):
    ILLUSTRATION = "illustration"
    GEOMETRIC    = "geometric"
    WATERCOLOR   = "watercolor"
    MINIMALIST   = "minimalist"

class VariantPrompt(BaseModel):
    style: VariantStyle
    prompt: str                  # full positive prompt (SDXL/FLUX compatible)
    negative_prompt: str         # full negative prompt; never empty
    color_palette: list[str]     # hex codes or named colors
    mood: str                    # descriptive tag for UI display
    width: int                   # product-specific pixel width (~300dpi equivalent)
    height: int

class DesignMetadata(BaseModel):
    cultural_authenticity_score: float
    print_feasibility: Literal["excellent", "good", "marginal", "poor"]
    color_count: int
    complexity: Literal["simple", "medium", "complex"]
    estimated_print_time_min: float
    kerala_themes_used: list[KeralaTheme]

class DesignStrategy(BaseModel):
    base_story_summary: str      # 1-sentence design brief for display/logging
    variants: list[VariantPrompt]  # exactly 4
    design_metadata: DesignMetadata
    is_fallback: bool = False

class DesignVariant(BaseModel):
    id: UUID
    variant_number: int          # 1–4 for initial set; 5+ for refinements
    is_initial_set: bool
    style: VariantStyle
    prompt_used: str
    negative_prompt: str | None
    image_url: str | None        # always a local /cache/ path in MVP
    generation_time_ms: int | None
    fal_request_id: str | None   # for fal.ai support queries
    generation_seed: int | None  # enables exact replay
    is_refined: bool = False
    is_fallback: bool = False
    parent_variant_id: UUID | None = None

class ImageResult(BaseModel):
    variant_number: int
    style: VariantStyle
    image_path: str              # absolute local path
    image_url: str               # relative URL served by StaticFiles
    prompt_used: str
    negative_prompt_used: str
    model_used: str
    fal_request_id: str | None
    generation_time_ms: int
    seed: int | None
    success: bool
    error: str | None

class ScoreBreakdown(BaseModel):
    design_fit: float            # weight 40%
    complexity_match: float      # weight 30%
    inferred_demographics: float # weight 15%
    budget_fit: float            # weight 10%
    inventory_available: bool    # weight 5% (pass/fail)

class MockupHint(BaseModel):
    suggested_color: str         # must match a value in inventory.colors
    suggested_size: str | None   # must match a value in inventory.sizes; None if one-size
    placement: str | None        # e.g. "center_chest"

class ProductRecommendation(BaseModel):
    rank: int
    product_id: str
    product_name: str
    score: float                 # 0.0–1.0 weighted composite
    score_breakdown: ScoreBreakdown
    reasons: list[str]
    price_paise: int
    print_area_width_in: float
    print_area_height_in: float
    production_time_minutes: int
    mockup_hint: MockupHint
    units_available: int         # live from inventory; show "low stock" warning if < 5
```

---

## Migration Strategy

- All schema changes via Alembic (`alembic revision --autogenerate`)
- Migration files committed to `backend/app/db/migrations/`
- `alembic upgrade head` runs on every deploy
- No manual SQL in production; all DDL through migrations

## Seed Data

Initial `inventory` rows seeded from `docs/BOBB_Backend_Architecture_v1.md` product catalog:
- tshirt_premium, tshirt_standard, tote_canvas, cap_snapback, phone_case, laptop_skin, keychain, water_bottle, flipflops, helmet_sticker
