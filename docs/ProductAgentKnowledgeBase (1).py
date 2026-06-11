"""
BOBB KITCHEN - Product Sub-Agent Knowledge Base
Complete design thinking research for all 10 product categories.

Each ProductAgent imports its specialized knowledge class.
Usage: from ProductAgentKnowledgeBase import TShirtKnowledgeBase
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


# ============================================================================
# SHARED ENUMS & DATA STRUCTURES
# ============================================================================

class MaterialType(Enum):
    COTTON = "cotton"
    CANVAS = "canvas"
    POLYESTER = "polyester"
    LEATHER = "leather"
    RUBBER = "rubber"
    VINYL = "vinyl"
    TPU = "tpu"
    FOAM = "foam"
    SILK = "silk"
    METAL = "metal"


class PrintMethod(Enum):
    DTF = "dtf"  # Direct-to-Fabric
    DTG = "dtg"  # Direct-to-Garment
    SCREEN = "screen_print"
    VINYL = "vinyl_decal"
    LASER = "laser_engraving"
    UV = "uv_printing"
    EMBOSSING = "embossing"
    EMBROIDERY = "embroidery"


@dataclass
class TechnicalConstraints:
    """Technical specifications for a product"""
    print_area: str  # e.g., "10\"×12\""
    method: PrintMethod
    material: MaterialType
    durability_months: int  # How long design lasts
    max_colors: Optional[int]  # Color limit (None = unlimited)
    dpi_minimum: int
    hard_to_print_areas: List[str]
    flexibility_required: bool


@dataclass
class DesignPrinciple:
    """A design principle for a product"""
    name: str
    description: str
    best_for: str
    example: str


@dataclass
class KeralaTheme:
    """A Kerala cultural theme for design"""
    name: str
    imagery: str
    colors: List[str]
    significance: str
    design_approach: str
    best_for: str
    example: str
    challenges: str
    avoid_if_possible: bool  # True = avoid, False = embrace


@dataclass
class UserMotivation:
    """Understanding why customers buy this product"""
    motivation: str
    percentage: int  # What % of buyers have this motivation
    psychological_need: str
    design_implication: str


@dataclass
class QualityCheckItem:
    """Items to verify before approval"""
    category: str  # e.g., "Composition", "Technical", "Cultural"
    item: str
    critical: bool  # True = must pass


@dataclass
class CommonMistake:
    """A common design mistake to avoid"""
    mistake: str
    problem: str
    solution: str


# ============================================================================
# PRODUCT 1: T-SHIRT
# ============================================================================

class TShirtKnowledgeBase:
    """T-Shirt Design Knowledge Base"""
    
    PRODUCT_NAME = "T-Shirt"
    PRINT_AREA = '10" × 12"'
    
    technical_constraints = TechnicalConstraints(
        print_area='10" × 12" on chest',
        method=PrintMethod.DTF,
        material=MaterialType.COTTON,
        durability_months=60,
        max_colors=6,
        dpi_minimum=300,
        hard_to_print_areas=["Shoulder seams", "Collar area", "Underarm"],
        flexibility_required=True
    )
    
    composition_approaches = [
        "Centered focal point (body-aware)",
        "Left-bias (natural reading flow)",
        "Full-chest coverage (bold statement)",
        "Minimalist single element (elegant)",
        "Repeating pattern (texture-based)"
    ]
    
    design_principles = [
        DesignPrinciple(
            name="Body-Aware Composition",
            description="Design should work on 3D human body, not flat canvas",
            best_for="All t-shirt designs",
            example="Focal point placed above center (heart level) for visibility"
        ),
        DesignPrinciple(
            name="Readable from 3 feet",
            description="Design must be clearly readable from conversation distance",
            best_for="Text-based or detailed designs",
            example="Text minimum 1 inch tall for clarity"
        ),
        DesignPrinciple(
            name="Color Durability",
            description="Design must survive 50+ wash cycles",
            best_for="All designs",
            example="Use BOBB palette (gold #E8C547, black #0A0A0A, bone #FAF7F0)"
        )
    ]
    
    user_motivations = [
        UserMotivation(
            motivation="Self-expression",
            percentage=40,
            psychological_need="Show my personality",
            design_implication="Personal, meaningful, tells wearer's story"
        ),
        UserMotivation(
            motivation="Social connection",
            percentage=25,
            psychological_need="Relate to others with same values",
            design_implication="Community-oriented, shareable, relatable"
        ),
        UserMotivation(
            motivation="Gifting",
            percentage=20,
            psychological_need="Give meaningful present",
            design_implication="Timeless, high-quality, gift-worthy"
        ),
        UserMotivation(
            motivation="Fashion/aesthetics",
            percentage=10,
            psychological_need="Outfit coordination, style",
            design_implication="Visually beautiful, coordinated with wardrobe"
        ),
        UserMotivation(
            motivation="Nostalgia/memory",
            percentage=5,
            psychological_need="Remember special moment",
            design_implication="Meaningful symbol, lasting appeal"
        )
    ]
    
    kerala_themes = [
        KeralaTheme(
            name="Backwater Heritage",
            imagery="Backwater landscape, boats, water",
            colors=["#1E40AF", "#E8C547", "#FAF7F0"],
            significance="Connection to home, serene beauty",
            design_approach="Landscape across chest, centered",
            best_for="Nature-lovers, homesick diaspora",
            example="Minimalist backwater boat on horizon",
            challenges="Simplify landscape for 10x12 format",
            avoid_if_possible=False
        ),
        KeralaTheme(
            name="Theyyam Symbolic",
            imagery="Geometric Theyyam pattern (NOT mask)",
            colors=["#DC2626", "#E8C547", "#0A0A0A"],
            significance="Cultural pride, artistic heritage",
            design_approach="Bold geometric pattern, centered",
            best_for="Heritage-proud, artistic",
            example="Simplified Theyyam face pattern in gold",
            challenges="Use symbolic pattern, NOT actual mask",
            avoid_if_possible=False
        ),
        KeralaTheme(
            name="Monsoon Spirit",
            imagery="Rain, clouds, renewal, water",
            colors=["#475569", "#06B6D4", "#FFFFFF"],
            significance="Seasonal connection, growth",
            design_approach="Dynamic rain pattern or scene",
            best_for="Romantic, poetic personalities",
            example="Rain drops with clearing sky background",
            challenges="Show movement and hope in design",
            avoid_if_possible=False
        ),
        KeralaTheme(
            name="Spice Route",
            imagery="Historical spice patterns, trade routes",
            colors=["#DC2626", "#D97706", "#E8C547"],
            significance="Entrepreneurial spirit, heritage",
            design_approach="Spice plant or pattern-based",
            best_for="Business owners, traders",
            example="Stylized pepper plant or spice leaf",
            challenges="Avoid romanticizing colonialism",
            avoid_if_possible=False
        ),
        KeralaTheme(
            name="Fishing Community",
            imagery="Fishing boats, nets, harbor",
            colors=["#E67E22", "#1E40AF", "#FFFFFF"],
            significance="Working tradition, livelihood",
            design_approach="Fishing boat or net imagery",
            best_for="Traditional values, labor-respecting",
            example="Stylized fishing net geometric pattern",
            challenges="Honor labor authentically",
            avoid_if_possible=False
        ),
        KeralaTheme(
            name="Kathakali Artistry",
            imagery="Ornamental patterns, aesthetic elements",
            colors=["#DC2626", "#E8C547", "#1E1E1E"],
            significance="Artistic mastery, refinement",
            design_approach="Ornamental framing or patterns",
            best_for="Artists, performers, refined taste",
            example="Ornamental border with central focal point",
            challenges="Elegant without being clichéd",
            avoid_if_possible=False
        ),
        KeralaTheme(
            name="Coconut Economy",
            imagery="Coconut trees, sustainable growth",
            colors=["#16A34A", "#92400E", "#E8C547"],
            significance="Resourcefulness, growth, sustainability",
            design_approach="Tree silhouette or economic symbolism",
            best_for="Sustainability-focused, growth-minded",
            example="Stylized coconut palm with business symbol",
            challenges="Make sustainability look premium",
            avoid_if_possible=False
        ),
        KeralaTheme(
            name="Literary Kerala",
            imagery="Scripts, writing, knowledge",
            colors=["#1E40AF", "#E8C547", "#FFFFFF"],
            significance="Intellectual heritage, literature",
            design_approach="Malayalam script or literary element",
            best_for="Educated, literary-minded",
            example="Elegant Malayalam character with English text",
            challenges="Script must be beautiful and readable",
            avoid_if_possible=False
        )
    ]
    
    common_mistakes = [
        CommonMistake(
            mistake="Design too centered vertically (too low)",
            problem="On body, appears lower and less visible",
            solution="Place focal point slightly above center (heart level)"
        ),
        CommonMistake(
            mistake="Text too small to read",
            problem="Illegible from 3 feet away",
            solution="Minimum 1 inch tall for readability"
        ),
        CommonMistake(
            mistake="Too many colors (8+)",
            problem="Looks chaotic, difficult to print",
            solution="Maximum 4-5 colors for clean appearance"
        ),
        CommonMistake(
            mistake="Design doesn't account for body shape",
            problem="Looks distorted on curved torso",
            solution="Test on actual t-shirt form or mockup"
        ),
        CommonMistake(
            mistake="Poor color choices (pastels, light colors)",
            problem="Fades quickly, looks cheap after wash",
            solution="Use bold, saturated colors from BOBB palette"
        )
    ]
    
    quality_checklist = [
        QualityCheckItem(category="Composition", item="Focal point is above center", critical=True),
        QualityCheckItem(category="Composition", item="Design is readable from 3 feet", critical=True),
        QualityCheckItem(category="Technical", item="Colors match approved proof", critical=True),
        QualityCheckItem(category="Technical", item="Text is minimum 1 inch tall", critical=False),
        QualityCheckItem(category="Durability", item="Design will survive 50+ wash cycles", critical=True),
        QualityCheckItem(category="Cultural", item="No sacred/deity imagery", critical=True),
        QualityCheckItem(category="Cultural", item="Theyyam representation is symbolic only", critical=True),
    ]
    
    system_prompt_section = """
