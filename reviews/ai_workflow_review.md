# BOBB AI Platform — AI Workflow Review

**Reviewer**: Principal Architect / Technical Lead  
**Date**: 2026-06-11  
**Scope**: Pre-Sprint-1 review of the full AI agent pipeline  
**Input documents**: architecture.md, database_schema.md, api_contracts.md,  
  docs/BOBB_Agents_Implementation.py, docs/BOBB_Product_Agent_System_Prompts.md,  
  docs/BOBB_Gemini_Master_System_Prompt.md  
**Focus**: Observability · Debugging · Maintainability · Future extensibility

---

## Executive Summary

The AI workflow is structurally sound at the macro level — three agents in sequence, each with a clear responsibility boundary. However, the **inter-agent data contracts are underspecified** at the point that matters: the exact JSON schema Claude is asked to produce and what the application code does when that schema doesn't come back cleanly. Several schemas have ambiguous types, uncontrolled vocabularies, and missing fields that will make the pipeline opaque in production. The observability design captures the right *metrics* but lacks the *correlation* needed to trace a customer's journey across agents. Six issues are blocking; twelve are significant for long-term health.

---

## 1. Agent Orchestration

### AW-01 — Orchestrator has no formal pipeline definition
**Severity**: HIGH · **Affects**: Maintainability, debuggability

The orchestrator is described as "manages agent call sequence and context threading." There is no formal pipeline model — no explicit list of steps, no step names, no step-level isolation. The current implied shape is:

```
run_story_pipeline():
    story  = conversation_agent.extract_story()
    prompts = design_agent.generate_prompts(story)
    images  = image_service.generate(prompts)
    db.save(design, variants)
```

This is a synchronous chain of function calls. The problems this creates:

- **No step checkpointing**: If `generate_prompts()` succeeds but `generate()` times out, there is no record that prompts were already produced. On retry, the Design Agent is called again — at cost.
- **No per-step span**: All three agent calls log to `agent_logs` with only `session_id` + `agent_name`. There is no `pipeline_run_id` to group them into a single trace. You cannot compute "what fraction of pipeline time was spent in each step" without correlating timestamps manually.
- **No step-level retry policy**: The architecture says "1 retry then raise." But different steps have different retry profiles — a transient 429 from Anthropic should retry with exponential backoff; a deterministic Claude JSON parse failure should not retry blindly.

**Recommendation**: Define the pipeline as a first-class data structure before implementing:

```python
STORY_PIPELINE: list[PipelineStep] = [
    PipelineStep(
        name="conversation",
        fn=conversation_agent.extract_story,
        timeout_s=8,
        retry=RetryPolicy(max_attempts=2, backoff_s=1, on=[RateLimitError]),
        fallback=FallbackStory.from_guided_input,
    ),
    PipelineStep(
        name="design",
        fn=design_agent.generate_prompts,
        timeout_s=10,
        retry=RetryPolicy(max_attempts=2, backoff_s=2, on=[RateLimitError]),
        fallback=FallbackDesign.from_kerala_theme,
    ),
    PipelineStep(
        name="image_gen",
        fn=image_service.generate,
        timeout_s=60,
        retry=RetryPolicy(max_attempts=1, backoff_s=5, on=[TimeoutError]),
        fallback=None,  # partial results acceptable; see AW-04
    ),
]
```

Each step receives a `PipelineContext` containing `session_id`, `pipeline_run_id`, and the outputs of all prior steps. This makes step isolation, per-step timing, and per-step fallback implementable without restructuring the orchestrator each time a new step is added.

---

### AW-02 — No pipeline_run_id; agent calls cannot be correlated across a single flow
**Severity**: HIGH · **Affects**: Observability, debugging

`agent_logs` rows have `session_id` and `agent_name`. A session that goes through THINKING twice (once for initial generation, once for "try different") will have two `design` rows and two `image_gen` rows, all sharing the same `session_id`. There is no way to know which design agent call produced which image set.

Additionally, during a refinement, the Design Agent is called a third time. `agent_logs` will show three `design` rows for a session with no ordering beyond `created_at`, and no link to the specific `design_variants` rows they produced.

**Recommendation**: Add `pipeline_run_id UUID` to `agent_logs` and to `designs`:

```sql
ALTER TABLE agent_logs ADD COLUMN pipeline_run_id UUID;
ALTER TABLE designs     ADD COLUMN pipeline_run_id UUID;
```

The orchestrator generates a new `pipeline_run_id` at the start of each pipeline invocation (initial generation, each "try different", each refinement). Every agent call within that invocation uses the same `pipeline_run_id`. This makes "show me everything that happened for the generation that produced variant 3" a single indexed query.

---

### AW-03 — No system prompt version tracking
**Severity**: HIGH · **Affects**: Debuggability, maintainability

System prompts live in `prompts/*.txt` files. They are loaded at startup. `agent_logs` records `model_used` but not which version of the system prompt was active at call time. If a prompt change causes degraded Story extraction or poor design prompts three days after deployment, you cannot go back and compare "what did this agent produce with the old prompt vs the new prompt" on historical data.

