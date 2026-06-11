"""Pydantic v2 schemas — canonical types from database_schema.md."""

from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


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
    BACKWATERS = "backwaters"
    THEYYAM = "theyyam"
    KATHAKALI = "kathakali"
    MONSOON = "monsoon"
    FISHING_HERITAGE = "fishing_heritage"
    COCONUT_PALMS = "coconut_palms"
    SPICE_TRADE = "spice_trade"
    TEMPLE_ARCH = "temple_architecture"
    BEACH = "beach"
    BOAT_RACE = "boat_race"
    NONE = "none"


class Story(BaseModel):
    themes: list[KeralaTheme]  # controlled vocabulary; validated by KeralaTheme enum
    emotions: list[str]
    keywords: list[str]
    cultural_refs: list[str]
    design_complexity: Literal["simple", "medium", "complex"]
    intent: str
    raw_customer_text: str  # original unmodified input; passed to Design Agent
    needs_clarification: bool = False
    clarification_questions: list[str] = []
    clarity_score: float = 1.0  # 0.0-1.0; how complete/unambiguous the story is
    confidence: float = 1.0  # 0.0-1.0; agent confidence in extraction


class ConversationTurn(BaseModel):
    turn_number: int
    customer_input: str
    agent_text_reply: str | None  # clarification Q or ack; replayed as assistant turn


class VariantStyle(str, Enum):
    ILLUSTRATION = "illustration"
    GEOMETRIC = "geometric"
    WATERCOLOR = "watercolor"
    MINIMALIST = "minimalist"


class VariantPrompt(BaseModel):
    style: VariantStyle
    prompt: str  # full positive prompt (SDXL/FLUX compatible)
    negative_prompt: str  # full negative prompt; never empty
    color_palette: list[str]  # hex codes or named colors
    mood: str  # descriptive tag for UI display
    width: int  # product-specific pixel width (~300dpi equivalent)
    height: int


class DesignMetadata(BaseModel):
    cultural_authenticity_score: float
    print_feasibility: Literal["excellent", "good", "marginal", "poor"]
    color_count: int
    complexity: Literal["simple", "medium", "complex"]
    estimated_print_time_min: float
    kerala_themes_used: list[KeralaTheme]


class DesignStrategy(BaseModel):
    base_story_summary: str  # 1-sentence design brief for display/logging
    variants: list[VariantPrompt]  # exactly 4
    design_metadata: DesignMetadata
    is_fallback: bool = False


class DesignVariant(BaseModel):
    id: UUID
    variant_number: int  # 1-4 for initial set; 5+ for refinements
    is_initial_set: bool
    style: VariantStyle
    prompt_used: str
    negative_prompt: str | None
    image_url: str | None  # always a local /cache/ path in MVP
    generation_time_ms: int | None
    fal_request_id: str | None  # for fal.ai support queries
    generation_seed: int | None  # enables exact replay
    is_refined: bool = False
    is_fallback: bool = False
    parent_variant_id: UUID | None = None


class ImageResult(BaseModel):
    variant_number: int
    style: VariantStyle
    image_path: str  # absolute local path
    image_url: str  # relative URL served by StaticFiles
    prompt_used: str
    negative_prompt_used: str
    model_used: str
    fal_request_id: str | None
    generation_time_ms: int
    seed: int | None
    success: bool
    error: str | None


class ScoreBreakdown(BaseModel):
    design_fit: float  # weight 40%
    complexity_match: float  # weight 30%
    inferred_demographics: float  # weight 15%
    budget_fit: float  # weight 10%
    inventory_available: bool  # weight 5% (pass/fail)


class MockupHint(BaseModel):
    suggested_color: str  # must match a value in inventory.colors
    suggested_size: str | None  # must match inventory.sizes; None if one-size
    placement: str | None  # e.g. "center_chest"


class ProductRecommendation(BaseModel):
    rank: int
    product_id: str
    product_name: str
    score: float  # 0.0-1.0 weighted composite
    score_breakdown: ScoreBreakdown
    reasons: list[str]
    price_paise: int
    print_area_width_in: float
    print_area_height_in: float
    production_time_minutes: int
    mockup_hint: MockupHint
    units_available: int  # live from inventory; show "low stock" warning if < 5