You are BOBB's T-Shirt Design Specialist Agent.

YOUR MISSION:
Transform customer stories into wearable art that tells their story with pride and craftsmanship.

CRITICAL CONSTRAINTS (NON-NEGOTIABLE):
✓ Print Area: 10"×12" on chest (6 colors maximum)
✓ Method: DTF printing
✓ Focal Point: Slightly above center (heart level for visibility)
✓ Readability: Clear from 3 feet away
✓ Durability: 50+ wash cycles
✓ Colors: 4-5 maximum (BOBB palette preferred)

DESIGN PRINCIPLES:
1. Body-Aware: Design for 3D human form, not flat canvas
2. Centered Story: Focal point tells main narrative
3. Durable Colors: Saturated, quality inks that last
4. Kerala Pride: 8 cultural themes available
5. Timeless: Won't look dated in 5 years

KERALA CULTURAL THEMES (8 Available):
- Backwater Heritage | Theyyam Symbolic | Monsoon Spirit
- Spice Route | Fishing Community | Kathakali Artistry
- Coconut Economy | Literary Kerala

AVOID:
✗ Sacred masks or deity faces
✗ Stereotypical "exotic India" imagery
✗ Overly trendy designs
✗ Text smaller than 1 inch
✗ More than 5 colors

OUTPUT:
Include design prompt, composition type, focal point, color palette, 
cultural theme (if any), and quality validation.
"""
    
    @staticmethod
    def get_theme(theme_name: str) -> Optional[KeralaTheme]:
        """Get a specific Kerala theme by name"""
        for theme in TShirtKnowledgeBase.kerala_themes:
            if theme.name.lower() == theme_name.lower():
                return theme
        return None
    
    @staticmethod
    def list_themes() -> List[str]:
        """List all available Kerala themes"""
        return [theme.name for theme in TShirtKnowledgeBase.kerala_themes]
    
    @staticmethod
    def validate_composition(composition_type: str) -> bool:
        """Validate that composition is one of allowed types"""
        return composition_type in TShirtKnowledgeBase.composition_approaches


# ============================================================================
# PRODUCT 2: KEYCHAIN
# ============================================================================

class KeychainKnowledgeBase:
    """Keychain Design Knowledge Base"""
    
    PRODUCT_NAME = "Keychain"
    PRINT_AREA = '2" × 2"'
    
    technical_constraints = TechnicalConstraints(
        print_area='2" × 2" (small pendant)',
        method=PrintMethod.LASER,
        material=MaterialType.METAL,
        durability_months=36,
        max_colors=2,
        dpi_minimum=300,
        hard_to_print_areas=["Edges", "Curve areas"],
        flexibility_required=False
    )
    
    design_principles = [
        DesignPrinciple(
            name="Icon-Level Simplicity",
            description="If you can't see it at 2 inches, don't include it",
            best_for="All keychain designs",
            example="Simple geometric symbol, bold lines only"
        ),
        DesignPrinciple(
            name="Memorable Symbol",
            description="Must be instantly recognizable",
            best_for="All designs",
            example="Theyyam pattern, boat silhouette, initials"
        ),
        DesignPrinciple(
            name="High Contrast",
            description="Dark on light or light on dark",
            best_for="Visibility and identification",
            example="Gold symbol on black background or vice versa"
        )
    ]
    
    valid_styles = [
        "Geometric (angular, structured)",
        "Bold line art (clean, defined)",
        "Silhouette (solid shape)",
        "Symbolic (meaningful mark)",
        "Text-based (initials, name)",
        "Hybrid (symbol + text)"
    ]
    
    common_mistakes = [
        CommonMistake(
            mistake="Too much detail",
            problem="Detail disappears at 2x2 scale",
            solution="Radical simplification, essential elements only"
        ),
        CommonMistake(
            mistake="Text too small",
            problem="Unreadable on small pendant",
            solution="Minimum 12pt font (larger is better)"
        ),
        CommonMistake(
            mistake="Thin lines",
            problem="Engraving doesn't show fine details",
            solution="Minimum 1mm line width for laser engraving"
        )
    ]
    
    system_prompt_section = """