**Recommendation**: Add `prompt_version VARCHAR(40)` to `agent_logs`. At startup, compute a SHA-1 of each loaded system prompt file and store it as `CONVERSATION_PROMPT_VERSION`, `DESIGN_PROMPT_VERSION`, `PRODUCT_PROMPT_VERSION` in application config. Each agent call logs its prompt version. This is a single field that costs nothing to add and makes prompt regression analysis possible.

```python
# On startup:
import hashlib
CONVERSATION_PROMPT_SHA = hashlib.sha1(
    open("prompts/conversation.txt", "rb").read()
).hexdigest()[:8]  # "a3f7b2c1"
```

No external versioning system needed. The Git commit hash is not sufficient because prompts may be tweaked on disk without a commit during live tuning.

---

### AW-04 — Fallback behaviours are named but not specified
**Severity**: MEDIUM · **Affects**: Maintainability, observability

Architecture review ISSUE-06 called for fallback behaviours per agent. The plan was accepted. But nowhere in any document is the fallback behaviour *specified*: what does `FallbackStory.from_guided_input` actually return? What's the exact JSON? What Kerala theme canonical prompt does `FallbackDesign.from_kerala_theme` select? Without specifying these:

- Fallback paths will be implemented inconsistently across sprints
- Monitoring cannot distinguish "real success" from "fallback success" — both look like a delivered design
- Fallback quality cannot be evaluated or improved

**Recommendation**: Add a section to `architecture.md` — "Fallback Catalogue" — that specifies the exact output each fallback returns. At minimum:

| Agent | Trigger | Fallback output | `is_fallback` flag |
|---|---|---|---|
| ConversationAgent | API error / timeout | `Story{themes:["Kerala"],emotions:["joy"],complexity:"medium",…}` | true |
| DesignAgent | API error / timeout | Canonical prompt from Kerala theme matrix (keyed by story.themes[0]) | true |
| ImageGenService | 2+ variants fail | Return succeeded variants (min 1); mark failed slots as null | partial |

The `is_fallback: bool` field must be added to both `designs` and `design_variants` so that fallback sessions can be filtered out of quality metrics.

---

## 2. Story Intelligence Output Schema

### AW-05 — Story schema uses free-form strings where controlled vocabulary is needed
**Severity**: HIGH · **Affects**: Design Agent quality, product scoring, analytics

The `Story.themes` and `Story.cultural_refs` fields are `list[str]`. Claude will produce these:

```json
// Customer 1 says "I love the backwaters of Kerala"
{ "themes": ["backwaters", "Kerala", "water"] }

// Customer 2 says "I grew up near the backwaters"
{ "themes": ["backwaters", "childhood memories", "serene water"] }
```

These two customers have the same core theme. But the Design Agent receives different string tokens, the product scoring algorithm gets different strings, and analytics `top_design_theme` will split the count across "backwaters", "water", "serene water".

The Kerala theme matrix in `docs/` defines exactly **8 primary themes** and **10 secondary themes**. These should be the canonical vocabulary.

**Recommendation**: Define `KeralaTheme` and `DesignTheme` enums in the schema. Ask Claude to classify into these:

```python
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
    NONE             = "none"  # story has no Kerala reference

class Story(BaseModel):
    themes: list[str]           # free-form universal themes (e.g. "family", "music")
    kerala_themes: list[KeralaTheme]   # from controlled vocabulary; [] if none
    emotions: list[str]
    keywords: list[str]         # verbatim key phrases from customer text (max 8)
    design_complexity: Literal["simple", "medium", "complex"]
    intent: Intent              # enum, not str
    needs_clarification: bool = False
    clarification_questions: list[str] = []
    # Fields for observability:
    clarity_score: float        # 0.0–1.0; logged for quality monitoring
    confidence: float           # 0.0–1.0; logged, triggers clarification if < 0.6
    raw_customer_text: str      # verbatim; used for replay and audit
    is_fallback: bool = False
```

The system prompt must instruct Claude to populate `kerala_themes` using **only** values from the enum list. Validation happens in Pydantic — any unrecognised value fails fast with a clear error, not a silent degradation.

---

### AW-06 — No validation contract between Claude's JSON output and Pydantic schema
**Severity**: HIGH · **Affects**: Reliability, debugging

The docs' agent implementation uses:
```python
try:
    story_json = json.loads(response_text)
except json.JSONDecodeError:
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    story_json = json.loads(json_match.group()) if json_match else self._parse_fallback(response_text)
```

Three failure modes, one of which is completely silent:
1. `json.loads()` succeeds but the JSON has the wrong shape → Pydantic model construction fails elsewhere, far from the agent call
2. Regex extraction succeeds but gets a partial object → silent data truncation, `themes` may be empty
3. Both fail → `_parse_fallback()` returns `themes: ["generic"]` and proceeds as normal

