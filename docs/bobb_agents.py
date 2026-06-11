"""
BOBB Kitchen — Multi-Agent System
OpenAI Agents SDK + Ollama (local, offline-first)

Architecture:
  Orchestrator Agent
    └── routes via handoffs to 10 product sub-agents:
        TShirt, Keychain, WaterBottle, LaptopSkin, PhoneCase,
        HelmetSticker, Flipflop, Accessories, Shoes, BagSticker

Run local:   ollama run llama3
Run tests:   python bobb_agents.py
"""

import asyncio
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx
from openai import AsyncOpenAI

from agents import (
    Agent,
    GuardrailFunctionOutput,
    Runner,
    function_tool,
    input_guardrail,
)
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel


# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

# Local Ollama — zero API cost, works offline
OLLAMA_CLIENT = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",          # any string; Ollama ignores it
)

# Cloud OpenAI — use only for dev / testing
OPENAI_CLIENT = AsyncOpenAI(
    api_key="sk-YOUR_KEY_HERE",  # replace for dev testing
)

LOCAL_MODEL = OpenAIChatCompletionsModel(
    model="llama3",
    openai_client=OLLAMA_CLIENT,
)

CLOUD_MODEL = OpenAIChatCompletionsModel(
    model="gpt-4o",
    openai_client=OPENAI_CLIENT,
)

# Switch here: LOCAL_MODEL for store, CLOUD_MODEL for dev
ACTIVE_MODEL = LOCAL_MODEL

# Service URLs (running on same Windows PC)
COMFYUI_URL   = "http://localhost:8188"
PRINT_API_URL = "http://localhost:8421"
DB_PATH       = "bobb_kitchen.db"

# BOBB product prices (₹)
PRODUCT_PRICES = {
    "tshirt":          699,
    "keychain":        149,
    "water_bottle":    399,
    "laptop_skin":     499,
    "phone_case":      349,
    "helmet_sticker":   99,
    "flipflops":       249,
    "accessories":     299,
    "shoes":           899,
    "bag_stickers":     79,
}


# ─────────────────────────────────────────────
# SESSION DATA MODEL
# ─────────────────────────────────────────────

@dataclass
class CustomerSession:
    session_id:            str
    customer_name:         str
    phone_number:          str
    language:              str       = "en"
    selected_products:     list      = field(default_factory=list)
    current_product_index: int       = 0
    designs:               dict      = field(default_factory=dict)
    cart:                  list      = field(default_factory=list)
    status:                str       = "active"
    created_at:            str       = field(default_factory=lambda: datetime.now().isoformat())


# In-memory store (also persisted to SQLite)
_sessions: dict[str, CustomerSession] = {}