You are BOBB's Keychain Design Specialist Agent.

YOUR MISSION:
Create memorable icons that fit in 2"×2" and tell wearer's story instantly.

CRITICAL CONSTRAINTS:
✓ Print Area: 2"×2" (maximum)
✓ Method: Laser engraving or UV printing
✓ Colors: 1-2 maximum (simplicity critical)
✓ Complexity: Icon-level only (no detail)

THE KEYCHAIN RULE:
If you can't see it at 2 inches, don't include it.
Simple > Complex (always)
Memorable > Beautiful (priority)

DESIGN PRINCIPLES:
1. Icon-Level Simplicity
2. Instantly Recognizable
3. High Contrast
4. Meaningful Symbol
5. 1-2 Colors Maximum

VALID STYLES:
- Geometric | Bold line art | Silhouette
- Symbolic | Text-based | Hybrid (symbol + text)

OUTPUT:
Include design prompt, icon description, line weight (1mm minimum),
color palette, contrast strategy.
"""


# ============================================================================
# PRODUCT 3: WATER BOTTLE
# ============================================================================

class WaterBottleKnowledgeBase:
    """Water Bottle Design Knowledge Base"""
    
    PRODUCT_NAME = "Water Bottle"
    PRINT_AREA = '4" × 6" (cylindrical wrap)'
    
    technical_constraints = TechnicalConstraints(
        print_area='4" × 6" on curved cylinder',
        method=PrintMethod.UV,
        material=MaterialType.POLYESTER,
        durability_months=36,
        max_colors=None,  # Unlimited
        dpi_minimum=300,
        hard_to_print_areas=["Top rim", "Bottom edges"],
        flexibility_required=False
    )
    
    design_principles = [
        DesignPrinciple(
            name="Cylindrical Wrapping",
            description="Left edge must align seamlessly with right edge",
            best_for="All water bottle designs",
            example="Design that creates continuous pattern when wrapped"
        ),
        DesignPrinciple(
            name="Horizontal Level",
            description="Horizontal lines must be perfectly level despite curve",
            best_for="Landscape or banded designs",
            example="Water line must appear level when bottle is tilted"
        ),
        DesignPrinciple(
            name="15-20% Curve Distortion",
            description="Design will distort as it wraps cylinder",
            best_for="Accounting for visual distortion",
            example="Allow artistic distortion as part of design"
        )
    ]
    
    composition_approaches = [
        "Horizontal bands (simplest, repeating)",
        "Vertical centerpiece (focal point in middle)",
        "Repeating 360° pattern (geometric, all-around)",
        "Landscape wrap (panoramic, continuous)",
        "Front-focused (main image with minimal back)"
    ]
    
    common_mistakes = [
        CommonMistake(
            mistake="Design doesn't account for cylindrical wrap",
            problem="Left and right edges don't connect properly",
            solution="Design left edge to seamlessly connect with right"
        ),
        CommonMistake(
            mistake="Horizontal lines not level",
            problem="Water/horizon line appears crooked when wrapped",
            solution="Verify horizontals are pixel-perfect level"
        ),
        CommonMistake(
            mistake="Ignoring the curve in composition",
            problem="Design looks distorted and awkward on bottle",
            solution="Embrace or compensate for 15-20% curve distortion"
        )
    ]
    
    system_prompt_section = """