**There is no point at which Claude's output is validated against the expected schema before it is used downstream.**

**Recommendation**: Use Anthropic's structured output / tool-use pattern to enforce the schema at the API call level. Claude returns a JSON object that matches a JSON Schema you provide — if it doesn't, the API returns an error rather than free text.

```python
# Use tool_use / tools parameter to force structured output:
response = client.messages.create(
    model="claude-sonnet-4-6",
    system=system_prompt,
    messages=messages,
    tools=[{
        "name": "submit_story",
        "description": "Submit the extracted story in structured format",
        "input_schema": Story.model_json_schema()
    }],
    tool_choice={"type": "tool", "name": "submit_story"}
)
story = Story.model_validate(response.content[0].input)
```

This eliminates the `json.loads()` + regex fallback entirely. If the model can't produce a valid `Story`, you get a structured error, not silent garbage downstream. Every planning document that mentions "structured output via response_format or prompt-enforced JSON" should now read: **use tool_use with a JSON Schema; never parse Claude's text output with regex**.

---

### AW-07 — `design_complexity` classification has no objective criteria defined
**Severity**: MEDIUM · **Affects**: Product scoring accuracy, Design Agent prompt quality

Claude must classify design complexity as `simple`, `medium`, or `complex`. This classification drives 30% of the product recommendation score. Yet nowhere — not in the system prompt spec, not in the docs — is the classification criteria defined. Claude will classify arbitrarily and inconsistently.

Example ambiguity:
- "A palm tree silhouette" — simple or medium?
- "A Theyyam dancer with geometric border" — medium or complex?
- "Sunset over backwaters with three fishing boats and Sanskrit calligraphy" — complex or very complex?

**Recommendation**: Add explicit classification criteria to the Conversation Agent system prompt:

```
COMPLEXITY CLASSIFICATION RULES:
- simple:  1-2 visual elements, single focal point, flat/minimal color, no text
- medium:  3-5 elements, clear hierarchy, 3-4 colors, optional short text
- complex: 6+ elements, detailed scene/pattern, 5+ colors, multilayer composition

CALIBRATION EXAMPLES:
- "A single coconut palm silhouette" → simple
- "Theyyam dancer with decorative border" → medium  
- "Full Kathakali scene with landscape background and Malayalam text" → complex
```

These examples should come from the docs' Kerala cultural research — they already have complexity analysis per product. Pin these examples to the system prompt verbatim.

---

### AW-08 — `ConversationTurn` type used in ISSUE-01 fix is not defined in any schema
**Severity**: MEDIUM · **Affects**: Sprint 2 implementation correctness

The architecture fix for ISSUE-01 defines:
```python
async def extract_story(
    self,
    new_input: str,
    session_id: str,
    prior_turns: list[ConversationTurn],
) -> Story: ...
```

`ConversationTurn` is referenced but never defined. The implementation will likely use a raw dict from the DB query, leading to inconsistent field access (`turn["customer_input"]` vs `turn.customer_input`). More importantly, `conversation_logs.agent_response` stores the raw Claude response (which in later turns may be JSON, clarification questions, or error text). The orchestrator needs to know: **which field of the log row should be replayed as the assistant turn?**

**Recommendation**: Define `ConversationTurn` explicitly in `database_schema.md` Pydantic schemas:

```python
class ConversationTurn(BaseModel):
    turn_number: int
    customer_input: str          # always the user message
    agent_text_response: str | None  # the assistant message (clarification Q or ack)
    # agent_text_response is what gets replayed as {"role": "assistant", "content": ...}
    # It is DISTINCT from story_extracted — never replay the JSON blob as assistant text
```

`conversation_logs` needs a dedicated column for the assistant's conversational text, separate from `agent_response` (which currently mixes the full Claude response including JSON). Add:

```sql
ALTER TABLE conversation_logs
  ADD COLUMN agent_text_reply TEXT;  -- only the human-readable part (clarification Q or ack)
  -- agent_response retains the full raw response for debugging
```

---

## 3. Design Strategy Output Schema

### AW-09 — Design Agent returns a single prompt string; 4 variant schema is undefined
**Severity**: HIGH · **Affects**: Sprint 3 correctness, image gen quality, debugging

The docs' `DesignAgent.translate_story()` returns `str` — a single prompt string. The system prompt asks Claude to produce a JSON structure with `design_prompt`, `variants: [...]`, `design_metadata`, and `refinement_suggestions`. But `_extract_design_prompt()` discards the JSON and joins raw text lines. The 4 variant prompts that `image_gen.generate()` needs to receive are never defined as a type anywhere.

**Recommendation**: Define `VariantPrompt` and `DesignStrategy` as explicit types, and make `generate_prompts()` return a structured `DesignStrategy`:

```python
class VariantPrompt(BaseModel):
    style: Literal["illustration", "geometric", "watercolor", "minimalist"]
    prompt: str                  # full SDXL-compatible prompt
    negative_prompt: str         # what to exclude (SDXL quality critical)
    color_palette: list[str]     # hex codes or named colors
    mood: str                    # descriptive mood tag for UI display
    width: int                   # product-specific (from ProductHint)
    height: int

class DesignStrategy(BaseModel):
    base_story_summary: str      # 1-sentence design brief for display/logging
    variants: list[VariantPrompt]  # exactly 4
    design_metadata: DesignMetadata
    is_fallback: bool = False

class DesignMetadata(BaseModel):
    cultural_authenticity_score: float   # 0.0–1.0
    print_feasibility: Literal["excellent", "good", "marginal", "poor"]
    color_count: int
    complexity: Literal["simple", "medium", "complex"]
    estimated_print_time_min: float
    kerala_themes_used: list[KeralaTheme]  # from Story; echoed here for audit
```

`designs.design_prompt_base TEXT` in the DB should store the `DesignStrategy` serialised as JSONB — not just the base prompt string — so the full strategy is recoverable for debugging. Add `design_strategy_json JSONB` to the `designs` table.

---

### AW-10 — Variant style list inconsistent across documents
**Severity**: MEDIUM · **Affects**: Sprint 3, frontend display, testing

The variant styles are specified as three different sets across documents:

| Document | Styles |
|---|---|
| architecture.md (Design Agent) | illustration, geometric, watercolor, minimalist |
| docs/BOBB_Agents_Implementation.py system prompt | illustration, geometric, **photorealistic**, watercolor |
| docs/BOBB_Product_Agent_System_Prompts.md | not specified |

`minimalist` and `photorealistic` are mutually exclusive options filling the same slot 3 position. This inconsistency will cause:
- Frontend to render a "minimalist" label while the backend generates a photorealistic image
- Tests written against one set to fail when code uses the other

**Resolution**: Choose `minimalist` over `photorealistic` for MVP. Rationale: photorealistic images are harder to print cleanly on DTF fabric (colour banding, gradient issues), and the docs' design thinking research explicitly recommends illustration/geometric/minimalist for Kerala themes. Document this decision in `CLAUDE.md` agent design section. Update `VariantPrompt.style` to use a `Literal` type so the mismatch is caught at schema validation time, not at runtime.

---

### AW-11 — No negative prompts defined; SDXL/FLUX output quality will be unpredictable
**Severity**: HIGH · **Affects**: Image generation quality

Neither the Design Agent output schema nor the `ImageGenerationService` interface carries a `negative_prompt`. For SDXL-family and FLUX models, the negative prompt is as important as the positive prompt for print-quality output. Without a negative prompt:

- "blurry, low quality, watermark, text, distorted, extra limbs" will all appear in generated images
- Thin lines (which DTF cannot print) will not be suppressed
- NSFW guardrails are fully dependent on the model's default behaviour

**Recommendation**: The Design Agent must produce a `negative_prompt` per variant. The base negative prompt for print designs should be defined as a constant and extended per variant:

```python
BASE_NEGATIVE_PROMPT = (
    "blurry, low quality, jpeg artifacts, watermark, signature, text overlay, "
    "thin lines under 2px, gradient mesh, photographic grain, overexposed, "
    "underexposed, distorted anatomy, extra limbs, nsfw"
)

STYLE_NEGATIVE_PROMPTS = {
    "illustration": "photorealistic, 3d render, photograph",
    "geometric":    "organic shapes, photorealistic, gradient backgrounds",
    "watercolor":   "digital art, sharp edges, high contrast",
    "minimalist":   "cluttered, busy background, multiple focal points",
}
```

The full `negative_prompt` for each variant = `BASE_NEGATIVE_PROMPT + " " + STYLE_NEGATIVE_PROMPTS[style]`. This must be a field on `VariantPrompt` and passed through to `ImageGenerationService.generate()`.

---

## 4. Image Generation Request Schema

### AW-12 — `ImageResult` type is never defined
**Severity**: HIGH · **Affects**: Sprint 3, contract between image service and orchestrator

The `ImageGenerationService.generate()` returns `list[ImageResult]`. `ImageResult` appears in no planning document — no Pydantic schema, no DB schema section. The orchestrator, which must map each result to a `design_variants` DB row, has no typed contract for what it receives.

**Recommendation**: Define `ImageResult` explicitly:

```python
class ImageResult(BaseModel):
    variant_number: int          # 1–4
    style: str                   # echoed from VariantPrompt.style
    image_path: str              # absolute local path: cache/designs/{session_id}/v{n}.png
    image_url: str               # relative URL served by StaticFiles: /cache/designs/…
    prompt_used: str             # full positive prompt sent to fal.ai
    negative_prompt_used: str    # full negative prompt sent to fal.ai
    model_used: str              # e.g. "fal-ai/flux/dev"
    fal_request_id: str | None   # fal.ai's own request ID for their support/billing lookup
    generation_time_ms: int
    seed: int | None             # if fal.ai returns a seed, store it for reproducibility
    success: bool
    error: str | None            # populated if success=False, None otherwise
```

