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
    device_id       VARCHAR(50)    -- tablet identifier
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
    input_type      VARCHAR(10) NOT NULL CHECK (input_type IN ('text', 'voice')),
    customer_input  TEXT NOT NULL,
    agent_response  TEXT,               -- raw Claude response
    story_extracted JSONB,              -- structured Story JSON (see below)
    clarification_needed BOOLEAN NOT NULL DEFAULT false,
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
    story_json          JSONB NOT NULL,          -- Story extracted by Conversation Agent
    design_prompt_base  TEXT NOT NULL,           -- Master prompt from Design Agent
    design_metadata     JSONB,                   -- complexity, cultural_refs, color_count
    selected_variant    SMALLINT CHECK (selected_variant BETWEEN 1 AND 4),
    refinements_count   SMALLINT NOT NULL DEFAULT 0,
    design_locked       BOOLEAN NOT NULL DEFAULT false,
    locked_at           TIMESTAMPTZ
);

CREATE INDEX idx_designs_session ON designs(session_id);
```

---

### `design_variants`

Each of the 4 (or refined) image variants for a design.

```sql
CREATE TABLE design_variants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    design_id       UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    variant_number  SMALLINT NOT NULL CHECK (variant_number BETWEEN 1 AND 4),
    prompt_used     TEXT NOT NULL,           -- exact prompt sent to image gen
    style           VARCHAR(30),             -- illustration | geometric | watercolor | minimalist
    image_url       TEXT,                    -- local cache path or external URL
    image_path      TEXT,                    -- filesystem path
    generation_time_ms  INT,
    model_used      VARCHAR(80),             -- e.g. fal-ai/flux/dev
    is_selected     BOOLEAN NOT NULL DEFAULT false,
    is_refined      BOOLEAN NOT NULL DEFAULT false,
    parent_variant_id UUID REFERENCES design_variants(id)  -- refinement chain
);

CREATE INDEX idx_variants_design ON design_variants(design_id);
```

---

### `product_recommendations`

AI-generated product recommendations per design.

```sql
CREATE TABLE product_recommendations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    design_id       UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    recommendations JSONB NOT NULL,  -- array of {rank, product_id, score, reasons, price}
    model_used      VARCHAR(50),
    response_time_ms INT
);

CREATE INDEX idx_recs_session ON product_recommendations(session_id);
```

**`recommendations` shape**:
```json
[
  {
    "rank": 1,
    "product_id": "tshirt_premium",
    "score": 0.87,
    "reasons": ["Design fit: illustration", "Perfect complexity match: medium"],
    "price_paise": 65000,
    "print_area": "10x12 inches",
    "production_time_minutes": 7
  }
]
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

class Story(BaseModel):
    themes: list[str]
    emotions: list[str]
    keywords: list[str]
    cultural_refs: list[str]
    design_complexity: Literal["simple", "medium", "complex"]
    intent: str
    needs_clarification: bool = False
    clarification_questions: list[str] = []

class DesignVariant(BaseModel):
    variant_number: int        # 1–4
    style: str                 # illustration | geometric | watercolor | minimalist
    prompt_used: str
    image_url: str | None
    generation_time_ms: int | None

class ProductRecommendation(BaseModel):
    rank: int
    product_id: str
    product_name: str
    score: float               # 0.0–1.0
    reasons: list[str]
    price_paise: int
    print_area: str
    production_time_minutes: int
    mockup_hint: str | None    # color/size suggestion for mockup render
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