You are BOBB's Water Bottle Design Specialist Agent.

YOUR MISSION:
Create designs for cylindrical surface that feel seamless when wrapped.

CRITICAL CONSTRAINTS:
✓ Print Area: 4"×6" on curved surface
✓ Method: UV printing on plastic/steel
✓ Wrapping: Left edge must connect seamlessly to right
✓ Distortion: Account for 15-20% visual stretch on curve

THE WATER BOTTLE PRINCIPLE:
Design for the cylinder, not the flat mockup.
Seamless wrapping is essential.
Horizontal lines must be perfectly level.
Left edge = Right edge (continuity critical)

COMPOSITION APPROACHES:
1. Horizontal bands | 2. Vertical centerpiece
3. Repeating pattern | 4. Landscape wrap
5. Front-focused

DESIGN PRINCIPLES:
1. Dance with the curve, don't fight it
2. Seamless left/right edge connection
3. Level horizontal lines
4. Account for 15-20% distortion
5. 360° visual coherence

OUTPUT:
Include design prompt, composition type, wrapping strategy,
distortion plan, color palette.
"""


# ============================================================================
# PRODUCT 4: LAPTOP SKIN
# ============================================================================

class LaptopSkinKnowledgeBase:
    """Laptop Skin Design Knowledge Base"""
    
    PRODUCT_NAME = "Laptop Skin"
    PRINT_AREA = '13" × 9" (flat vinyl)'
    
    technical_constraints = TechnicalConstraints(
        print_area='13" × 9" for standard laptop',
        method=PrintMethod.VINYL,
        material=MaterialType.VINYL,
        durability_months=60,
        max_colors=None,  # Unlimited
        dpi_minimum=300,
        hard_to_print_areas=["Edges (0.25 inch wrap)", "Logo area"],
        flexibility_required=False
    )
    
    professional_languages = [
        "Minimalist Professional (clean, restrained)",
        "Bold Statement (impactful, draws attention)",
        "Sophisticated/Luxury (refined, premium feel)",
        "Artistic/Creative (expressive, illustrative)",
        "Corporate (structured, branded)"
    ]
    
    common_mistakes = [
        CommonMistake(
            mistake="Too much detail (cluttered design)",
            problem="Becomes visually overwhelming",
            solution="Embrace white space, focus on focal point"
        ),
        CommonMistake(
            mistake="Overly trendy design",
            problem="Dated in 6 months, won't age well",
            solution="Timeless design that works in 5 years"
        ),
        CommonMistake(
            mistake="Text too small",
            problem="Unreadable from distance",
            solution="Minimum 14pt for readable text"
        )
    ]
    
    system_prompt_section = """
You are BOBB's Laptop Skin Design Specialist Agent.

YOUR MISSION:
Create premium laptop designs reflecting professional identity + cultural heritage.

CRITICAL CONSTRAINTS:
✓ Print Area: 13"×9" flat vinyl with lamination
✓ Method: Vinyl printing with protective laminate
✓ Material: Premium matte vinyl
✓ Edge: Design stops 0.25" from edge (no wrap)
✓ Durability: 3-5 years normal laptop use

THE LAPTOP SKIN PRINCIPLE:
Laptop skins are personal billboards (portable art).
Seen constantly in professional settings.
Design must show BOTH professional identity AND Kerala heritage.
Must feel premium, sophisticated, intentional.

COMPOSITION APPROACHES:
1. Centered hero image | 2. Full-bleed landscape
3. Corner/edge focused | 4. Pattern/texture
5. Split/diptych narrative

DESIGN PRINCIPLES:
1. Premium & Refined
2. Works at close + far distance
3. Balanced composition
4. Professional context appropriate
5. Timeless aesthetic

OUTPUT:
Include design prompt, composition type, professional language,
focal point, color palette, Kerala theme integration.
"""


# ============================================================================
# PRODUCT 5: MOBILE PHONE CASE
# ============================================================================

class MobilePhoneCaseKnowledgeBase:
    """Mobile Phone Case Design Knowledge Base"""
    
    PRODUCT_NAME = "Mobile Phone Case"
    PRINT_AREA = '5" × 8" front (3D wrapping)'
    
    technical_constraints = TechnicalConstraints(
        print_area='5" × 8" front + curved sides + back (3D)',
        method=PrintMethod.UV,
        material=MaterialType.TPU,
        durability_months=36,
        max_colors=None,  # Unlimited
        dpi_minimum=200,
        hard_to_print_areas=["Camera cutout", "Button areas"],
        flexibility_required=True
    )
    
    composition_approaches = [
        "Wraparound scene (front + sides + back continuous)",
        "Front-focused with colored back",
        "Edge accent design (sides emphasized)",
        "Pattern across full 3D surface",
        "Geometric/abstract utilizing curves",
        "Back-as-statement (front clean, back bold)"
    ]
    
    functional_requirements = {
        "camera_cutout_buffer": "0.25 inch minimum",
        "top_button_area": "0.5 inch clear",
        "bottom_area": "0.5 inch clear (charging/speaker)",
        "side_buttons": "accessible"
    }
    
    common_mistakes = [
        CommonMistake(
            mistake="Design interferes with camera/buttons",
            problem="Blocks function, looks unintentional",
            solution="Leave functional areas completely clear"
        ),
        CommonMistake(
            mistake="Ignores 3D curvature",
            problem="Design distorts awkwardly on curved surface",
            solution="Design WITH curves, not against them"
        ),
        CommonMistake(
            mistake="No consideration for side/back views",
            problem="When placed down, design looks incomplete",
            solution="Design works from all angles (360°)"
        )
    ]
    
    system_prompt_section = """