`fal_request_id` and `seed` are critical for production debugging: if a customer complains "the design was offensive," you need to contact fal.ai with their request ID. If you want to reproduce a variant exactly, you need the seed.

---

### AW-13 — Image generation dimensions are hardcoded; product-specific sizes not passed through
**Severity**: MEDIUM · **Affects**: Print quality, ComfyUI migration

`image_gen.generate()` always produces 1024×1024. The product print areas from the docs are not square:

| Product | Print area | Aspect ratio |
|---|---|---|
| T-shirt | 10×12" | 5:6 → 1024×1229px |
| Tote | 10×10" | 1:1 → 1024×1024px |
| Water bottle | 4×6" wrap | 2:3 → 683×1024px |
| Laptop skin | 13×9" | 13:9 → 1024×709px |
| Cap front | 3.5×2.5" | 7:5 → 1024×731px |

Generating a 1:1 image for a t-shirt (5:6) means either the top/bottom are cropped or the design is letterboxed. Neither is acceptable for a product that will be physically printed and worn.

**Recommendation**: `GenerationParams` (already proposed in architecture review ISSUE-25) must carry `width` and `height`:

```python
@dataclass
class GenerationParams:
    variants: list[VariantPrompt]
    width: int                   # from products.print_area_width_in × 102 (≈300dpi equiv)
    height: int
    product_type: str
    workflow_overrides: dict = field(default_factory=dict)
```

Add `print_area_width_in NUMERIC(4,2)` and `print_area_height_in NUMERIC(4,2)` to the `products` table (replacing the string `print_area`). The `Design Agent` must receive these from a `ProductHint` before generating prompts (architecture review ISSUE-02). The circle closes: product → dimensions → prompts → images, all consistent.

---

## 5. Product Recommendation Schema

### AW-14 — `score` is opaque; `mockup_hint` is a string with no format contract
**Severity**: MEDIUM · **Affects**: Debugging, frontend, maintainability

Two fields in `ProductRecommendation` lack sufficient specification:

**`score: float`** — How it's computed matters for debugging. When a customer picks the third-ranked product, why wasn't the top-ranked better? There is no `score_breakdown` showing the contribution of each factor. This makes product recommendation quality entirely invisible.

**`mockup_hint: str | None`** — What is the format? The frontend must render the product mockup using this hint. If the format is `"black/L"` (color/size) vs `"navy"` (color only) vs `"L"` (size only) vs `"black t-shirt size L for male"` (free text), the frontend cannot write a parser for it.

**Recommendation**: Expand the schema:

```python
class ScoreBreakdown(BaseModel):
    design_fit: float           # 0.0–1.0, weight 40%
    complexity_match: float     # 0.0–1.0, weight 30%
    inferred_demographics: float # 0.0–1.0, weight 15%
    budget_fit: float           # 0.0–1.0, weight 10%
    inventory_available: bool   # pass/fail, weight 5%

class MockupHint(BaseModel):
    suggested_color: str        # e.g. "black" — must be in products.colors
    suggested_size: str | None  # e.g. "M" — must be in products.sizes; None if one_size
    placement: str | None       # e.g. "center_chest" for t-shirts

class ProductRecommendation(BaseModel):
    rank: int
    product_id: str
    product_name: str
    score: float
    score_breakdown: ScoreBreakdown  # replaces opaque float with auditable components
    reasons: list[str]
    price_paise: int
    print_area_width_in: float    # structured, not "10x12 inches" string
    print_area_height_in: float
    production_time_minutes: int
    mockup_hint: MockupHint     # structured, not free-form string
    units_available: int        # live from inventory; shown as "low stock" if < 5
```

`score_breakdown` makes it possible to answer "why did the tote score higher than the t-shirt?" in a support conversation or for prompt debugging.

---

### AW-15 — Product catalog injected into Claude prompt; catalog drift is a risk
**Severity**: MEDIUM · **Affects**: Maintainability, future product additions

Architecture review ISSUE-03 recommended replacing Claude with a deterministic scorer. If the scorer remains Claude-assisted for enriching reasons copy (the accepted path), the product catalog must be injected into the system prompt. The catalog in `inventory` can change (new products added, prices updated, products deactivated). The system prompt, loaded at startup, will be stale.

**Recommendation**: Do not inject the full catalog into the static system prompt file. Instead, build the product context dynamically at call time by querying `SELECT * FROM products WHERE is_active = true` and formatting it as a context block. The deterministic scorer uses the DB directly. Claude (if used only for `reasons`) receives the dynamically-built context. System prompt files contain only reasoning instructions, never data that changes independently.

---

## 6. Data Persistence Between Agents

### AW-16 — Story is stored in two places with no canonical source
**Severity**: HIGH · **Affects**: Data integrity, debuggability

The customer's story is persisted as:
1. `conversation_logs.story_extracted JSONB` — written after each Conversation Agent call
2. `designs.story_json JSONB` — written when the design is created