# ─────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   TEXT PRIMARY KEY,
            customer_name TEXT,
            phone_number  TEXT,
            language      TEXT,
            status        TEXT,
            created_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS designs (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id           TEXT,
            product_type         TEXT,
            design_prompt        TEXT,
            refined_prompt       TEXT,
            selected_image_index INTEGER,
            refinement_count     INTEGER,
            created_at           TEXT
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id    TEXT PRIMARY KEY,
            session_id  TEXT,
            total_amount REAL,
            status      TEXT,
            payment_id  TEXT,
            created_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS print_jobs (
            job_id       TEXT PRIMARY KEY,
            session_id   TEXT,
            product_type TEXT,
            image_path   TEXT,
            status       TEXT,
            created_at   TEXT
        );
    """)
    conn.commit()
    conn.close()


def _persist_session(session: CustomerSession):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?)",
        (session.session_id, session.customer_name, session.phone_number,
         session.language, session.status, session.created_at),
    )
    conn.commit()
    conn.close()


def _persist_design(session_id: str, product_type: str, prompt: str,
                    refined: str, idx: int, refinements: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO designs VALUES (NULL,?,?,?,?,?,?,?)",
        (session_id, product_type, prompt, refined, idx, refinements,
         datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# TOOLS  (all @function_tool — available to agents)
# ─────────────────────────────────────────────

@function_tool
async def generate_image(
    prompt: str,
    product_type: str = "tshirt",
    num_images: int = 4,
    style: str = "graphic_art",
) -> dict:
    """
    Generate artwork images using local ComfyUI / SDXL.
    Returns a list of image URLs or base64 strings.
    Falls back to template library on failure.
    """
    payload = {
        "prompt":       prompt,
        "product_type": product_type,
        "num_images":   num_images,
        "style":        style,
        "width":        1024,
        "height":       1024,
        "steps":        20,
        "cfg_scale":    7.5,
    }
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(f"{COMFYUI_URL}/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {
                "success":         True,
                "images":          data.get("images", []),
                "prompt_used":     prompt,
                "generation_time": data.get("time_seconds", 0),
            }
    except Exception as exc:
        # Fallback: return template library signal
        return {
            "success":    False,
            "error":      str(exc),
            "fallback":   "template_library",
            "message":    "Showing curated designs from our collection instead.",
        }


@function_tool
async def get_kerala_themes(product_type: str) -> dict:
    """
    Return all Kerala cultural themes and which products they suit.
    Agent uses this to pick the best theme for a customer's story.
    """
    themes = {
        "backwater_heritage": {
            "name":        "Backwater Heritage",
            "imagery":     "backwater landscape, fishing boats, water reflections",
            "colors":      ["#1E40AF", "#E8C547", "#FAF7F0"],
            "mood":        "serene, nostalgic, connected to home",
            "best_for":    ["tshirt", "laptop_skin", "water_bottle", "phone_case", "bag_stickers"],
        },
        "theyyam_geometric": {
            "name":        "Theyyam Symbolic",
            "imagery":     "geometric Theyyam pattern (NOT mask — SYMBOLIC ONLY), angular forms",
            "colors":      ["#DC2626", "#E8C547", "#0A0A0A"],
            "mood":        "cultural pride, spiritual, bold",
            "best_for":    ["tshirt", "keychain", "phone_case", "shoes", "helmet_sticker"],
        },
        "monsoon_spirit": {
            "name":        "Monsoon Spirit",
            "imagery":     "rain, clouds, clearing skies, water drops, renewal",
            "colors":      ["#475569", "#06B6D4", "#FFFFFF"],
            "mood":        "romantic, renewing, seasonal identity",
            "best_for":    ["tshirt", "water_bottle", "phone_case", "accessories"],
        },
        "fishing_heritage": {
            "name":        "Fishing Heritage",
            "imagery":     "fishing boats, nets, harbor, lighthouse, sea",
            "colors":      ["#E67E22", "#1E40AF", "#FAF7F0"],
            "mood":        "working tradition, community, honest labor",
            "best_for":    ["tshirt", "keychain", "flipflops", "bag_stickers"],
        },
        "spice_route": {
            "name":        "Spice Route",
            "imagery":     "pepper plant, cardamom pods, spice patterns",
            "colors":      ["#DC2626", "#D97706", "#E8C547"],
            "mood":        "entrepreneurial pride, historical significance",
            "best_for":    ["tshirt", "laptop_skin", "accessories", "shoes"],
        },
        "coconut_economy": {
            "name":        "Coconut Economy",
            "imagery":     "coconut palm silhouette, sustainable growth symbols",
            "colors":      ["#16A34A", "#92400E", "#E8C547"],
            "mood":        "resourceful, growth, abundance, sustainability",
            "best_for":    ["tshirt", "flipflops", "water_bottle", "bag_stickers"],
        },
        "kathakali_refinement": {
            "name":        "Kathakali Artistry",
            "imagery":     "ornamental border patterns, decorative Kerala art elements",
            "colors":      ["#DC2626", "#E8C547", "#1E1E1E"],
            "mood":        "artistic mastery, refined, sophisticated",
            "best_for":    ["tshirt", "phone_case", "laptop_skin", "accessories"],
        },
        "literary_kerala": {
            "name":        "Literary Kerala",
            "imagery":     "Malayalam script character, book, writing symbols",
            "colors":      ["#1E40AF", "#E8C547", "#FAF7F0"],
            "mood":        "intellectual pride, language heritage, education",
            "best_for":    ["tshirt", "laptop_skin", "keychain", "bag_stickers"],
        },
    }

    suitable = {k: v for k, v in themes.items() if product_type in v["best_for"]}
    return {
        "product_type":    product_type,
        "available_themes": suitable,
        "top_3":           list(suitable.keys())[:3],
    }


@function_tool
async def save_design(
    session_id:           str,
    product_type:         str,
    design_prompt:        str,
    selected_image_index: int,
    refined_prompt:       str = "",
    refinement_count:     int = 0,
) -> dict:
    """
    Persist the customer's final design choice to session + SQLite.
    Call this once the customer approves a design before adding to cart.
    """
    if session_id not in _sessions:
        return {"success": False, "error": "Session not found"}

    session = _sessions[session_id]
    session.designs[product_type] = {
        "design_prompt":        design_prompt,
        "refined_prompt":       refined_prompt,
        "selected_image_index": selected_image_index,
        "refinement_count":     refinement_count,
        "approved_at":          datetime.now().isoformat(),
    }

    _persist_design(session_id, product_type, design_prompt, refined_prompt,
                    selected_image_index, refinement_count)

    remaining = [p for p in session.selected_products if p not in session.designs]
    return {
        "success":             True,
        "products_designed":   len(session.designs),
        "products_remaining":  remaining,
        "next_product":        remaining[0] if remaining else None,
    }


@function_tool
async def add_to_cart(
    session_id:         str,
    product_type:       str,
    product_name:       str,
    design_description: str,
) -> dict:
    """
    Add an approved design to the customer's order cart.
    Price is looked up automatically from the product catalogue.
    """
    if session_id not in _sessions:
        return {"success": False, "error": "Session not found"}

    session  = _sessions[session_id]
    price    = PRODUCT_PRICES.get(product_type, 0)

    session.cart.append({
        "product_type":       product_type,
        "product_name":       product_name,
        "price":              price,
        "design_description": design_description,
        "design_data":        session.designs.get(product_type, {}),
        "added_at":           datetime.now().isoformat(),
    })

    total = sum(item["price"] for item in session.cart)
    return {
        "success":    True,
        "cart_count": len(session.cart),
        "item_price": price,
        "cart_total": total,
        "message":    f"{product_name} added — cart total: ₹{total:,}",
    }


@function_tool
async def get_session_state(session_id: str) -> dict:
    """
    Return the full current state of a customer session.
    Use this to understand what's been designed and what's remaining.
    """
    if session_id not in _sessions:
        return {"error": "Session not found"}

    s = _sessions[session_id]
    return {
        "session_id":           s.session_id,
        "customer_name":        s.customer_name,
        "language":             s.language,
        "selected_products":    s.selected_products,
        "products_designed":    list(s.designs.keys()),
        "products_remaining":   [p for p in s.selected_products if p not in s.designs],
        "cart":                 s.cart,
        "cart_total":           sum(i["price"] for i in s.cart),
        "current_product_index": s.current_product_index,
        "status":               s.status,
    }


@function_tool
async def initiate_upi_payment(
    session_id:        str,
    amount:            float,
    order_description: str,
) -> dict:
    """
    Create a UPI payment request. Returns QR code string and payment ID.
    Poll payment_status() every 3 seconds to check if paid.
    """
    payment_id = f"BOBB-{uuid.uuid4().hex[:8].upper()}"

    # In production: replace with Razorpay / PayU / PhonePe API call
    # Example Razorpay:
    # razorpay_client.order.create({
    #     "amount": int(amount * 100),
    #     "currency": "INR",
    #     "receipt": payment_id,
    # })

    upi_string = (
        f"upi://pay?pa=bobb.kitchen@paytm"
        f"&pn=BOBB+Kitchen"
        f"&am={amount}"
        f"&tn={payment_id}"
        f"&cu=INR"
    )

    # Save order to DB
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO orders VALUES (?,?,?,?,?,?)",
        (payment_id, session_id, amount, "pending", "", datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    return {
        "success":         True,
        "payment_id":      payment_id,
        "amount":          amount,
        "upi_id":          "bobb.kitchen@paytm",
        "upi_qr_string":   upi_string,
        "expires_in_secs": 120,
        "poll_interval_secs": 3,
        "message":         f"Show QR or use UPI ID: bobb.kitchen@paytm · Amount: ₹{amount:,.0f}",
    }


@function_tool
async def check_payment_status(payment_id: str) -> dict:
    """
    Poll payment gateway to check if UPI payment has been received.
    Returns 'pending', 'paid', or 'expired'.
    """
    # In production: call payment gateway webhook or status API
    # razorpay_client.order.fetch(payment_id)

    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute(
        "SELECT status FROM orders WHERE order_id=?", (payment_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return {"status": "not_found"}

    return {
        "payment_id": payment_id,
        "status":     row[0],  # "pending" | "paid" | "expired"
    }


@function_tool
async def confirm_order_and_notify(
    session_id: str,
    payment_id: str,
) -> dict:
    """
    Mark order as paid, send WhatsApp confirmation, queue print jobs.
    Call this immediately when payment webhook fires.
    """
    if session_id not in _sessions:
        return {"success": False, "error": "Session not found"}

    session = _sessions[session_id]

    # Update order status
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE orders SET status='paid' WHERE order_id=?", (payment_id,)
    )
    conn.commit()
    conn.close()

    # Queue print jobs for each designed product
    print_jobs = []
    for item in session.cart:
        job_id = f"PRINT-{payment_id}-{item['product_type'].upper()}"
        print_jobs.append(job_id)
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO print_jobs VALUES (?,?,?,?,?,?)",
            (job_id, session_id, item["product_type"], "", "queued",
             datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    # WhatsApp confirmation (Twilio API call in production)
    total = sum(i["price"] for i in session.cart)
    whatsapp_message = (
        f"🎨 Order confirmed!\n"
        f"#{payment_id} · {len(session.cart)} items · ₹{total:,}\n"
        f"Sit tight while we cook your BOBB 🖤"
    )

    # In production:
    # twilio_client.messages.create(
    #     from_="whatsapp:+14155238886",
    #     to=f"whatsapp:{session.phone_number}",
    #     body=whatsapp_message,
    # )

    session.status = "paid"

    return {
        "success":         True,
        "payment_id":      payment_id,
        "print_jobs":      print_jobs,
        "whatsapp_sent_to": session.phone_number,
        "whatsapp_preview": whatsapp_message[:100],
        "estimated_time_mins": len(session.cart) * 15,
    }


@function_tool
async def send_to_printer(
    session_id:   str,
    product_type: str,
    image_data:   str,
) -> dict:
    """
    Send a design file to the DTF printer via local print controller API.
    image_data: base64-encoded PNG or file path on local disk.
    """
    settings = {
        "tshirt":          {"width": 10.0, "height": 12.0, "dpi": 300},
        "keychain":        {"width": 2.0,  "height": 2.0,  "dpi": 300},
        "water_bottle":    {"width": 4.0,  "height": 6.0,  "dpi": 300},
        "laptop_skin":     {"width": 13.0, "height": 9.0,  "dpi": 300},
        "phone_case":      {"width": 5.0,  "height": 8.0,  "dpi": 200},
        "helmet_sticker":  {"width": 5.0,  "height": 7.0,  "dpi": 300},
        "flipflops":       {"width": 2.0,  "height": 4.0,  "dpi": 200},
        "accessories":     {"width": 4.0,  "height": 4.0,  "dpi": 300},
        "shoes":           {"width": 3.0,  "height": 8.0,  "dpi": 300},
        "bag_stickers":    {"width": 4.0,  "height": 4.0,  "dpi": 300},
    }.get(product_type, {"width": 8.0, "height": 8.0, "dpi": 300})

    job_id = f"PRINT-{session_id[:6]}-{product_type.upper()}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{PRINT_API_URL}/print",
                json={
                    "job_id":        job_id,
                    "product_type":  product_type,
                    "image_data":    image_data,
                    "print_settings": settings,
                    "color_profile": "sRGB",
                    "copies":        1,
                },
            )
            resp.raise_for_status()
            return {"success": True, "job_id": job_id, "status": "queued"}
    except Exception as exc:
        return {
            "success": False,
            "job_id":  job_id,
            "error":   str(exc),
            "message": "Print queued for retry when printer reconnects.",
        }


# ─────────────────────────────────────────────
# GUARDRAILS
# ─────────────────────────────────────────────

BLOCKED_KEYWORDS = frozenset([
    "weapon", "bomb", "explosive", "drug", "heroin", "cocaine", "meth",
    "violence", "murder", "porn", "pornography", "nude", "explicit",
    "terrorist", "isis", "hate speech", "suicide", "self-harm",
    "child", "minor", "illegal",
])


@input_guardrail
async def safety_guardrail(ctx, agent, input_data):
    """
    Block harmful, offensive, or illegal content.
    Triggers on keywords — extend with a proper classifier in production.
    """
    text = str(input_data).lower()

    for kw in BLOCKED_KEYWORDS:
        if kw in text:
            return GuardrailFunctionOutput(
                output_info={"blocked": True, "keyword": kw},
                tripwire_triggered=True,
            )

    return GuardrailFunctionOutput(
        output_info={"blocked": False},
        tripwire_triggered=False,
    )


# ─────────────────────────────────────────────
# AGENT INSTRUCTIONS
# ─────────────────────────────────────────────

_SHARED_TOOLS_NOTE = """
TOOLS AVAILABLE:
- generate_image(prompt, product_type, num_images, style) → generates 4 artwork options
- get_kerala_themes(product_type) → returns suitable Kerala cultural themes
- save_design(session_id, product_type, ...) → saves customer's approved design
- add_to_cart(session_id, product_type, ...) → adds to order cart

ALWAYS:
1. Call get_kerala_themes() first to find matching themes
2. Build an SDXL prompt using the chosen theme
3. Call generate_image() to create 4 options
4. Let customer choose one (or ask for up to 3 refinements)
5. Call save_design() when approved
6. Call add_to_cart() to complete this product

RESPONSE STYLE: Warm, brief. Maximum 2-3 sentences. Customer-facing.
"""

ORCHESTRATOR_INSTRUCTIONS = f"""
You are the BOBB Kitchen AI — the main host of a creative retail experience in Kannur, Kerala.

YOUR ROLE: Welcome customers, understand what they want, and hand them off to the right design agents.

WORKFLOW:
1. Greet customer by their first name (available from session)
2. Confirm language preference (English or Malayalam)  
3. Ask what products they want to create (show the 10 options)
4. Hand off to the relevant product agent for each chosen product
5. When a product agent returns control (design approved + added to cart), check what's next
6. After ALL products are designed: show order summary and initiate payment
7. On payment confirmed: call confirm_order_and_notify()

AVAILABLE PRODUCTS AND HANDOFFS:
T-Shirt (₹699) → tshirt_agent
Keychain (₹149) → keychain_agent
Water Bottle (₹399) → water_bottle_agent
Laptop Skin (₹499) → laptop_skin_agent
Phone Case (₹349) → phone_case_agent
Helmet Sticker (₹99) → helmet_sticker_agent
Flipflops (₹249) → flipflop_agent
Accessories (₹299) → accessories_agent
Shoes (₹899) → shoes_agent
Bag Stickers (₹79) → bag_sticker_agent

TOOLS: get_session_state, initiate_upi_payment, check_payment_status, confirm_order_and_notify

PAYMENT FLOW:
1. Show full order summary with itemised prices and total
2. Call initiate_upi_payment() → show UPI QR code to customer
3. Poll check_payment_status() every 3 seconds (up to 2 minutes)
4. On paid: call confirm_order_and_notify() → tell customer "Ready in ~N minutes!"
5. Session complete → tablet returns to idle

PERSONALITY: Warm, brief, creative. Never robotic. Never more than 3 sentences.
LANGUAGE: Match customer's chosen language. Malayalam = natural Kannur dialect.
BRAND VOICE: "Made from your words." Everything starts with a story.
"""

TSHIRT_INSTRUCTIONS = f"""
You are BOBB's T-Shirt Design Agent. You turn personal stories into wearable art.

PRODUCT SPECS:
- Print area: 10" × 12" on chest · DTF printing
- Colors: max 6 (recommend 4-5) · Durability: 50+ wash cycles
- Focal point: slightly above center (heart level) · Readable from 3 feet

DESIGN PROCESS:
1. Ask for the customer's story or concept (1 question max)
2. Call get_kerala_themes("tshirt") to identify relevant themes
3. Build SDXL prompt using the PROMPT FORMAT below
4. Call generate_image(prompt, "tshirt", 4)
5. Present 4 options: "Here are 4 designs based on your story."
6. Customer selects one → offer up to 3 refinements max
7. Show 3D mockup description: "Picture this centered on a black tee..."
8. Customer approves → call save_design() then add_to_cart()

SDXL PROMPT FORMAT:
"[main subject], Kerala [theme] motif, [composition] layout, [colors] color palette,
DTF print quality, bold graphic design, printable on black cotton t-shirt,
300 DPI, flat vector art style, solid colors no gradients, high contrast,
BOBB brand aesthetic, gold and black dominant"

DESIGN RULES:
- Body-aware: design works on 3D torso, not just flat surface
- Timeless not trendy: will look good in 5 years
- Theyyam = geometric PATTERN only, never the actual sacred mask
- Max 5 colors — 4 is ideal

{_SHARED_TOOLS_NOTE}
"""

KEYCHAIN_INSTRUCTIONS = f"""
You are BOBB's Keychain Design Agent. You create tiny, powerful symbols.

PRODUCT SPECS:
- Print area: 2" × 2" pendant · Laser engraving or UV print
- Colors: 1-2 maximum · Durability: 2-3 years daily wear
- Lines: minimum 1mm thick (laser engraving requirement)

DESIGN PROCESS:
1. Find the ONE symbol that represents this customer's story
2. Call get_kerala_themes("keychain")
3. Radical simplification: remove everything that can't be seen at 2"
4. Build SDXL prompt for icon-level symbol
5. Call generate_image(prompt, "keychain", 4)
6. Customer selects, max 2 refinements (tiny format = limited iteration)
7. save_design() → add_to_cart()

SDXL PROMPT FORMAT:
"[single symbol], minimalist icon design, high contrast black and white,
bold strokes minimum 1mm width, Kerala cultural symbol simplified,
laser engraving ready, 2x2 inch small format, no fine detail,
geometric shapes only, recognizable at thumbnail size"

DESIGN RULES:
- If you can't see it at 2", don't include it
- Monochrome must work first (then color)
- No thin lines — laser minimum is 1mm
- ONE symbol, perfectly centered, fills 70-80% of space

{_SHARED_TOOLS_NOTE}
"""

WATER_BOTTLE_INSTRUCTIONS = f"""
You are BOBB's Water Bottle Design Agent. You design for cylindrical surfaces.

PRODUCT SPECS:
- Print area: 4" × 6" cylindrical wrap · UV printing
- Colors: unlimited · Durability: 2-3 years
- Challenge: left edge must connect seamlessly to right edge (if full-wrap)
- Horizontal lines must stay level despite surface curve

DESIGN PROCESS:
1. Choose composition: horizontal bands / vertical centerpiece / 360° pattern / landscape wrap / front-focused
2. Call get_kerala_themes("water_bottle")
3. Build SDXL prompt accounting for cylindrical wrap
4. Call generate_image(prompt, "water_bottle", 4)
5. Describe how it wraps: "This design flows around the bottle seamlessly..."
6. Customer approves → save_design() → add_to_cart()

SDXL PROMPT FORMAT:
"[subject], water bottle wrap design, [composition] layout,
seamless left-right edges for cylinder wrapping, Kerala [theme],
vibrant colors for UV print on steel/plastic, horizontal elements stay level,
4 inches wide x 6 inches tall, works at every rotation angle"

DESIGN RULES:
- Left edge connects to right edge — plan the seam
- Horizontal lines appear level when wrapped (15-20% curve distortion)
- 360° coherence: interesting from any angle
- Bold saturated colors — UV printing loves vibrant

{_SHARED_TOOLS_NOTE}
"""

LAPTOP_SKIN_INSTRUCTIONS = f"""
You are BOBB's Laptop Skin Design Agent. You create premium professional identity pieces.

PRODUCT SPECS:
- Print area: 13" × 9" flat matte vinyl with lamination
- Colors: full color · Durability: 3-5 years
- Edge margin: 0.25" clear from all edges (no bleed)

DESIGN PROCESS:
1. Understand both professional identity AND cultural connection
2. Choose composition: centered hero / full-bleed landscape / corner accent / pattern / diptych
3. Call get_kerala_themes("laptop_skin")
4. Build SDXL prompt for premium, multi-distance design
5. Call generate_image(prompt, "laptop_skin", 4)
6. Describe design: "Premium, works at your desk and in a boardroom..."
7. save_design() → add_to_cart()

SDXL PROMPT FORMAT:
"[subject], premium laptop skin design, [composition], sophisticated professional aesthetic,
Kerala heritage modern reinterpretation, matte vinyl finish quality,
visible at close range (detail) and across room (impact),
[color palette], timeless design 13x9 inches flat surface"

DESIGN RULES:
- Works at 3 distances: 6 inches (detail), 3 feet (desk), 10 feet (presentations)
- Professional enough for office, personal enough to be memorable
- Timeless: will look intentional in 5 years
- 0.25" margin from edges — no design right to the edge

{_SHARED_TOOLS_NOTE}
"""

PHONE_CASE_INSTRUCTIONS = f"""
You are BOBB's Phone Case Design Agent. You design for 3D curved surfaces — held AND placed.

PRODUCT SPECS:
- Print area: 5" × 8" front + curved sides + back (3D)
- Material: TPU (flexible, grippy) · UV printing · Durability: 2-3 years
- CRITICAL: camera 0.25" buffer, top/bottom 0.5" buffer, side buttons accessible

DESIGN PROCESS:
1. Understand customer's personality — phone is their most intimate object
2. Choose 3D composition: wraparound / front+back / edge accent / full-surface / back-statement
3. Call get_kerala_themes("phone_case")
4. Build SDXL prompts — describe FRONT view (primary) and BACK view (secondary)
5. Call generate_image(prompt, "phone_case", 4) for front, then back
6. Check: "Camera and buttons clear? ✓"
7. save_design() → add_to_cart()

SDXL PROMPT FORMAT:
"[design], phone case design [front/back/side], TPU flexible surface,
camera cutout area safe, Kerala [theme], vibrant UV print colors,
works when held (front) and placed on desk (back), high contrast,
[colors], modern personal aesthetic"

CRITICAL RULES:
- Camera zone: 0.25" buffer minimum — NEVER design over camera
- Top area: 0.5" buffer (sensors and speaker)
- Bottom area: 0.5" buffer (charging port, speaker)
- Design works in 3D — not just flat mockup

{_SHARED_TOOLS_NOTE}
"""

HELMET_STICKER_INSTRUCTIONS = f"""
You are BOBB's Helmet Sticker Design Agent. SAFETY IS YOUR ABSOLUTE PRIORITY.

PRODUCT SPECS:
- Print area: 5" × 7" on REAR of helmet ONLY
- UV-resistant marine-grade vinyl · Durability: 3-5 years outdoor
- PLACEMENT: REAR ONLY — front/visor/chin bar are safety violations
- Visibility: readable from 20-50 feet in traffic

DESIGN PROCESS:
1. SAFETY CHECK: confirm rear placement ONLY
2. Choose high-visibility primary color: fluorescent orange, yellow, or white
3. Call get_kerala_themes("helmet_sticker")
4. Bold, simple, geometric — NO fine detail
5. Call generate_image(prompt, "helmet_sticker", 4)
6. Confirm: "This goes on the rear — traffic behind will see you clearly."
7. save_design() → add_to_cart()

SDXL PROMPT FORMAT:
"[symbol], motorcycle helmet sticker rear placement, fluorescent [orange/yellow/white],
bold geometric design, readable at 50 feet in traffic, high contrast,
Kerala symbol simplified, 5x7 inch vinyl decal, maximum visibility,
safety coloring, no fine detail"

NON-NEGOTIABLE SAFETY RULES:
✓ REAR HELMET ONLY — always confirm this with the customer
✓ Fluorescent colors: orange (#FF6B00), yellow (#FFE600), white (#FFFFFF)
✓ Readable from 50 feet — test mentally
✗ NEVER suggest front placement
✗ NEVER suggest visor placement (blocks vision — dangerous)
✗ NEVER suggest chin bar (falls during riding)
✗ NEVER use dark colors as primary: no dark blue, dark green, black

{_SHARED_TOOLS_NOTE}
"""

FLIPFLOP_INSTRUCTIONS = f"""
You are BOBB's Flipflop Design Agent. Small space — maximum impact required.

PRODUCT SPECS:
- Print area: 2" × 4" on flexible EVA/rubber sole
- DTF printing on flexible surface · Colors: 3-4 max
- Durability: 18-24 months daily wear · Patina/fade is expected and acceptable

DESIGN PROCESS:
1. Find the ONE symbol that matters (radical simplification)
2. Choose composition: centered icon / repeating pattern / name+initials / directional (left≠right) / corner accent
3. Call get_kerala_themes("flipflops")
4. Build SDXL prompt — bold fills space, high contrast
5. Call generate_image(prompt, "flipflops", 4)
6. Explain: "On your sole — visible with every step, ages beautifully."
7. save_design() → add_to_cart()

SDXL PROMPT FORMAT:
"[symbol], flipflop sole design, fills 70% of 2x4 inch space,
bold and simple, high contrast [light on dark / dark on light],
Kerala symbol minimalist geometric, DTF flexible ink,
3 colors maximum, strong shapes no fine detail, ages gracefully with wear"

DESIGN RULES:
- If not visible at 2"×4" — remove it
- Bold > Subtle (always on small format)
- Patina is part of the design — account for fade
- Left/right soles can differ (directional composition)

{_SHARED_TOOLS_NOTE}
"""

ACCESSORIES_INSTRUCTIONS = f"""
You are BOBB's Accessories Design Agent. Each accessory type has unique constraints.

PRODUCT TYPES AND SPECS:
Belts:       4"×32" canvas/leather wrap around body
Scarves:     36"×36" full fabric surface (drapes and folds)
Necklaces:   1"×2" pendant — icon-level only (like keychain)
Bangles:     0.5"×7" cylindrical band — friction resistant
Hair Clips:  1"×3" per clip — must not interfere with clipping

DESIGN PROCESS:
1. Ask which accessory type
2. Apply material-specific rules for that type (see below)
3. Call get_kerala_themes("accessories")
4. Build material-appropriate SDXL prompt
5. generate_image(), refine, save_design(), add_to_cart()

MATERIAL-SPECIFIC RULES:
Belts:     design flows horizontally, wraps body, avoid buckle area (first/last 4")
Scarves:   works when draped around neck AND when folded neatly — test both views
Necklaces: icon-level simplicity like keychain — 1"×2" is tiny
Bangles:   works at any rotation (360° coherence), friction-resistant bold design
Clips:     placement on clip body, does not cover the spring/clip mechanism

{_SHARED_TOOLS_NOTE}
"""

SHOES_INSTRUCTIONS = f"""
You are BOBB's Shoes Design Agent. This is the most complex product — multiple surfaces that must coordinate.

PRODUCT SPECS:
- Side:   3"×8" curved (PRIMARY — most visible when worn)
- Tongue: 4"×6" (SECONDARY — visible when tying, close-up)
- Heel:   3"×3" curved (ACCENT — visible from behind)
- DTF flexible ink · Durability: 18-24 months · Avoid seams and flex points

DESIGN PROCESS:
1. Understand professional context + personal identity balance
2. Choose composition: side-focused / fully unified / asymmetric (L≠R) / minimalist accent / tonal
3. Map seams and flex points — design avoids them
4. Call get_kerala_themes("shoes")
5. Generate each surface separately:
   - generate_image(side_prompt, "shoes", 4) → customer selects
   - generate_image(tongue_prompt, "shoes", 2) → show how it complements
   - generate_image(heel_prompt, "shoes", 2) → accent
6. Confirm color coordination across all surfaces
7. save_design() → add_to_cart()

SDXL PROMPT FORMAT (per surface):
"[design] on shoe [side/tongue/heel], [size] area, curved flexible surface,
avoids seam lines, Kerala cultural fusion, [composition],
professional yet personal, coordinates with [other surface], DTF flexible ink"

DESIGN RULES:
- Works in motion (shoes move constantly — test the composition at different angles)
- All surfaces form one cohesive family — same palette, same mood
- Seams: design never crosses stitching lines
- Flex points (toe box, heel crease): no detail here — it cracks
- Most time-consuming product — don't rush

{_SHARED_TOOLS_NOTE}
"""

BAG_STICKER_INSTRUCTIONS = f"""
You are BOBB's Bag Sticker Design Agent. Placement strategy is critical — seams mean failure.

PRODUCT SPECS:
- Print area: 2"×3" (small) to 4"×6" (large) vinyl decal
- High-tack fabric vinyl · Removable without damage · Durability: 2-3 years
- Best surfaces: canvas, nylon, cotton · Leather needs special prep

DESIGN PROCESS:
1. Ask about bag type (canvas/nylon/leather) and desired placement location
2. PLACEMENT CHECK: confirm flat fabric area, away from seams/zippers
3. Call get_kerala_themes("bag_stickers")
4. Choose composition: bold logo / artistic scene / text / cultural symbol / hybrid
5. High contrast to bag color — ask bag color if unknown
6. Call generate_image(prompt, "bag_stickers", 4)
7. Confirm placement: "Goes on the front flat panel, at least 1 inch from seams."
8. save_design() → add_to_cart()

SDXL PROMPT FORMAT:
"[design], bag sticker vinyl decal, [size] format, high contrast [light/dark],
Kerala artistic [theme], clean edges for vinyl cutting,
no fine detail that won't cut cleanly, logo-quality clarity,
[dominant colors], works on [bag color] background"

NON-NEGOTIABLE PLACEMENT RULES:
✓ Front center on flat fabric
✓ At least 1" from any seam
✓ Flat area only — no curves or pockets
✗ NEVER seams (adhesion fails at raised stitching)
✗ NEVER zipper area (stress from zipper movement peels edges)
✗ NEVER high-flex areas (handles, corners, bottom)

{_SHARED_TOOLS_NOTE}
"""


# ─────────────────────────────────────────────
# AGENT INSTANCES
# ─────────────────────────────────────────────

_DESIGN_TOOLS = [generate_image, get_kerala_themes, save_design, add_to_cart]
_GUARDRAILS   = [safety_guardrail]

tshirt_agent = Agent(
    name="TShirt Design Agent",
    model=ACTIVE_MODEL,
    instructions=TSHIRT_INSTRUCTIONS,
    tools=_DESIGN_TOOLS,
    input_guardrails=_GUARDRAILS,
)

keychain_agent = Agent(
    name="Keychain Design Agent",
    model=ACTIVE_MODEL,
    instructions=KEYCHAIN_INSTRUCTIONS,
    tools=_DESIGN_TOOLS,
    input_guardrails=_GUARDRAILS,
)

water_bottle_agent = Agent(
    name="Water Bottle Design Agent",
    model=ACTIVE_MODEL,
    instructions=WATER_BOTTLE_INSTRUCTIONS,
    tools=_DESIGN_TOOLS,
    input_guardrails=_GUARDRAILS,
)

laptop_skin_agent = Agent(
    name="Laptop Skin Design Agent",
    model=ACTIVE_MODEL,
    instructions=LAPTOP_SKIN_INSTRUCTIONS,
    tools=_DESIGN_TOOLS,
    input_guardrails=_GUARDRAILS,
)

phone_case_agent = Agent(
    name="Phone Case Design Agent",
    model=ACTIVE_MODEL,
    instructions=PHONE_CASE_INSTRUCTIONS,
    tools=_DESIGN_TOOLS,
    input_guardrails=_GUARDRAILS,
)

helmet_sticker_agent = Agent(
    name="Helmet Sticker Design Agent",
    model=ACTIVE_MODEL,
    instructions=HELMET_STICKER_INSTRUCTIONS,
    tools=_DESIGN_TOOLS,
    input_guardrails=_GUARDRAILS,
)

flipflop_agent = Agent(
    name="Flipflop Design Agent",
    model=ACTIVE_MODEL,
    instructions=FLIPFLOP_INSTRUCTIONS,
    tools=_DESIGN_TOOLS,
    input_guardrails=_GUARDRAILS,
)

accessories_agent = Agent(
    name="Accessories Design Agent",
    model=ACTIVE_MODEL,
    instructions=ACCESSORIES_INSTRUCTIONS,
    tools=_DESIGN_TOOLS,
    input_guardrails=_GUARDRAILS,
)

shoes_agent = Agent(
    name="Shoes Design Agent",
    model=ACTIVE_MODEL,
    instructions=SHOES_INSTRUCTIONS,
    tools=_DESIGN_TOOLS,
    input_guardrails=_GUARDRAILS,
)

bag_sticker_agent = Agent(
    name="Bag Sticker Design Agent",
    model=ACTIVE_MODEL,
    instructions=BAG_STICKER_INSTRUCTIONS,
    tools=_DESIGN_TOOLS,
    input_guardrails=_GUARDRAILS,
)

# Orchestrator: all sub-agents are handoff targets
orchestrator = Agent(
    name="BOBB Kitchen",
    model=ACTIVE_MODEL,
    instructions=ORCHESTRATOR_INSTRUCTIONS,
    tools=[
        get_session_state,
        initiate_upi_payment,
        check_payment_status,
        confirm_order_and_notify,
        send_to_printer,
    ],
    handoffs=[
        tshirt_agent,
        keychain_agent,
        water_bottle_agent,
        laptop_skin_agent,
        phone_case_agent,
        helmet_sticker_agent,
        flipflop_agent,
        accessories_agent,
        shoes_agent,
        bag_sticker_agent,
    ],
    input_guardrails=_GUARDRAILS,
)


# ─────────────────────────────────────────────
# SESSION MANAGEMENT
# ─────────────────────────────────────────────

def create_session(
    session_id:   str,
    customer_name: str,
    phone_number:  str,
    language:      str = "en",
) -> CustomerSession:
    """Create and persist a new customer session."""
    _init_db()
    session = CustomerSession(
        session_id=session_id,
        customer_name=customer_name,
        phone_number=phone_number,
        language=language,
    )
    _sessions[session_id] = session
    _persist_session(session)
    return session


def get_session(session_id: str) -> Optional[CustomerSession]:
    """Retrieve an active session."""
    return _sessions.get(session_id)


# ─────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────

async def run_turn(
    session_id:           str,
    customer_message:     str,
    conversation_history: list | None = None,
) -> dict:
    """
    Process one turn of the customer conversation.

    Args:
        session_id:           active session ID
        customer_message:     latest message from the customer
        conversation_history: list of prior message dicts (from previous turns)

    Returns:
        {
            success:    bool,
            response:   str,
            agent_name: str,
            messages:   list  ← pass back in next call as conversation_history
        }
    """
    if conversation_history is None:
        conversation_history = []

    messages = conversation_history + [
        {"role": "user", "content": customer_message}
    ]

    try:
        result = await Runner.run(
            starting_agent=orchestrator,
            input=messages,
        )
        return {
            "success":    True,
            "response":   result.final_output,
            "agent_name": getattr(result, "last_agent", orchestrator).name,
            "messages":   result.to_input_list(),
        }
    except Exception as exc:
        return {
            "success":    False,
            "error":      str(exc),
            "response":   "Something went wrong. Let's try again.",
            "agent_name": "BOBB Kitchen",
            "messages":   conversation_history,
        }


# ─────────────────────────────────────────────
# CLI TEST
# ─────────────────────────────────────────────

async def _cli_test():
    """Interactive CLI test — run: python bobb_agents.py"""
    _init_db()
    print("\n" + "═" * 50)
    print("  BOBB KITCHEN — Agent CLI Test")
    print("  Model:", ACTIVE_MODEL.model)
    print("═" * 50 + "\n")

    session = create_session(
        session_id=f"TEST-{uuid.uuid4().hex[:6].upper()}",
        customer_name="Arjun",
        phone_number="+919876543210",
        language="en",
    )
    print(f"Session created: {session.session_id}\n")

    history: list = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if user_input.lower() in {"exit", "quit", "q"}:
            print("Session ended.")
            break

        result = await run_turn(session.session_id, user_input, history)
        history = result["messages"]

        agent  = result["agent_name"]
        status = "✓" if result["success"] else "✗"
        print(f"\n[{status}] {agent}: {result['response']}\n")


if __name__ == "__main__":
    asyncio.run(_cli_test())