You are BOBB's Mobile Phone Case Design Specialist Agent.

YOUR MISSION:
Create beautiful 3D phone case designs for intimate, daily-touched product.

CRITICAL CONSTRAINTS:
✓ Print Area: 5"×8" front + curved sides + back (3D)
✓ Method: Direct UV printing on TPU
✓ Material: Premium matte TPU (flexible, grippy)
✓ 3D Challenge: Must work held (front), placed (back), all angles
✓ Functional: Camera/buttons MUST be clear (0.25-0.5" buffers)
✓ Durability: 2-3 years with daily heavy use

THE PHONE CASE PRINCIPLE:
Phone is touched 100+ times daily.
Design must work in 3D (not think flat).
Must be beautiful AND protective.
Must make customer smile when they pick it up.

3D COMPOSITIONS:
1. Wraparound scene | 2. Front-focused + colored back
3. Edge accent | 4. Full-surface pattern
5. Geometric/abstract | 6. Back-as-statement

DESIGN PRINCIPLES:
1. Works when held (front primary)
2. Works when placed (back visible)
3. Utilizes curves as asset
4. Functional areas protected
5. Tactile intimacy

FUNCTIONAL REQUIREMENTS:
- Camera cutout: 0.25" clear buffer
- Top: 0.5" clear (button/sensor)
- Bottom: 0.5" clear (charging/speaker)
- Sides: Design okay here

OUTPUT:
Include design prompt, 3D strategy, focal point, front/side/back designs,
functional clearances, color palette, tactile quality assessment.
"""


# ============================================================================
# PRODUCT 6: HELMET STICKER
# ============================================================================

class HelmetStickerKnowledgeBase:
    """Helmet Sticker Design Knowledge Base"""
    
    PRODUCT_NAME = "Helmet Sticker"
    PRINT_AREA = '5" × 7" rear (vinyl decal)'
    
    technical_constraints = TechnicalConstraints(
        print_area='5" × 7" on helmet back (only safe placement)',
        method=PrintMethod.VINYL,
        material=MaterialType.VINYL,
        durability_months=60,
        max_colors=None,  # Unlimited
        dpi_minimum=300,
        hard_to_print_areas=["Curved helmet surface"],
        flexibility_required=False
    )
    
    safety_rules = {
        "placement_mandatory": "Rear helmet ONLY",
        "vision_protection": "No front/visor placement (SAFETY HAZARD)",
        "visibility_requirement": "Readable from 20-50 feet away",
        "colors": "Bright, high-visibility (orange, yellow, white)",
        "priority": "Visibility > Aesthetics (ALWAYS)"
    }
    
    common_mistakes = [
        CommonMistake(
            mistake="Design on front/visor",
            problem="SAFETY HAZARD - blocks vision or falls during ride",
            solution="Rear placement ONLY (back of helmet)"
        ),
        CommonMistake(
            mistake="Poor visibility colors (dark blue, green)",
            problem="Invisible at distance, defeats safety purpose",
            solution="Use bright colors (orange, yellow, white)"
        ),
        CommonMistake(
            mistake="No consideration for safety",
            problem="Creates hazard instead of protection",
            solution="Safety ALWAYS comes first, before aesthetics"
        )
    ]
    
    system_prompt_section = """
You are BOBB's Safety-First Helmet Sticker Design Specialist Agent.

YOUR MISSION:
Create highly visible helmet stickers that make riders safe AND express identity.

CRITICAL SAFETY-FIRST CONSTRAINTS:
✓ PLACEMENT: Rear helmet ONLY (5"×7")
✓ NO FRONT/VISOR: Vision obstruction is SAFETY HAZARD
✓ VISIBILITY: Readable from 20-50 feet (traffic safety critical)
✓ COLORS: Bright, high-contrast (orange, yellow, white)
✓ PRIORITY: Visibility > Aesthetics (ALWAYS)

THE HELMET STICKER RULE:
If a sticker makes the rider LESS visible, it's not acceptable.
If a sticker blocks vision, it's not acceptable.
Safety is paramount. No exceptions.

SAFETY-FIRST PRINCIPLE:
Visibility > Aesthetics (Always)
Safety > Identity (Always)

VALID PLACEMENTS:
✓ Rear helmet (back): Primary, safest
✓ Helmet sides: Secondary, okay
✗ Front helmet: FORBIDDEN
✗ Visor: FORBIDDEN
✗ Chin bar: FORBIDDEN

VISIBILITY COLORS:
1. Fluorescent Yellow (best)
2. Fluorescent Orange (excellent)
3. White (universal)
4. Bright Red (attention-grabbing)
5. Combinations (yellow+black optimal)

INVALID COLORS:
✗ Dark blue | ✗ Dark green | ✗ Light pastels

DESIGN PRINCIPLES:
1. BOLD & SIMPLE
2. HIGH CONTRAST
3. READABLE AT DISTANCE
4. SAFETY-COMPLIANT
5. DURABLE COLOR

OUTPUT:
Include design prompt, placement verification, visibility analysis,
color strategy, safety compliance check (MUST PASS).
"""


# ============================================================================
# PRODUCT 7: FLIPFLOPS
# ============================================================================

class FlipflopKnowledgeBase:
    """Flipflop Design Knowledge Base"""
    
    PRODUCT_NAME = "Flipflops"
    PRINT_AREA = '2" × 4" (flexible sole)'
    
    technical_constraints = TechnicalConstraints(
        print_area='2" × 4" on curved, textured sole',
        method=PrintMethod.DTF,
        material=MaterialType.FOAM,
        durability_months=24,
        max_colors=3,
        dpi_minimum=200,
        hard_to_print_areas=["Heel area", "Textured ridges"],
        flexibility_required=True
    )
    
    micro_impact_principle = """
Small space = Maximum impact required.
Simple > Complex (always).
Bold > Subtle (always).
Meaningful > Beautiful (hierarchy).
Durability > Perfection (wear is natural).
"""
    
    wear_timeline = {
        "initial": "Visible and vibrant immediately",
        "6_months": "Still clear, some edge wear",
        "12_months": "Noticeable fade at heel/toe",
        "18_months": "Design still visible but aged",
        "24_months": "Significant patina, expected wear"
    }
    
    common_mistakes = [
        CommonMistake(
            mistake="Design too small",
            problem="At 2\"×4\", small becomes invisible",
            solution="Bold, fills 70-80% of space"
        ),
        CommonMistake(
            mistake="Too much detail",
            problem="Disappears at scale + with foot friction",
            solution="Radical simplification, geometric approach"
        ),
        CommonMistake(
            mistake="Poor color contrast",
            problem="Invisible on dark sole",
            solution="Light on dark (white/gold on dark sole)"
        )
    ]
    
    system_prompt_section = """
You are BOBB's Micro-Impact Flipflop Design Specialist Agent.

YOUR MISSION:
Create meaningful flipflop sole designs that tell wearer's story with every step.

CRITICAL CONSTRAINTS:
✓ Print Area: 2"×4" maximum (tiny, demands simplicity)
✓ Method: DTF printing on flexible EVA/rubber sole
✓ Material: Flexible foam or rubber
✓ Colors: 3-4 maximum (simple palette)
✓ Durability: 18-24 months with daily wear
✓ Flexibility: Must flex with sole (no cracking)

THE FLIPFLOP PRINCIPLE:
Small space = Maximum impact required.
Simple > Complex (always).
Bold > Subtle (always).
Meaningful > Beautiful.
Durability > Perfection (wear is natural).

COMPOSITION APPROACHES:
1. Centered Icon (single symbol, 70-80% space)
2. Repeating Pattern (geometric, works with small area)
3. Name/Personalization (bold typography)
4. Directional Design (left/right pair identity)
5. Corner Accent (subtle but visible)

DESIGN PRINCIPLES:
1. RADICAL SIMPLIFICATION
2. BOLD, FILLS SPACE
3. HIGH CONTRAST
4. ICON-LEVEL CLARITY
5. AGES GRACEFULLY

DURABILITY TIMELINE:
- Heel/toe: Fade first (high friction)
- Center: Lasts longer
- 18-24 months: Design remains visible
- Patina is natural and acceptable

OUTPUT:
Include design prompt, composition, core symbol, size coverage,
color palette, contrast strategy, wear plan, personal meaning.
"""


# ============================================================================
# PRODUCT 8: ACCESSORIES (Belts, Scarves, Necklaces, etc.)
# ============================================================================

class AccessoriesKnowledgeBase:
    """Accessories Design Knowledge Base (Multi-Type)"""
    
    PRODUCT_NAME = "Accessories"
    SUB_CATEGORIES = ["Belts", "Scarves", "Necklaces", "Bangles", "Hair Clips"]
    
    sub_category_specs = {
        "Belts": {
            "print_area": "4\" × 32\" (wraps body)",
            "method": PrintMethod.DTF,
            "material": MaterialType.CANVAS,
            "durability_months": 36
        },
        "Scarves": {
            "print_area": "Full 36\"×36\" or variable",
            "method": PrintMethod.SCREEN,
            "material": MaterialType.COTTON,
            "durability_months": 60
        },
        "Necklaces": {
            "print_area": "1\"×2\" pendant area",
            "method": PrintMethod.UV,
            "material": MaterialType.METAL,
            "durability_months": 36
        },
        "Bangles": {
            "print_area": "0.5\" band × 7\" circumference",
            "method": PrintMethod.LASER,
            "material": MaterialType.METAL,
            "durability_months": 24
        },
        "Hair Clips": {
            "print_area": "1\"×3\" per clip",
            "method": PrintMethod.DTF,
            "material": MaterialType.FABRIC,
            "durability_months": 18
        }
    }
    
    user_motivations = [
        UserMotivation(
            motivation="Personal style expression",
            percentage=40,
            psychological_need="Show fashion sense",
            design_implication="Fashionable, coordinated, trendy-but-timeless"
        ),
        UserMotivation(
            motivation="Brand love/personal brand",
            percentage=30,
            psychological_need="Express values or interests",
            design_implication="Meaningful, symbolic, authentic"
        ),
        UserMotivation(
            motivation="Group belonging",
            percentage=20,
            psychological_need="Connect with community",
            design_implication="Community-oriented, shareable"
        ),
        UserMotivation(
            motivation="Gifting",
            percentage=7,
            psychological_need="Give meaningful present",
            design_implication="Premium, giftworthy, timeless"
        ),
        UserMotivation(
            motivation="Practical identification",
            percentage=3,
            psychological_need="Identify personal items",
            design_implication="Distinct, recognizable, useful"
        )
    ]
    
    system_prompt_section = """
You are BOBB's Accessories Design Specialist Agent.

YOUR MISSION:
Create beautiful accessory designs across multiple types (belts, scarves, 
necklaces, bangles, hair clips) with material-specific expertise.

CRITICAL CONSTRAINTS (Vary by Type):
✓ Belts: 4"×32" on canvas/leather, body-wrap challenge
✓ Scarves: 36"×36" full surface, fabric drape considerations
✓ Necklaces: 1"×2" pendant, icon-level simplicity
✓ Bangles: 0.5"×7" cylindrical, friction resistance
✓ Hair Clips: 1"×3", fabric-safe attachment

DESIGN APPROACH (Material-Specific):
1. Understand accessory type (each has unique constraints)
2. Choose appropriate print method for material
3. Account for material-specific properties
4. Design for wearability + durability
5. Ensure personal style expression

SUB-CATEGORY SPECS:
- Belts: Body-wrap design, leather/canvas compatibility
- Scarves: Fabric drape, full-surface utilization
- Necklaces: Small pendant focus, visibility
- Bangles: Cylindrical wrapping, friction resistance
- Hair Clips: Minimal space, practical placement

DESIGN PRINCIPLES:
1. Material Compatibility
2. Wearability First
3. Style Expression
4. Durability Expectations
5. Cultural Authenticity

OUTPUT:
Include accessory type, design prompt, material specifications,
composition approach, color palette, durability timeline, 
cultural theme integration.
"""


# ============================================================================
# PRODUCT 9: SHOES (Complex 3D, Highest Difficulty)
# ============================================================================

class ShoesKnowledgeBase:
    """Shoes Design Knowledge Base"""
    
    PRODUCT_NAME = "Shoes"
    SURFACES = ["Side (primary)", "Tongue (secondary)", "Heel (accent)"]
    
    technical_constraints = TechnicalConstraints(
        print_area="Variable (3\"×8\" side, 4\"×6\" tongue, 3\"×3\" heel)",
        method=PrintMethod.DTF,
        material=MaterialType.CANVAS,  # Typically
        durability_months=24,
        max_colors=None,  # Unlimited
        dpi_minimum=300,
        hard_to_print_areas=["Seams", "Flex points", "Arch area"],
        flexibility_required=True
    )
    
    multi_surface_principle = """
Side surface is most visible (primary focal point).
Tongue can feature secondary message (visible when tying).
Heel accent adds balance and complexity.
All surfaces must coordinate as unified design.
Design must work in motion (constant viewing angle changes).
"""
    
    composition_approaches = [
        "Side-focused with tongue accent (RECOMMENDED)",
        "Fully coordinated unified design",
        "Asymmetrical (left/right difference)",
        "Minimalist accent",
        "Tonal/monochromatic"
    ]
    
    common_mistakes = [
        CommonMistake(
            mistake="Ignoring 3D form",
            problem="Design distorts severely on curved shoe",
            solution="Design WITH 3D curves, account for distortion"
        ),
        CommonMistake(
            mistake="Seams not considered",
            problem="Won't print on raised stitching",
            solution="Map seams, design around them gracefully"
        ),
        CommonMistake(
            mistake="Overdesigning all surfaces",
            problem="Overwhelming, looks chaotic, unprofessional",
            solution="Focus on side (primary), accent other surfaces"
        )
    ]
    
    system_prompt_section = """
You are BOBB's Premium Multi-Surface Shoe Design Specialist Agent.

YOUR MISSION:
Create sophisticated, coordinated shoe designs across multiple curved 
surfaces while surviving daily wear.

CRITICAL CONSTRAINTS:
✓ Multiple Surfaces: Side (3\"×8\"), Tongue (4\"×6\"), Heel (3\"×3\")
✓ 3D Form: Curved, flexible, constantly moving
✓ Materials: Canvas + leather + rubber (mixed)
✓ Durability: 18-24 months with daily heavy wear
✓ Flexibility: Ink must flex (won't crack with shoe bending)
✓ Seams: Design avoids stitching stress points

THE SHOE DESIGN PRINCIPLE:
Shoes are personal, visible, daily companions.
Design must be bold AND professional.
Must work in motion, not static viewing.
Multiple surfaces must coordinate seamlessly.
Design must age gracefully with shoe wear.

DESIGN APPROACH:
1. Understand professional + personal identity
2. Map all printable surfaces
3. Create focal point on primary surface (side)
4. Design secondary elements for supporting surfaces
5. Ensure color coordination
6. Account for flex points
7. Verify design works in motion

COMPOSITION APPROACHES:
1. Side-Focused Primary (70% side, accent tongue/heel)
2. Fully Coordinated Unified (all surfaces integrated)
3. Asymmetrical/Narrative (left/right shoe asymmetry)
4. Minimalist Accent (clean shoe, small logo)
5. Tonal/Monochromatic (pattern through texture)

PRIMARY SURFACE (SIDE):
- What people see when shoes are worn
- Most visible during walking
- Fills 70% of 3\"×8\" space
- Clear focal point
- Coordinates with professional context

SECONDARY (TONGUE):
- Visible when tying, sitting, close-up
- 30-40% of 4\"×6\" space
- Complements main design
- Same color palette

ACCENT (HEEL):
- Visible from behind, adds balance
- 20-30% of 3\"×3\" space
- Small detail, color block, or initials
- Completes overall design

DESIGN PRINCIPLES:
1. Works in motion
2. Multiple surfaces coordinate
3. Avoids seams and stress points
4. Professional + identity balanced
5. Ages beautifully

OUTPUT:
Include design prompt, 3D strategy, surface breakdown,
functional areas clear, color palette, cultural theme,
flex/durability compliance.
"""


# ============================================================================
# PRODUCT 10: BAG STICKERS (Vinyl on Fabric)
# ============================================================================

class BagStickerKnowledgeBase:
    """Bag Sticker Design Knowledge Base"""
    
    PRODUCT_NAME = "Bag Stickers"
    PRINT_AREA = '2"-4" × 3"-6" (variable)'
    
    technical_constraints = TechnicalConstraints(
        print_area="2\"×3\" (small) to 4\"×6\" (large)",
        method=PrintMethod.VINYL,
        material=MaterialType.CANVAS,
        durability_months=36,
        max_colors=None,  # Unlimited
        dpi_minimum=300,
        hard_to_print_areas=["Fabric seams", "Bag edges"],
        flexibility_required=False
    )
    
    placement_strategy = {
        "front": "Most visible, primary placement",
        "side": "Secondary visibility, interesting angle",
        "back": "Less visible, can be bold statement",
        "avoid": ["Seams", "Zipper areas", "High-friction edges"]
    }
    
    fabric_types = {
        "canvas": "Excellent vinyl adhesion, durable",
        "nylon": "Good adhesion, smooth surface",
        "leather": "Requires special prep, premium appearance",
        "cotton": "Good adhesion, absorbent fabric",
        "mixed": "Adhesion varies by material"
    }
    
    common_mistakes = [
        CommonMistake(
            mistake="Design directly on seams",
            problem="Won't adhere properly to stitching",
            solution="Design avoids seams entirely"
        ),
        CommonMistake(
            mistake="Placement on high-friction area",
            problem="Edge peeling from bag movement",
            solution="Center placement on flat areas"
        ),
        CommonMistake(
            mistake="Weak adhesive vinyl",
            problem="Fails after few weeks/washes",
            solution="High-tack vinyl for fabric (removable if needed)"
        )
    ]
    
    system_prompt_section = """
You are BOBB's Bag Sticker Design Specialist Agent.

YOUR MISSION:
Create beautiful vinyl stickers that personalize bags while remaining 
durable and attractive.

CRITICAL CONSTRAINTS:
✓ Print Area: 2"×3" (small) to 4"×6" (large)
✓ Method: Vinyl decal cutting and printing
✓ Material: Canvas, nylon, or cotton backing
✓ Adhesion: High-tack vinyl for fabric (removable)
✓ Durability: 2-3 years with bag use
✓ Placement: Front center (avoid seams/edges)

THE BAG STICKER PRINCIPLE:
Bag stickers extend personal brand/identity.
Visible in social contexts, conversation starters.
Design must be meaningful yet not overwhelming.
Placement strategy is critical (seams = failure).

PLACEMENT STRATEGY:
✓ Front center: Primary, optimal visibility
✓ Side area: Secondary, interesting angle
✓ Back: Less visible, can be bolder
✗ Seams: AVOID (adhesion fails)
✗ Zipper area: AVOID (movement stresses edge)
✗ Edges: AVOID (peeling risk)

DESIGN PRINCIPLES:
1. Logo-like clarity OR Artistic statement
2. High contrast for visibility
3. Seam avoidance critical
4. Center placement on flat fabric
5. Removable without damage

FABRIC TYPES:
- Canvas: Excellent adhesion (best)
- Nylon: Good adhesion
- Cotton: Good adhesion
- Leather: Requires prep, premium feel
- Mixed: Variable, assess before applying

COMPOSITION APPROACHES:
1. Bold logo/symbol
2. Artistic scene/illustration
3. Text-based (name, quote)
4. Cultural symbol
5. Hybrid (symbol + text)

COLOR & CONTRAST:
✓ High contrast (light on dark or vice versa)
✓ Bold, saturated colors
✓ 3-4 colors maximum (cohesive)
✗ Pastels (invisible on dark bags)
✗ Low contrast (disappears)

OUTPUT:
Include design prompt, placement strategy, composition type,
color palette, fabric consideration, adhesion plan,
removability assessment.
"""


# ============================================================================
# MASTER REGISTRY
# ============================================================================

class ProductKnowledgeRegistry:
    """Registry of all product knowledge bases"""
    
    PRODUCTS = {
        "tshirt": TShirtKnowledgeBase,
        "keychain": KeychainKnowledgeBase,
        "water_bottle": WaterBottleKnowledgeBase,
        "laptop_skin": LaptopSkinKnowledgeBase,
        "phone_case": MobilePhoneCaseKnowledgeBase,
        "helmet_sticker": HelmetStickerKnowledgeBase,
        "flipflops": FlipflopKnowledgeBase,
        "accessories": AccessoriesKnowledgeBase,
        "shoes": ShoesKnowledgeBase,
        "bag_stickers": BagStickerKnowledgeBase
    }
    
    @staticmethod
    def get_knowledge_base(product_name: str):
        """Get knowledge base for specific product"""
        product_key = product_name.lower().replace(" ", "_")
        return ProductKnowledgeRegistry.PRODUCTS.get(product_key)
    
    @staticmethod
    def list_products() -> List[str]:
        """List all available products"""
        return list(ProductKnowledgeRegistry.PRODUCTS.keys())
    
    @staticmethod
    def get_all_knowledge_bases() -> Dict[str, type]:
        """Get all knowledge base classes"""
        return ProductKnowledgeRegistry.PRODUCTS


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Example 1: Get T-Shirt knowledge base
    kb = TShirtKnowledgeBase()
    print(f"Product: {kb.PRODUCT_NAME}")
    print(f"Print Area: {kb.PRINT_AREA}")
    print(f"Technical Constraints: {kb.technical_constraints}")
    
    # Example 2: List Kerala themes for t-shirts
    print(f"\nAvailable Kerala themes: {kb.list_themes()}")
    
    # Example 3: Get specific theme
    theme = kb.get_theme("Backwater Heritage")
    if theme:
        print(f"\nTheme: {theme.name}")
        print(f"Colors: {theme.colors}")
    
    # Example 4: Use product registry
    registry = ProductKnowledgeRegistry()
    print(f"\nAll products: {registry.list_products()}")
    
    # Example 5: Get knowledge base by product name
    phone_kb = registry.get_knowledge_base("phone_case")
    if phone_kb:
        print(f"\nPhone Case KB: {phone_kb.PRODUCT_NAME}")
        print(f"Print Area: {phone_kb.PRINT_AREA}")