These are two separate copies. If the customer clarifies (turn 2), `conversation_logs` gets a second row with a new `story_extracted`. But `designs.story_json` is written once at design creation time. If the design is created after turn 1 but before the customer's clarification in turn 2, `designs.story_json` is stale.

There is also a third in-memory representation: the `Story` Python object passed from the Conversation Agent to the Design Agent in the orchestrator's scope. If the DB write fails mid-pipeline but the pipeline continues in memory, the DB state diverges from the in-memory state.

**Recommendation**: Establish a single canonical source:

- `designs.story_json` is the **authoritative** story used for design generation — written once at design creation, from the final `Story` object after all clarifications are complete.
- `conversation_logs.story_extracted` is the **per-turn snapshot** — written after each turn, useful for turn-level debugging but not the design source.
- The orchestrator must only call `DesignAgent` after the final `Story` is persisted to `designs.story_json`. No in-memory-only story objects should cross agent boundaries.
- Add `story_version INT NOT NULL DEFAULT 1` to `designs` — incremented if "try different" forces a re-extraction (future scenario where story can be re-elicited).

---

### AW-17 — Design Agent intermediate output (4 variant prompts) is not persisted before image generation
**Severity**: HIGH · **Affects**: Debugging, cost efficiency, replay

The pipeline is: `DesignAgent.generate_prompts(story) → [4 prompts] → ImageService.generate([4 prompts])`. The 4 variant prompts exist only in memory between these two calls. They are written to `design_variants.prompt_used` *after* image generation completes. If image generation fails mid-way (2 of 4 complete), the prompts for the 2 failed variants are lost.

More importantly: if you want to debug "why did this design turn out badly?", you need to see the exact prompt the Design Agent produced — but all you can see is what was sent to fal.ai (which may have been truncated or post-processed).

**Recommendation**: Persist the `DesignStrategy` (from AW-09) to `designs.design_strategy_json` *before* invoking the image service. This makes the Design Agent's output durable and recoverable:

```
Pipeline order:
1. story  = ConversationAgent.extract_story(...)
2. db.save(designs, story_json=story)         ← persist story
3. strategy = DesignAgent.generate_prompts(story)
4. db.update(designs, design_strategy_json=strategy)  ← persist prompts BEFORE images
5. images = ImageService.generate(strategy.variants)
6. db.save(design_variants, images)           ← persist results
```

Step 4 ensures that if step 5 fails, you can inspect exactly what prompts were generated, retry image generation with the same prompts (no extra Claude call cost), and compare strategy outputs across sessions.

---

### AW-18 — Agent handoff uses lossy dict serialisation
**Severity**: MEDIUM · **Affects**: Design quality, debuggability

The docs' `DesignAgent.translate_story()` builds a context dict:
```python
story_context = {
    "themes":              ", ".join(story.get("themes", [])),
    "emotions":            ", ".join(story.get("emotions", [])),
    "keywords":            ", ".join(story.get("keywords", [])),
    "cultural_references": ", ".join(story.get("cultural_references", [])),
    "complexity":          story.get("design_complexity", "medium")
}
```

This is a lossy string join. `["beach", "Kannur", "hometown"]` becomes `"beach, Kannur, hometown"`. The Design Agent's user message then embeds these as flat strings. There is no structure for Claude to reason about the *relative weight* of themes (is "Kannur" a stronger theme than "beach"?), or which cultural references are Kerala-specific vs generic.

**Recommendation**: Pass the full `Story` object as structured JSON in the Design Agent's user message, not a flat string join. Claude can reason over structured JSON directly:

```python
user_message = f"""Design for this customer story:

{story.model_dump_json(indent=2)}

Product constraints:
{product_hint.model_dump_json(indent=2)}

Generate exactly 4 variant prompts using the submit_design_strategy tool."""
```

Keeping the full structure in the prompt gives Claude: the ordered list of themes (implied priority), the `is_fallback` flag (so it knows to be more conservative), the `kerala_themes` enum list (for correct cultural mapping), and the `raw_customer_text` (for grounding the design in the customer's own words). This is materially better for design quality than a comma-joined string.

---

## 7. Future Support for Additional Products and Agents

### AW-19 — No product registry; adding a new product requires changes in multiple places
**Severity**: MEDIUM · **Affects**: Extensibility, maintainability

Adding a new product (e.g., mug, yoga mat) currently requires changes in:
1. `inventory` DB seed (or admin insert)
2. `products` table (post ISSUE-09 split)
3. `PRODUCT_CATALOG` constant in agent code
4. Design Agent system prompt (new print constraints)
5. `GenerationParams` width/height logic
6. `ProductRecommendationEngine` scoring

There is no single place that describes a product for the system. The design thinking research in `/docs/` has detailed per-product specifications (`BOBB_Product_Agent_System_Prompts.md` has 10 ready system prompts), but they live in markdown, not in a queryable form.

**Recommendation**: Create a `ProductConfig` registry loaded at startup:

```python
@dataclass
class ProductConfig:
    product_id: str
    name: str
    print_width_in: float
    print_height_in: float
    print_method: str           # dtf | sublimation | uv | vinyl | embroidery
    design_system_prompt: str   # loaded from prompts/products/{product_id}.txt
    complexity_range: tuple[str, str]
    design_fit_scores: dict[str, float]
    negative_prompt_additions: str  # product-specific exclusions

PRODUCT_REGISTRY: dict[str, ProductConfig] = load_all_products()
```

The 10 system prompts in `/docs/BOBB_Product_Agent_System_Prompts.md` can be extracted to `prompts/products/{product_id}.txt` immediately. The `ProductRecommendationEngine` reads from `PRODUCT_REGISTRY` at runtime. Adding a new product means: add a DB row, add a `prompts/products/new_product.txt` file, restart. No code changes.

---

### AW-20 — No agent capability registry; orchestrator is hard-coded to 3 agents
**Severity**: LOW (MVP) · MEDIUM (Phase 2) · **Affects**: Future extensibility

The orchestrator has exactly 3 hardcoded agent calls. When new agents are added (Quality Check Agent that reviews generated images, Voice Transcription Agent, Loyalty Agent), they must be manually wired into the orchestrator. There is no way to add an agent without modifying orchestrator code.

**Recommendation**: Not a Sprint 1 concern, but document the extension pattern now so future agents are built to fit:

```
Agent interface (for any future agent):
- Must implement: async process(ctx: PipelineContext) -> PipelineContext
- Must declare: INPUT_KEY (which context field it reads from)
- Must declare: OUTPUT_KEY (which context field it writes to)
- Must register: in PIPELINE_REGISTRY

PipelineContext is the shared state bag:
- session_id, pipeline_run_id
- story: Story | None
- design_strategy: DesignStrategy | None
- images: list[ImageResult] | None
- recommendations: list[ProductRecommendation] | None
- [future keys added without breaking existing agents]
```

This is a simple publish/subscribe over a dict-like context object. Each agent reads what it needs and writes what it produces. The orchestrator executes agents in declared dependency order. New agents slot in without touching existing agent code.

---

### AW-21 — No prompt A/B testing or canary mechanism
**Severity**: LOW · **Affects**: Maintainability, quality improvement

All sessions in production use the same system prompt. There is no mechanism to:
- Test a new conversation prompt on 10% of sessions
- Compare design quality between two prompt versions
- Roll back a prompt change that degraded output quality

This matters because prompt engineering is an iterative process. After launch, the team will want to tune prompts based on real customer data. Without a framework for controlled experiments, every prompt change is a production risk.

**Recommendation**: Implement a minimal `PromptVariant` flag in the session:
```sql
ALTER TABLE sessions ADD COLUMN prompt_variant VARCHAR(20) DEFAULT 'v1';
```
At session creation, assign variant based on a simple hash of `session_id % 100 < CANARY_PERCENT`. Load the appropriate prompt version per session. This costs one config field and enables data-driven prompt improvement from day one.

---

## Observability Design Assessment

### What the current design captures well
- `agent_logs`: tokens in/out, execution time, model, error codes per call ✓
- `design_variants.prompt_used`: exact prompt sent to image generation ✓
- `design_variants.generation_time_ms`: per-variant timing ✓
- `session.duration_seconds`, `satisfaction_score`: session-level outcomes ✓
- `analytics`: daily aggregates for business metrics ✓

### What is missing (must add before Sprint 1)

| Missing signal | Where to add | Why it matters |
|---|---|---|
| `pipeline_run_id` | `agent_logs`, `designs` | Correlate all calls for one generation attempt |
| `prompt_version` | `agent_logs` | Know which system prompt produced which output |
| `is_fallback` | `designs`, `design_variants` | Filter fallback sessions from quality metrics |
| `fal_request_id` | `design_variants` | Contact fal.ai support for specific failures |
| `seed` | `design_variants` | Reproduce exact generation for debugging |
| `story.clarity_score` | `conversation_logs` | Track conversation quality over time |
| `story.confidence` | `conversation_logs` | Alert when Conversation Agent is uncertain |
| `score_breakdown` | recommendations JSONB | Debug product recommendation scoring |
| `agent_text_reply` | `conversation_logs` | Separate conversational response from JSON blob |
| `design_strategy_json` | `designs` | Full 4-prompt strategy before image gen |

---

## Debugging Capability Assessment

The most important debugging question for a retail kiosk is: **"Why did this customer's design look bad?"** The ability to answer it depends on which artifacts are stored.

| Debug scenario | Answerable with current design? |
|---|---|
| What story did the Conversation Agent extract? | ✓ (`conversation_logs.story_extracted`) |
| What prompt did the Design Agent produce? | ✗ (not stored before image gen; only after) |
| What exact prompt was sent to fal.ai? | ✓ (`design_variants.prompt_used`) |
| What negative prompt was used? | ✗ (not stored anywhere) |
| Which system prompt version was active? | ✗ (no prompt versioning) |
| How long did each agent step take this run? | ✗ (no `pipeline_run_id` to group logs) |
| Was a fallback used? | ✗ (no `is_fallback` flag) |
| Can we replay this exact generation? | ✗ (no seed, no full strategy JSON) |
| Did this session use the canary prompt? | ✗ (no `prompt_variant` on session) |

After the fixes in this review, all of the above become answerable.

---

## Summary Table

| # | Issue | Severity | Primary concern |
|---|---|---|---|
| AW-01 | No formal pipeline definition; no per-step isolation | HIGH | Maintainability |
| AW-02 | No `pipeline_run_id`; agent calls unorrelated | HIGH | Observability |
| AW-03 | No system prompt version tracking | HIGH | Debuggability |
| AW-04 | Fallback behaviours named but unspecified | MEDIUM | Maintainability |
| AW-05 | Story schema uses free-form strings; no controlled vocabulary | HIGH | Design quality, analytics |
| AW-06 | No validation contract between Claude output and Pydantic | HIGH | Reliability |
| AW-07 | `design_complexity` has no classification criteria | MEDIUM | Scoring accuracy |
| AW-08 | `ConversationTurn` type undefined; `agent_text_reply` missing | MEDIUM | Sprint 2 correctness |
| AW-09 | Design Agent returns `str`; `VariantPrompt`/`DesignStrategy` undefined | HIGH | Sprint 3 correctness |
| AW-10 | Variant style list inconsistent across documents | MEDIUM | Frontend, testing |
| AW-11 | No negative prompts anywhere in the pipeline | HIGH | Image quality |
| AW-12 | `ImageResult` type never defined | HIGH | Sprint 3 contract |
| AW-13 | Image dimensions hardcoded 1024×1024; products need different sizes | MEDIUM | Print quality |
| AW-14 | `score` opaque; `mockup_hint` has no format contract | MEDIUM | Debugging, frontend |
| AW-15 | Product catalog in static prompt; will drift from DB | MEDIUM | Maintainability |
| AW-16 | Story stored twice; no canonical source | HIGH | Data integrity |
| AW-17 | Design Agent prompts not persisted before image generation | HIGH | Debuggability, cost |
| AW-18 | Agent handoff uses lossy string join | MEDIUM | Design quality |
| AW-19 | No product registry; new product = multi-file edit | MEDIUM | Extensibility |
| AW-20 | No agent capability registry; orchestrator is hardcoded | LOW | Future extensibility |
| AW-21 | No prompt A/B testing mechanism | LOW | Maintainability |

---

## Required Schema Additions Before Sprint 1

These additions are purely additive (no breaking changes to existing planned schema) and must be in the first migration:

```sql
-- Observability fields
ALTER TABLE agent_logs      ADD COLUMN pipeline_run_id UUID;
ALTER TABLE agent_logs      ADD COLUMN prompt_version  VARCHAR(40);
ALTER TABLE agent_logs      ADD COLUMN is_fallback     BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE designs         ADD COLUMN pipeline_run_id        UUID;
ALTER TABLE designs         ADD COLUMN design_strategy_json   JSONB;  -- full DesignStrategy before image gen
ALTER TABLE designs         ADD COLUMN is_fallback            BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE designs         ADD COLUMN story_version          SMALLINT NOT NULL DEFAULT 1;

ALTER TABLE design_variants ADD COLUMN fal_request_id  VARCHAR(100);
ALTER TABLE design_variants ADD COLUMN generation_seed BIGINT;
ALTER TABLE design_variants ADD COLUMN negative_prompt TEXT;
ALTER TABLE design_variants ADD COLUMN is_fallback     BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE conversation_logs ADD COLUMN agent_text_reply TEXT;
ALTER TABLE conversation_logs ADD COLUMN clarity_score   NUMERIC(4,3);
ALTER TABLE conversation_logs ADD COLUMN confidence      NUMERIC(4,3);

ALTER TABLE sessions        ADD COLUMN prompt_variant   VARCHAR(20) NOT NULL DEFAULT 'v1';
```

---

## Required Planning Document Updates Before Sprint 2

1. **`database_schema.md`**: Apply schema additions above; add `DesignStrategy`, `VariantPrompt`, `ImageResult`, `ConversationTurn`, `MockupHint`, `ScoreBreakdown` to Pydantic schemas section; add `KeralaTheme` enum.
2. **`architecture.md`**: Add "Fallback Catalogue" section; update Design Agent description to return `DesignStrategy` not `str`; update Image Gen interface to carry `GenerationParams` with dimensions and negative prompts; add `ProductConfig` registry concept.
3. **`CLAUDE.md`**: Add "Use tool_use for all structured agent output — never parse Claude text with regex" as a non-negotiable rule; document `pipeline_run_id` convention; resolve variant style list to definitive 4 styles.

---

*End of AI Workflow Review — 21 issues documented*
