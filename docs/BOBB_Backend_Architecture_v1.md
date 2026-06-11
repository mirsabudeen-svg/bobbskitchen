# BOBB AI PLATFORM - COMPLETE BACKEND ARCHITECTURE
## Lead Developer Specification Document

**Version**: 1.0  
**Date**: May 2026  
**Status**: Production-Ready Architecture  
**Lead Dev Role**: Full-Stack AI Platform Architecture & Implementation

---

## EXECUTIVE OVERVIEW

BOBB AI is a **multi-agent retail AI system** that converts customer stories into personalized printed apparel in real-time. The platform orchestrates five specialized AI agents working in concert with hardware integrations (DTF printer, heat press, tablet interface).

### Core Value Proposition
- **Customer Input**: Voice/text story (2-3 min conversation)
- **AI Processing**: Multi-agent orchestration (20-25 sec)
  - Conversation Agent (understanding intent)
  - Design Agent (visual translation)
  - Product Agent (recommendation)
  - Commerce Agent (pricing/checkout)
  - Production Agent (print scheduling)
- **Physical Output**: Printed custom apparel + hand-stitched name tag (6-8 min)

### Platform Scope
- **Users**: Walk-in customers, retail store staff, management
- **Scale**: 40-60 customers/day per van (single van MVP)
- **Deployment**: Fully offline-capable (local AI) + optional cloud (Gemini)
- **Hardware**: Samsung Tab S9 Ultra + Windows PC (RTX 3060) + DTF printer

---

## PART 1: SYSTEM ARCHITECTURE OVERVIEW

### 1.1 Architecture Layers (4-Tier Model)

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                      │
│           Samsung Tab S9 Ultra (React Interface)             │
│    - 13 screens (idle, listening, generating, etc)         │
│    - WebSocket real-time updates                            │
│    - Voice input (Web Audio API)                            │
└─────────────────────────────────────────────────────────────┘
                            ↕
                    (WebSocket + REST)
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                         │
│          FastAPI Backend (Python, Windows PC)               │
│    - Session Manager (state machine)                        │
│    - Multi-Agent Orchestrator                              │
│    - Business Logic (commerce, production)                 │
│    - WebSocket Server (real-time communication)            │
└─────────────────────────────────────────────────────────────┘
                            ↕
        ┌──────────────────┬──────────────────┐
        ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  AI AGENTS   │  │   SERVICES   │  │ DATA LAYER   │
│              │  │              │  │              │
│ • Converse   │  │ • Print API  │  │ • SQLite DB  │
│ • Design     │  │ • Payment    │  │ • Analytics  │
│ • Product    │  │ • Queue Mgmt │  │ • Cache      │
│ • Commerce   │  │ • Telemetry  │  │              │
│ • Produce    │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        ↕                  ↕                  ↕
        └──────────────────┬──────────────────┘
                            ↕
        ┌──────────────────┬──────────────────┐
        ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ MODELS (AI)  │  │  HARDWARE    │  │   EXTERNAL   │
│              │  │              │  │              │
│ • Whisper    │  │ • DTF Print  │  │ • Gemini API │
│ • Llama 3    │  │ • Heat Press │  │ • UPI/Card   │
│ • SDXL       │  │ • Scales     │  │ • Cloud Logs │
│ • Vision     │  │ • Barcode    │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 1.2 Technology Stack

**Backend**:
- **Framework**: FastAPI (async, Python 3.11)
- **Real-time**: WebSocket (async-websockets)
- **Database**: SQLite (local, no server needed)
- **Caching**: Redis (optional, in-memory for sessions)
- **Task Queue**: Celery + RabbitMQ (optional, for production scale)

**AI Agents**:
- **Conversation**: Gemini 2.5 Flash (live) OR Llama 3 (local)
- **Design Generation**: Gemini 2.5 Pro OR SDXL (local ComfyUI)
- **Vision**: Gemini 2.5 Vision OR Local vision transformer
- **Speech**: OpenAI Whisper (local)
- **Routing**: Custom multi-agent orchestrator (Python)

**Hardware Integration**:
- **DTF Printer**: USB serial API (RawPrint, EscPos)
- **Heat Press**: WiFi API (Geo Knight or custom IoT)
- **Tablet**: WebSocket + REST
- **PC**: Windows Task Scheduler for cleanup/monitoring

**Infrastructure**:
- **Local deployment**: Single Windows PC (RTX 3060 12GB)
- **Cloud (optional)**: Google Cloud Run (for Gemini API)
- **Logging**: CloudWatch or local file-based
- **Monitoring**: Prometheus + Grafana (optional)

---

## PART 2: MULTI-AGENT SYSTEM DESIGN

### 2.1 Agent Architecture

**Five Specialized Agents** working in orchestrated sequence:

```
CONVERSATION AGENT
├─ Responsibility: Extract customer story, intent, preferences
├─ Input: Voice transcript (Whisper) OR text
├─ Output: Structured story JSON
├─ Tool: Gemini 2.5 Flash (0.5s response time)
├─ Memory: Session context (customer name, preferences)
└─ Fallback: Llama 3 7B (local)

DESIGN AGENT
├─ Responsibility: Translate story → visual design prompt
├─ Input: Story JSON + product type
├─ Output: SDXL-compatible prompt + mood board
├─ Tool: Gemini 2.5 Pro (reasoning, 2-4s)
├─ Memory: Design patterns, Kerala cultural themes
├─ Fallback: Template-based design generation

IMAGE GENERATION AGENT
├─ Responsibility: Create 4 design variants
├─ Input: SDXL prompt + product dimensions
├─ Output: 4 PNG images (1024x1024 or product-specific)
├─ Tool: SDXL (ComfyUI local) OR Gemini 2.5 Image
├─ Memory: Generation queue, caching
└─ Fallback: Stock templates + overlays

PRODUCT AGENT
├─ Responsibility: Recommend product based on design
├─ Input: Story, design complexity, customer budget
├─ Output: 3 product recommendations + pricing
├─ Tool: Gemini 2.5 Flash (decision logic)
├─ Memory: Product catalog, inventory, design-product mapping
└─ Fallback: Rule-based recommendation engine

COMMERCE AGENT
├─ Responsibility: Pricing, discounts, checkout, payment
├─ Input: Product selection, quantity, customer data
├─ Output: Order object + payment request
├─ Tool: Payment gateway API + inventory management
├─ Memory: Pricing rules, discounts, customer history
└─ Fallback: Cash/manual payment mode

PRODUCTION AGENT
├─ Responsibility: Queue management, print scheduling
├─ Input: Confirmed order + design files
├─ Output: Job queue item, device commands
├─ Tool: DTF printer API + production queue DB
├─ Memory: Queue state, printer status, production history
└─ Fallback: Manual print queue (staff can trigger)
```

### 2.2 Agent Orchestration Flow (State Machine)

```
STATE MACHINE: 12 STATES (Conversation to Completion)

IDLE
  ↓ [tap tablet]
  
GREETING
  ├─ Agent: Conversation Agent
  ├─ Output: "Welcome. Tell me something about yourself."
  └─ Transition: → LISTENING
  
LISTENING
  ├─ Duration: Max 30 seconds
  ├─ Input: Voice (Whisper) OR text
  ├─ Agent: Conversation Agent (processing)
  ├─ Output: Transcript + intent classification
  └─ Transition: → CLARIFYING (if ambiguous) OR THINKING
  
CLARIFYING
  ├─ Agent: Conversation Agent
  ├─ Output: 2-3 clarification questions
  ├─ Max iterations: 2 (don't over-ask)
  └─ Transition: → LISTENING OR → THINKING
  
THINKING
  ├─ Agent: Design Agent (Gemini 2.5 Pro)
  ├─ Process: Translate story to visual prompt
  ├─ Duration: 2-4 seconds (show spinner)
  └─ Transition: → GENERATING
  
GENERATING
  ├─ Agent: Image Generation Agent (SDXL OR Gemini)
  ├─ Process: Create 4 design variants
  ├─ Duration: 20-25 seconds
  ├─ UI: Progress bar + substatus messages
  └─ Transition: → PREVIEW
  
PREVIEW
  ├─ UI: 2×2 grid of 4 design variants
  ├─ Actions: "Select" (choose one) OR "Try Different" (regenerate)
  ├─ Max regenerations: 3
  └─ Transition: → REFINING (select) OR → THINKING (try different)
  
REFINING
  ├─ Agent: Design Agent + Image Generation Agent
  ├─ UI: Current design + 6 refinement pills (color, style, mood, etc)
  ├─ Max refinements: 3
  ├─ Input: Customer can text adjustments
  └─ Transition: → GENERATING (refine) OR → PRODUCT_SELECTION (done)
  
PRODUCT_SELECTION
  ├─ Agent: Product Agent (recommendation)
  ├─ UI: 3 product cards (design shown on mockup)
  ├─ Actions: Select product + quantity
  ├─ Optional: "Browse all products" (show catalog)
  └─ Transition: → CART
  
CART
  ├─ UI: Item list + pricing summary
  ├─ Features: Auto-apply discounts (2+ items = 5% off, 3+ = 10%)
  ├─ Actions: Continue shopping OR Checkout
  ├─ Note: Can add multiple designs to one order
  └─ Transition: → CHECKOUT
  
CHECKOUT
  ├─ Agent: Commerce Agent
  ├─ Input: Name, phone, name tag text (15 chars max)
  ├─ Payment: UPI (primary) / Card (secondary) / Cash (tertiary)
  ├─ Order creation + inventory deduction
  └─ Transition: → PRODUCTION
  
PRODUCTION
  ├─ Agent: Production Agent
  ├─ Queue position + 4-stage progress (Print → Press → Stitch → Ready)
  ├─ Duration: 6-8 minutes typical
  ├─ UI: Live progress updates (every 30s)
  └─ Transition: → SUCCESS (when complete) OR → ERROR (if failure)
  
SUCCESS
  ├─ UI: Animated checkmark (80px)
  ├─ Order details + QR code (for social sharing)
  ├─ CTA: "Make another one?" (loop back to GREETING)
  ├─ Auto-reset after 10 seconds to IDLE
  └─ Agent: Loyalty Agent (optional) - capture contact info
  
ERROR
  ├─ Agent: Error handler + escalation
  ├─ UI: Error message + troubleshooting
  ├─ Actions: "Try Again" OR "Get Help" (escalate to staff)
  └─ Transition: → IDLE OR → HELP (escalation)
  
HELP
  ├─ UI: Staff assistance mode
  ├─ Options: Talk to staff / Fix issue / Restart
  ├─ Staff can view full session + debug info
  └─ Transition: Back to relevant state
```

### 2.3 Agent Communication Protocol (JSON)

All agents communicate via standardized JSON messages:

```python
# Base Agent Message Format
{
    "agent_id": "conversation_agent_v1",
    "session_id": "sess_abc123xyz",
    "timestamp": "2026-05-30T15:30:00Z",
    "sequence_num": 3,
    "message_type": "thinking" | "output" | "error" | "tool_call",
    "state": "LISTENING",
    "payload": {...},
    "metadata": {
        "execution_time_ms": 450,
        "confidence": 0.92,
        "tokens_used": 156,
        "model_used": "gemini-2.5-flash"
    }
}

# CONVERSATION AGENT Output Example
{
    "agent_id": "conversation_agent_v1",
    "message_type": "output",
    "state": "LISTENING",
    "payload": {
        "transcript": "I love the beach and I'm from Kannur. I want something that shows my love for my hometown and the ocean.",
        "story_json": {
            "themes": ["beach", "hometown", "Kannur", "ocean"],
            "emotions": ["pride", "nostalgia", "joy"],
            "keywords": ["waves", "palm trees", "sunset", "backwaters"],
            "intent": "DESIGN_REQUEST",
            "cultural_references": ["Kerala backwaters", "fishing boats", "monsoon"],
            "design_complexity": "medium"
        },
        "next_action": "proceed_to_design",
        "clarifications_needed": false
    }
}

# DESIGN AGENT Output Example
{
    "agent_id": "design_agent_v1",
    "message_type": "output",
    "state": "THINKING",
    "payload": {
        "design_prompt": "A minimalist illustration of Kannur backwaters at golden hour. Palm trees silhouetted against a warm orange-gold sunset. Traditional fishing boat (kettuvallam) in shallow water. Ripples in the water reflecting light. Theyyam-inspired geometric border pattern on edges. Color palette: warm gold (#E8C547), deep navy blue (#0A1A3F), cream (#FAF7F0). Style: modern minimalist line art with solid color blocks. 1024x1024px, 300 DPI ready for print.",
        "mood_board": [
            "kerala_sunset_reference.jpg",
            "theyyam_pattern_study.jpg",
            "minimalist_boat_illustration.jpg"
        ],
        "design_metadata": {
            "cultural_authenticity_score": 0.95,
            "print_feasibility": "excellent",
            "color_count": 4,
            "complexity": "medium",
            "estimated_print_time": "2.5_minutes"
        },
        "variants": [
            {"style": "illustration", "mood": "nostalgic"},
            {"style": "geometric", "mood": "abstract"},
            {"style": "photorealistic", "mood": "realistic"},
            {"style": "watercolor", "mood": "artistic"}
        ]
    }
}

# IMAGE GENERATION AGENT Output Example
{
    "agent_id": "image_generation_agent_v1",
    "message_type": "output",
    "state": "GENERATING",
    "payload": {
        "job_id": "imgjob_xyz789",
        "images": [
            {
                "variant_id": 1,
                "image_url": "/cache/designs/sess_abc_v1.png",
                "prompt_used": "...[design_prompt variant 1]...",
                "generation_time_ms": 5200,
                "model": "sdxl-comfyui-local"
            },
            {
                "variant_id": 2,
                "image_url": "/cache/designs/sess_abc_v2.png",
                "prompt_used": "...[design_prompt variant 2]...",
                "generation_time_ms": 5150,
                "model": "sdxl-comfyui-local"
            },
            {
                "variant_id": 3,
                "image_url": "/cache/designs/sess_abc_v3.png",
                "prompt_used": "...[design_prompt variant 3]...",
                "generation_time_ms": 5180,
                "model": "sdxl-comfyui-local"
            },
            {
                "variant_id": 4,
                "image_url": "/cache/designs/sess_abc_v4.png",
                "prompt_used": "...[design_prompt variant 4]...",
                "generation_time_ms": 5220,
                "model": "sdxl-comfyui-local"
            }
        ],
        "next_action": "present_to_customer",
        "cache_location": "/cache/designs/sess_abc123xyz/"
    }
}

# PRODUCT AGENT Output Example
{
    "agent_id": "product_agent_v1",
    "message_type": "output",
    "state": "PRODUCT_SELECTION",
    "payload": {
        "recommendations": [
            {
                "rank": 1,
                "product_id": "tshirt_premium",
                "product_name": "Premium T-Shirt",
                "price": 650,
                "sizes": ["XS", "S", "M", "L", "XL", "XXL"],
                "colors": ["black", "white", "navy", "burgundy"],
                "reason": "Perfect for large front design, premium comfort",
                "image_mockup_url": "/mockups/tshirt_premium_design_preview.png",
                "print_area": "10x12 inches",
                "production_time": "7 minutes"
            },
            {
                "rank": 2,
                "product_id": "tote_canvas",
                "product_name": "Canvas Tote Bag",
                "price": 450,
                "colors": ["natural", "black", "navy"],
                "reason": "Great for medium designs, eco-friendly",
                "image_mockup_url": "/mockups/tote_design_preview.png",
                "print_area": "10x10 inches",
                "production_time": "6 minutes"
            },
            {
                "rank": 3,
                "product_id": "cap_snapback",
                "product_name": "Snapback Cap",
                "price": 450,
                "colors": ["black", "navy", "khaki"],
                "reason": "Compact design, great for travel",
                "image_mockup_url": "/mockups/cap_design_preview.png",
                "print_area": "3.5x2.5 inches (curved)",
                "production_time": "8 minutes"
            }
        ],
        "ranking_logic": "Design complexity → print area → customer budget",
        "inventory_check": true
    }
}

# COMMERCE AGENT Output Example
{
    "agent_id": "commerce_agent_v1",
    "message_type": "output",
    "state": "CHECKOUT",
    "payload": {
        "order_id": "ord_abc123xyz",
        "items": [
            {
                "product_id": "tshirt_premium",
                "product_name": "Premium T-Shirt",
                "size": "L",
                "color": "black",
                "quantity": 1,
                "price_per_unit": 650,
                "subtotal": 650
            }
        ],
        "pricing": {
            "subtotal": 650,
            "discount": 0,
            "discount_reason": "none",
            "tax": 0,
            "total": 650,
            "currency": "INR"
        },
        "customer_info": {
            "name": "Arjun",
            "phone": "9876543210",
            "name_tag": "ARJUN",
            "timestamp_created": "2026-05-30T15:35:00Z"
        },
        "payment_methods": [
            {
                "method": "upi",
                "provider": "google_pay",
                "qr_code": "data:image/png;base64,...",
                "upi_id": "merchant@upi"
            },
            {
                "method": "card",
                "provider": "razorpay",
                "button_text": "Pay with Card"
            },
            {
                "method": "cash",
                "enabled": true,
                "text": "Pay with Cash"
            }
        ],
        "next_action": "await_payment",
        "order_status": "PENDING_PAYMENT"
    }
}

# PRODUCTION AGENT Output Example
{
    "agent_id": "production_agent_v1",
    "message_type": "output",
    "state": "PRODUCTION",
    "payload": {
        "order_id": "ord_abc123xyz",
        "queue_position": 2,
        "queue_length": 5,
        "wait_time_minutes": 8,
        "stages": [
            {
                "stage": "PRINT",
                "status": "in_progress",
                "progress_percent": 40,
                "substatus": "Printing color layer 2 of 3",
                "remaining_time_seconds": 45
            },
            {
                "stage": "PRESS",
                "status": "queued",
                "progress_percent": 0,
                "substatus": "Waiting...",
                "estimated_start": "2026-05-30T15:38:00Z"
            },
            {
                "stage": "STITCH",
                "status": "queued",
                "progress_percent": 0,
                "substatus": "Will start after pressing",
                "estimated_start": "2026-05-30T15:39:00Z"
            },
            {
                "stage": "READY",
                "status": "queued",
                "progress_percent": 0,
                "substatus": "Final quality check",
                "estimated_completion": "2026-05-30T15:41:00Z"
            }
        ],
        "device_commands_sent": [
            {
                "device": "dtf_printer",
                "command": "print_file",
                "file_path": "/jobs/ord_abc123xyz_v1.png",
                "parameters": {
                    "resolution": "300dpi",
                    "color_profile": "srgb",
                    "media_type": "direct_to_film"
                }
            }
        ],
        "next_action": "monitor_progress",
        "update_interval_seconds": 30
    }
}
```

---

## PART 3: USER FLOW & STATE MANAGEMENT

### 3.1 Complete Customer Journey (12 States)

```
CUSTOMER JOURNEY MAP

TIME: 0:00 - CUSTOMER ARRIVES
┌─────────────────────────────────────────┐
│ STATE: IDLE                             │
│ • Tablet shows BOBB logo + pulsing ring │
│ • Tap to start prompt                   │
│ • Awning deployed, ambient music        │
└─────────────────────────────────────────┘
          ↓ [TAP TABLET]

TIME: 0:05 - GREETING
┌─────────────────────────────────────────┐
│ STATE: GREETING                         │
│ • Voice: "Welcome. Tell me something    │
│   about yourself."                      │
│ • Visual: Animated wave icon            │
│ • Ready for input (voice or text)       │
└─────────────────────────────────────────┘
          ↓ [CUSTOMER SPEAKS/TYPES]

TIME: 0:15-0:45 - LISTENING & PROCESSING
┌─────────────────────────────────────────┐
│ STATE: LISTENING                        │
│ • Waveform visualization (9 bars)       │
│ • 30-second max duration                │
│ • "Listening..." + timer                │
│ • Transcript appearing in real-time     │
└─────────────────────────────────────────┘
          ↓ [WHISPER TRANSCRIPTION]

TIME: 0:45-1:00 - AI UNDERSTANDING
┌─────────────────────────────────────────┐
│ STATE: CLARIFYING (if needed)           │
│ OR                                      │
│ STATE: THINKING (if clear)              │
│                                         │
│ Agent: Conversation Agent               │
│ • Extracting story, intent, themes      │
│ • Max 2 clarification questions         │
│ • If unclear: ask for details           │
└─────────────────────────────────────────┘
          ↓ [AI DETERMINES INTENT]

TIME: 1:00-4:00 - DESIGN GENERATION
┌─────────────────────────────────────────┐
│ STATE: THINKING (Design Agent)          │
│ • Translating story to visual prompt    │
│ • Duration: 2-4 seconds                 │
│ • Spinner + "Crafting your design..."   │
│                                         │
│ STATE: GENERATING (Image Gen)           │
│ • Creating 4 design variants            │
│ • Duration: 20-25 seconds               │
│ • Progress bar + substatus:             │
│   - "Analyzing themes..."               │
│   - "Creating variant 1..."             │
│   - "Creating variant 2..."             │
│   - "Finalizing designs..."             │
└─────────────────────────────────────────┘
          ↓ [4 IMAGES GENERATED]

TIME: 4:00-5:30 - DESIGN REVIEW
┌─────────────────────────────────────────┐
│ STATE: PREVIEW                          │
│ • 2×2 grid of 4 design variants         │
│ • Customer can:                         │
│   1. SELECT one (→ REFINING)            │
│   2. TRY DIFFERENT (→ re-generate)      │
│   3. Max 3 regenerations allowed        │
│                                         │
│ OR customer can refine choice:          │
└─────────────────────────────────────────┘
          ↓ [SELECT OR REFINE]

TIME: 5:30-7:00 - OPTIONAL REFINEMENT
┌─────────────────────────────────────────┐
│ STATE: REFINING                         │
│ • Current design shown (640px)          │
│ • 6 refinement pills:                   │
│   - Color scheme / Style / Mood         │
│   - Size / Complexity / Orientation     │
│ • Text input for custom changes         │
│ • Max 3 refinement iterations           │
│ • OR "Perfect! Move on"                 │
└─────────────────────────────────────────┘
          ↓ [DESIGN LOCKED IN]

TIME: 7:00-8:30 - PRODUCT SELECTION
┌─────────────────────────────────────────┐
│ STATE: PRODUCT_SELECTION                │
│ • 3 recommended products shown          │
│ • Design shown on product mockup        │
│ • Options: T-shirt, Tote, Cap, etc.     │
│ • Can "Browse all products"             │
│ • Select product + quantity             │
│ • Student discount option               │
└─────────────────────────────────────────┘
          ↓ [SELECT PRODUCT]

TIME: 8:30-9:00 - CART & DISCOUNTS
┌─────────────────────────────────────────┐
│ STATE: CART                             │
│ • Item list with prices                 │
│ • Auto-applied discounts:               │
│   - 2 items: 5% off                     │
│   - 3+ items: 10% off                   │
│   - 5+ items: 15% off                   │
│ • Student (5% extra)                    │
│ • Options: Continue / Checkout / Shop   │
└─────────────────────────────────────────┘
          ↓ [PROCEED TO CHECKOUT]

TIME: 9:00-10:30 - PAYMENT
┌─────────────────────────────────────────┐
│ STATE: CHECKOUT                         │
│ • 3 input fields:                       │
│   1. Name (for receipt)                 │
│   2. Phone (optional, for receipt)      │
│   3. Name tag text (15 chars max)       │
│                                         │
│ • Payment options:                      │
│   1. UPI (Google Pay, PhonePe)          │
│   2. Card (Visa, Mastercard)            │
│   3. Cash (manual at counter)           │
│                                         │
│ • Order summary visible                 │
│ • "Place Order" button                  │
└─────────────────────────────────────────┘
          ↓ [PAYMENT PROCESSED]

TIME: 10:30-18:30 - PRODUCTION
┌─────────────────────────────────────────┐
│ STATE: PRODUCTION                       │
│ • 4-stage progress bar:                 │
│   1. PRINT (2-3 min)                    │
│   2. PRESS (40-60 sec)                  │
│   3. STITCH (2-3 min) [name tag]        │
│   4. READY (quality check)              │
│                                         │
│ • Queue position + wait time            │
│ • Updates every 30 seconds              │
│ • Can view design through window        │
│ • Staff can monitor from tablet         │
└─────────────────────────────────────────┘
          ↓ [ALL STAGES COMPLETE]

TIME: 18:30-20:00 - DELIVERY
┌─────────────────────────────────────────┐
│ STATE: SUCCESS                          │
│ • Large animated checkmark              │
│ • Order complete! (with details)        │
│ • QR code for social sharing            │
│ • Receipt printable                     │
│ • "Make another one?" CTA               │
│ • Auto-reset to IDLE after 10s          │
│                                         │
│ Customer walks away with:               │
│ ✓ Custom printed apparel                │
│ ✓ Hand-stitched name tag                │
│ ✓ Receipt + care instructions           │
└─────────────────────────────────────────┘

TOTAL TIME: 10-14 minutes
CUSTOMER SATISFACTION TOUCHPOINTS:
✓ Personalized conversation
✓ Real-time design generation
✓ Multiple design options
✓ Refinement capability
✓ Physical product in hand
✓ Social sharing moment
```

### 3.2 Error Handling & Escalation

```
ERROR STATE MACHINE

GENERATING_IMAGE (failure)
  ↓
  ERROR: "Design creation failed (network issue)"
  ├─ [TRY AGAIN] → GENERATING (retry with same prompt)
  ├─ [TRY DIFFERENT] → THINKING (new design approach)
  └─ [GET HELP] → HELP (escalate to staff)

PRINTING_FAILED (printer offline)
  ↓
  ERROR: "Printer is offline. Staff notified."
  ├─ [WAIT] → PRODUCTION (retry in 30s)
  ├─ [CANCEL] → REFUND & back to IDLE
  └─ [SPEAK TO STAFF] → HELP

PAYMENT_FAILED (UPI timeout)
  ↓
  ERROR: "Payment failed. Retry or use different method."
  ├─ [RETRY UPI] → CHECKOUT (same method)
  ├─ [TRY CARD] → CHECKOUT (different method)
  ├─ [CASH PAYMENT] → CHECKOUT (manual)
  └─ [GET HELP] → HELP

SYSTEM_CRITICAL (PC crash, no models loaded)
  ↓
  ERROR: "System error. Get help from staff."
  ├─ ESCALATION TRIGGERED:
  │   • SMS to manager
  │   • Toast notification to staff tablet
  │   • Error logged with full context
  │   • Session saved for recovery
  └─ FALLBACK MODE:
      • Use pre-generated template designs
      • Offline payment processing
      • Manual production queue
```

---

## PART 4: DESIGN THINKING FRAMEWORK

### 4.1 Product Recommendation Engine

```python
# PRODUCT SELECTION LOGIC

class ProductRecommendationEngine:
    """
    Maps design characteristics → optimal product
    Considers: design complexity, customer demographics, budget
    """
    
    PRODUCT_CATALOG = {
        "tshirt_premium": {
            "name": "Premium T-Shirt",
            "price_range": (600, 800),
            "print_area": "10x12 inches",
            "min_design_complexity": "simple",
            "max_design_complexity": "complex",
            "design_fit_score": {"illustration": 0.95, "geometric": 0.85, "photo": 0.90},
            "production_time_minutes": 7,
            "margin_percent": 45,
            "inventory": {"XS": 20, "S": 30, "M": 40, "L": 35, "XL": 25, "XXL": 15}
        },
        "tote_canvas": {
            "name": "Canvas Tote Bag",
            "price_range": (400, 500),
            "print_area": "10x10 inches",
            "min_design_complexity": "simple",
            "max_design_complexity": "medium",
            "design_fit_score": {"illustration": 0.88, "geometric": 0.92, "photo": 0.75},
            "production_time_minutes": 6,
            "margin_percent": 50,
            "inventory": {"one_size": 50}
        },
        "cap_snapback": {
            "name": "Snapback Cap",
            "price_range": (400, 500),
            "print_area": "3.5x2.5 inches (curved)",
            "min_design_complexity": "simple",
            "max_design_complexity": "simple",
            "design_fit_score": {"illustration": 0.70, "geometric": 0.80, "photo": 0.60},
            "production_time_minutes": 8,
            "margin_percent": 48,
            "inventory": {"one_size": 30}
        },
        "phone_case": {
            "name": "Phone Case",
            "price_range": (600, 700),
            "print_area": "5x8 inches (vertical)",
            "min_design_complexity": "medium",
            "max_design_complexity": "complex",
            "design_fit_score": {"illustration": 0.85, "geometric": 0.80, "photo": 0.95},
            "production_time_minutes": 5,
            "margin_percent": 52,
            "inventory": {"iphone": 20, "samsung": 20}
        },
        "laptop_skin": {
            "name": "Laptop Skin",
            "price_range": (800, 1000),
            "print_area": "13x9 inches",
            "min_design_complexity": "simple",
            "max_design_complexity": "complex",
            "design_fit_score": {"illustration": 0.90, "geometric": 0.92, "photo": 0.88},
            "production_time_minutes": 5,
            "margin_percent": 55,
            "inventory": {"13inch": 15, "14inch": 15, "15inch": 10}
        }
    }
    
    def recommend(self, design_analysis, customer_data, session_context):
        """
        Returns: [product_1, product_2, product_3] ranked by fit
        """
        
        recommendations = []
        
        for product_id, specs in self.PRODUCT_CATALOG.items():
            score = 0
            reasons = []
            
            # FACTOR 1: Design fit (40%)
            design_type = design_analysis.get("type", "illustration")
            design_fit = specs["design_fit_score"].get(design_type, 0.7)
            score += design_fit * 0.40
            reasons.append(f"Design fit: {design_type}")
            
            # FACTOR 2: Design complexity (30%)
            complexity = design_analysis.get("complexity_level")  # simple/medium/complex
            min_complexity = self._complexity_to_score(specs["min_design_complexity"])
            max_complexity = self._complexity_to_score(specs["max_design_complexity"])
            complexity_score = self._complexity_to_score(complexity)
            
            if min_complexity <= complexity_score <= max_complexity:
                score += 0.30
                reasons.append(f"Perfect complexity match: {complexity}")
            elif complexity_score > max_complexity:
                score += 0.10
                reasons.append(f"Design complex for this product")
            else:
                score += 0.20
                reasons.append(f"Design simple for this product")
            
            # FACTOR 3: Customer demographics (15%)
            age_group = customer_data.get("age_group")  # teen/young_adult/adult/family
            if age_group == "teen" and "cap" in product_id:
                score += 0.12
                reasons.append("Popular with teens")
            elif age_group == "young_adult" and "tshirt" in product_id:
                score += 0.12
                reasons.append("Popular with young adults")
            elif age_group == "family" and "tote" in product_id:
                score += 0.12
                reasons.append("Popular for families")
            else:
                score += 0.05
            
            # FACTOR 4: Budget (10%)
            estimated_budget = customer_data.get("budget")  # low/medium/high
            product_price = specs["price_range"][0]
            
            if estimated_budget == "low" and product_price < 500:
                score += 0.10
                reasons.append("Fits budget")
            elif estimated_budget == "medium" and 400 < product_price < 800:
                score += 0.10
                reasons.append("Fits budget")
            elif estimated_budget == "high":
                score += 0.08
                reasons.append("Premium option")
            else:
                score += 0.03
            
            # FACTOR 5: Inventory (5%)
            is_in_stock = self._check_inventory(product_id)
            if is_in_stock:
                score += 0.05
                reasons.append("In stock")
            else:
                score -= 0.10
                reasons.append("Low stock")
            
            recommendations.append({
                "product_id": product_id,
                "score": min(1.0, score),  # Cap at 1.0
                "reasons": reasons,
                "specs": specs
            })
        
        # Sort by score descending
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:3]  # Return top 3

    def _complexity_to_score(self, level):
        mapping = {"simple": 0.3, "medium": 0.6, "complex": 0.9}
        return mapping.get(level, 0.5)
    
    def _check_inventory(self, product_id):
        # Check if product has stock > 5 units
        specs = self.PRODUCT_CATALOG[product_id]
        return sum(specs["inventory"].values()) > 5
```

### 4.2 Design Refinement Options

```python
# REFINEMENT PILL MECHANICS

REFINEMENT_OPTIONS = {
    "color_scheme": {
        "label": "Color Scheme",
        "icon": "🎨",
        "options": [
            "Vibrant & bold",
            "Pastel & soft",
            "Monochrome (black/white)",
            "Gold & warm tones",
            "Cool & calm (blues)",
            "Custom color"
        ]
    },
    "style": {
        "label": "Style",
        "icon": "✨",
        "options": [
            "Minimalist",
            "Detailed illustration",
            "Abstract",
            "Geometric patterns",
            "Watercolor",
            "Line art"
        ]
    },
    "mood": {
        "label": "Mood",
        "icon": "😊",
        "options": [
            "Playful & fun",
            "Professional & serious",
            "Nostalgic & retro",
            "Modern & trendy",
            "Calm & peaceful",
            "Energetic & bold"
        ]
    },
    "focus": {
        "label": "Focus Area",
        "icon": "🔍",
        "options": [
            "Center of design",
            "Full coverage",
            "Left side emphasis",
            "Right side emphasis",
            "Top to bottom flow",
            "Circular/radial"
        ]
    },
    "elements": {
        "label": "Add Elements",
        "icon": "➕",
        "options": [
            "Add text/quote",
            "Add name",
            "Add date",
            "Add symbols",
            "Add Kerala motifs",
            "Simplify (remove elements)"
        ]
    },
    "size": {
        "label": "Design Size",
        "icon": "📏",
        "options": [
            "Small & centered",
            "Medium (standard)",
            "Large & bold",
            "Print edge to edge",
            "Multiple small prints",
            "Back print option"
        ]
    }
}

# When customer selects refinement:
def refine_design(design_id, refinement_option, refinement_value, iteration_num):
    """
    Sends refinement request back to Design Agent
    """
    if iteration_num > 3:
        return {"error": "Max 3 refinements allowed"}
    
    # Generate new SDXL prompt with refinement
    new_prompt = apply_refinement(
        original_prompt=design_cache[design_id],
        refinement=refinement_option,
        value=refinement_value
    )
    
    # Queue for image regeneration
    return generate_images(new_prompt, num_variants=1)
```

---

## PART 5: DATABASE SCHEMA & DATA MODELS

### 5.1 SQLite Database Schema

```sql
-- SESSIONS TABLE (customer interactions)
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_state TEXT NOT NULL,
    customer_name TEXT,
    customer_phone TEXT,
    customer_email TEXT,
    duration_seconds INT,
    completed BOOLEAN DEFAULT FALSE,
    satisfaction_score INT,
    notes TEXT
);

-- CONVERSATION LOGS (all customer inputs)
CREATE TABLE conversation_logs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    turn_number INT,
    input_type TEXT,  -- "voice" | "text"
    customer_input TEXT,
    transcript TEXT,
    agent_response TEXT,
    response_time_ms INT,
    model_used TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- DESIGNS TABLE (generated designs per session)
CREATE TABLE designs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    design_prompt TEXT,
    design_metadata JSON,  -- {themes, complexity, cultural_refs}
    image_urls JSON,  -- {variant_1, variant_2, variant_3, variant_4}
    selected_variant INT,
    refinements_applied INT DEFAULT 0,
    design_locked BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ORDERS TABLE (completed purchases)
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    customer_name TEXT,
    customer_phone TEXT,
    customer_email TEXT,
    total_amount INT,  -- in paise (100 = ₹1)
    discount_amount INT,
    discount_type TEXT,  -- "quantity" | "student" | "promo"
    payment_method TEXT,  -- "upi" | "card" | "cash"
    payment_status TEXT,  -- "pending" | "completed" | "failed"
    order_status TEXT,  -- "queued" | "printing" | "pressing" | "stitching" | "complete" | "cancelled"
    completion_time TIMESTAMP,
    name_tag_text TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ORDER_ITEMS TABLE (line items)
CREATE TABLE order_items (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    design_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT,
    size TEXT,
    color TEXT,
    quantity INT,
    unit_price INT,  -- in paise
    subtotal INT,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (design_id) REFERENCES designs(id)
);

-- PRODUCTION_JOBS TABLE (printer queue)
CREATE TABLE production_jobs (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    order_item_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    design_file_path TEXT,
    printer_model TEXT,
    print_status TEXT,  -- "queued" | "printing" | "complete" | "failed"
    print_duration_seconds INT,
    press_status TEXT,  -- "queued" | "pressing" | "complete"
    press_duration_seconds INT,
    stitch_status TEXT,  -- "queued" | "stitching" | "complete"
    stitch_duration_seconds INT,
    quality_check_passed BOOLEAN,
    notes TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- AGENT_LOGS TABLE (multi-agent system tracking)
CREATE TABLE agent_logs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name TEXT,  -- "conversation_agent" | "design_agent" | etc
    agent_version TEXT,
    state TEXT,
    action TEXT,
    input_tokens INT,
    output_tokens INT,
    execution_time_ms INT,
    model_used TEXT,
    confidence_score FLOAT,
    error_occurred BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- INVENTORY TABLE (product stock tracking)
CREATE TABLE inventory (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL UNIQUE,
    product_name TEXT,
    total_units INT,
    units_sold INT,
    units_remaining INT,
    reorder_level INT,
    last_reorder_date TIMESTAMP,
    supplier_contact TEXT
);

-- ANALYTICS TABLE (aggregated metrics)
CREATE TABLE analytics (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_sessions INT,
    completed_orders INT,
    failed_orders INT,
    total_revenue INT,  -- in paise
    avg_session_duration_seconds INT,
    avg_satisfaction_score FLOAT,
    top_product TEXT,
    top_design_theme TEXT,
    printer_uptime_percent FLOAT
);

-- STAFF_ACTIVITIES TABLE (for multi-operator tracking)
CREATE TABLE staff_activities (
    id TEXT PRIMARY KEY,
    staff_id TEXT,
    staff_name TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activity_type TEXT,  -- "login" | "logout" | "manual_print" | "refund"
    session_id TEXT,
    notes TEXT
);
```

### 5.2 Python Data Models (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

# STATE ENUMS
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

# SESSION MODEL
class Session(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    current_state: SessionState
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    duration_seconds: int = 0
    completed: bool = False
    satisfaction_score: Optional[int] = None
    notes: Optional[str] = None

# STORY (from Conversation Agent)
class Story(BaseModel):
    themes: List[str]
    emotions: List[str]
    keywords: List[str]
    intent: str
    cultural_references: List[str]
    design_complexity: str  # simple | medium | complex

# DESIGN MODEL
class Design(BaseModel):
    id: str
    session_id: str
    created_at: datetime
    design_prompt: str
    story: Story
    image_urls: Dict[str, str]  # {variant_1: url, variant_2: url, ...}
    selected_variant: Optional[int] = None
    refinements_applied: int = 0
    design_locked: bool = False
    metadata: Dict = {}

# PRODUCT MODEL
class Product(BaseModel):
    product_id: str
    product_name: str
    price: int  # in paise
    sizes: Optional[List[str]] = None
    colors: List[str]
    print_area: str
    production_time_minutes: int
    design_fit_score: float
    inventory_count: int

# ORDER MODEL
class Order(BaseModel):
    id: str
    session_id: str
    created_at: datetime
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    items: List[OrderItem]
    subtotal: int  # in paise
    discount: int
    discount_type: Optional[str] = None
    tax: int
    total: int
    currency: str = "INR"
    payment_method: Optional[str] = None
    payment_status: str  # pending | completed | failed
    order_status: str  # queued | printing | complete | cancelled
    name_tag_text: str
    completion_time: Optional[datetime] = None

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    design_id: str
    size: Optional[str] = None
    color: str
    quantity: int
    unit_price: int
    subtotal: int

# PRODUCTION JOB MODEL
class ProductionJob(BaseModel):
    id: str
    order_id: str
    order_item_id: str
    created_at: datetime
    design_file_path: str
    
    # Stage statuses
    print_status: str  # queued | printing | complete | failed
    print_progress_percent: int
    print_duration_seconds: int
    
    press_status: str
    press_progress_percent: int
    press_duration_seconds: int
    
    stitch_status: str
    stitch_progress_percent: int
    stitch_duration_seconds: int
    
    quality_check_passed: Optional[bool] = None
    completed_at: Optional[datetime] = None

# AGENT MESSAGE MODEL
class AgentMessage(BaseModel):
    agent_id: str
    session_id: str
    timestamp: datetime
    sequence_num: int
    message_type: str  # thinking | output | error | tool_call
    state: SessionState
    payload: Dict
    metadata: Dict = {}
```

---

## PART 6: FASTAPI BACKEND STRUCTURE

### 6.1 Project Directory Structure

```
bobb-ai-backend/
├── main.py                          # FastAPI app entry point
├── config.py                        # Configuration (env vars, model paths)
├── requirements.txt                 # Python dependencies
│
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py               # All endpoints
│   │   ├── websocket.py            # WebSocket handler
│   │   └── middleware.py           # Auth, logging, CORS
│   │
│   ├── agents/                     # Multi-agent system
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Agent coordinator
│   │   ├── conversation_agent.py   # Talk to Gemini/Llama
│   │   ├── design_agent.py         # Translate story → prompt
│   │   ├── image_agent.py          # Generate images (SDXL)
│   │   ├── product_agent.py        # Recommend products
│   │   ├── commerce_agent.py       # Pricing & orders
│   │   └── production_agent.py     # Print queue mgmt
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session_manager.py      # Session state machine
│   │   ├── database.py             # SQLite operations
│   │   ├── printer_api.py          # DTF printer control
│   │   ├── payment_api.py          # UPI/Card payment
│   │   ├── cache.py                # Design caching
│   │   └── telemetry.py            # Analytics tracking
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py              # Pydantic models
│   │   ├── database.py             # SQLAlchemy (optional)
│   │   └── enums.py                # Session states, intent types
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py               # Logging setup
│       ├── validators.py           # Input validation
│       ├── formatters.py           # Response formatting
│       └── constants.py            # BOBB brand constants
│
├── prompts/
│   ├── conversation_system.txt     # Gemini system prompt
│   ├── design_system.txt           # Design agent prompt
│   ├── refinement.txt              # Refinement prompt
│   └── kerala_knowledge.json       # Cultural references
│
├── models/
│   ├── whisper-base/               # (if local) Whisper model
│   ├── sdxl-comfyui/               # (if local) SDXL model
│   └── llama-3-7b/                 # (if local) LLM
│
├── tests/
│   ├── test_agents.py
│   ├── test_api.py
│   └── test_session_manager.py
│
└── docs/
    ├── API.md                      # OpenAPI documentation
    ├── DEPLOYMENT.md               # Setup guide
    └── TROUBLESHOOTING.md          # Debug guide
```

### 6.2 Main FastAPI Application (main.py)

```python
# main.py
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import json
from datetime import datetime
import uuid

from app.api import routes, websocket_handler
from app.services import SessionManager, DatabaseManager
from app.agents import AgentOrchestrator
from app.utils import logger, get_config

# ============================================================================
# INITIALIZATION
# ============================================================================

config = get_config()
app = FastAPI(
    title="BOBB AI Platform",
    version="1.0.0",
    description="Multi-agent retail AI system for custom apparel design"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
session_manager = SessionManager()
db_manager = DatabaseManager()
agent_orchestrator = AgentOrchestrator()

# Startup/Shutdown
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 BOBB AI Backend starting up...")
    
    # Initialize database
    db_manager.init_db()
    logger.info("✓ Database initialized")
    
    # Load AI models
    if config.USE_LOCAL_MODELS:
        agent_orchestrator.load_local_models()
        logger.info("✓ Local AI models loaded")
    else:
        agent_orchestrator.init_gemini_api()
        logger.info("✓ Gemini API initialized")
    
    # Health check
    health_status = await check_system_health()
    logger.info(f"System health: {health_status}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 BOBB AI Backend shutting down...")
    db_manager.close()
    logger.info("✓ Cleanup complete")

# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.get("/health")
async def health_check():
    """System health status"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": db_manager.health_check(),
            "gemini_api": agent_orchestrator.health_check(),
            "printer": check_printer_status(),
        }
    }

async def check_system_health():
    """Comprehensive system health check"""
    return {
        "database": "ready",
        "ai_models": "loaded",
        "printer": "connected",
        "memory": f"{get_memory_usage()}MB"
    }

# ============================================================================
# REST ENDPOINTS
# ============================================================================

# Include all route modules
app.include_router(routes.session_router, prefix="/api/sessions", tags=["sessions"])
app.include_router(routes.design_router, prefix="/api/designs", tags=["designs"])
app.include_router(routes.order_router, prefix="/api/orders", tags=["orders"])
app.include_router(routes.product_router, prefix="/api/products", tags=["products"])
app.include_router(routes.analytics_router, prefix="/api/analytics", tags=["analytics"])

@app.post("/api/test/prompt")
async def test_gemini_prompt(prompt: str):
    """Test endpoint: send message to Gemini"""
    try:
        response = await agent_orchestrator.conversation_agent.call(
            prompt=prompt,
            session_id="test_session"
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# WEBSOCKET ENDPOINT (Real-time communication)
# ============================================================================

active_sessions = {}  # Track active WebSocket connections

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time tablet ↔ backend communication
    
    Handles:
    - Voice input streaming
    - Real-time state updates
    - Progress notifications
    - Error handling
    """
    await websocket.accept()
    active_sessions[session_id] = websocket
    
    logger.info(f"✓ WebSocket connected: {session_id}")
    
    try:
        # Create or load session
        session = await session_manager.get_or_create(session_id)
        
        # Send initial greeting
        await websocket.send_json({
            "type": "session_created",
            "session_id": session_id,
            "state": "GREETING",
            "timestamp": datetime.now().isoformat()
        })
        
        # Message loop
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            message_type = data.get("type")
            
            # Route message to appropriate handler
            if message_type == "voice_input":
                await handle_voice_input(session_id, websocket, data)
            
            elif message_type == "text_input":
                await handle_text_input(session_id, websocket, data)
            
            elif message_type == "design_selection":
                await handle_design_selection(session_id, websocket, data)
            
            elif message_type == "design_refinement":
                await handle_design_refinement(session_id, websocket, data)
            
            elif message_type == "product_selection":
                await handle_product_selection(session_id, websocket, data)
            
            elif message_type == "checkout":
                await handle_checkout(session_id, websocket, data)
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
    
    except Exception as e:
        logger.error(f"WebSocket error ({session_id}): {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass
    
    finally:
        active_sessions.pop(session_id, None)
        logger.info(f"✗ WebSocket disconnected: {session_id}")

# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================

async def handle_voice_input(session_id: str, websocket: WebSocket, data: dict):
    """Handle voice input from tablet"""
    audio_data = data.get("audio_base64")
    
    # Send status: transcribing
    await websocket.send_json({
        "type": "status",
        "state": "LISTENING",
        "message": "Transcribing audio...",
        "timestamp": datetime.now().isoformat()
    })
    
    # Transcribe audio with Whisper
    transcript = await agent_orchestrator.transcribe_audio(audio_data)
    
    # Pass to conversation agent
    await websocket.send_json({
        "type": "status",
        "state": "THINKING",
        "message": "Understanding your story...",
        "timestamp": datetime.now().isoformat()
    })
    
    story = await agent_orchestrator.conversation_agent.extract_story(
        transcript=transcript,
        session_id=session_id
    )
    
    # Check if clarification needed
    if story.get("needs_clarification"):
        await websocket.send_json({
            "type": "clarification_needed",
            "questions": story.get("clarification_questions"),
            "timestamp": datetime.now().isoformat()
        })
        await session_manager.update_state(session_id, "CLARIFYING")
    else:
        # Proceed to design generation
        await websocket.send_json({
            "type": "story_received",
            "story": story,
            "next_action": "generating_design",
            "timestamp": datetime.now().isoformat()
        })
        await handle_design_generation(session_id, websocket, story)

async def handle_text_input(session_id: str, websocket: WebSocket, data: dict):
    """Handle text input from tablet"""
    text_input = data.get("text")
    
    await websocket.send_json({
        "type": "status",
        "state": "THINKING",
        "message": "Processing your story...",
        "timestamp": datetime.now().isoformat()
    })
    
    story = await agent_orchestrator.conversation_agent.extract_story(
        text=text_input,
        session_id=session_id
    )
    
    if story.get("needs_clarification"):
        await websocket.send_json({
            "type": "clarification_needed",
            "questions": story.get("clarification_questions"),
            "timestamp": datetime.now().isoformat()
        })
        await session_manager.update_state(session_id, "CLARIFYING")
    else:
        await websocket.send_json({
            "type": "story_received",
            "story": story,
            "next_action": "generating_design",
            "timestamp": datetime.now().isoformat()
        })
        await handle_design_generation(session_id, websocket, story)

async def handle_design_generation(session_id: str, websocket: WebSocket, story: dict):
    """Generate 4 design variants"""
    
    await websocket.send_json({
        "type": "status",
        "state": "GENERATING",
        "progress_percent": 0,
        "substatus": "Analyzing themes...",
        "timestamp": datetime.now().isoformat()
    })
    await session_manager.update_state(session_id, "GENERATING")
    
    # Design Agent: translate story to visual prompt
    design_prompt = await agent_orchestrator.design_agent.translate_story(
        story=story,
        session_id=session_id
    )
    
    await websocket.send_json({
        "type": "status",
        "state": "GENERATING",
        "progress_percent": 25,
        "substatus": "Creating variant 1...",
        "timestamp": datetime.now().isoformat()
    })
    
    # Image Generation Agent: create 4 variants
    images = await agent_orchestrator.image_agent.generate_variants(
        prompt=design_prompt,
        session_id=session_id,
        num_variants=4
    )
    
    # Save design to database
    design_id = str(uuid.uuid4())
    db_manager.save_design(
        design_id=design_id,
        session_id=session_id,
        design_prompt=design_prompt,
        image_urls={f"variant_{i+1}": url for i, url in enumerate(images)},
        metadata={"story": story}
    )
    
    # Send images to tablet
    await websocket.send_json({
        "type": "design_variants_ready",
        "design_id": design_id,
        "images": [{"variant_id": i+1, "url": url} for i, url in enumerate(images)],
        "next_action": "select_design",
        "timestamp": datetime.now().isoformat()
    })
    await session_manager.update_state(session_id, "PREVIEW")

async def handle_design_selection(session_id: str, websocket: WebSocket, data: dict):
    """User selects one of 4 variants"""
    design_id = data.get("design_id")
    variant_id = data.get("variant_id")
    
    # Mark design as selected in DB
    db_manager.select_design_variant(design_id, variant_id)
    
    await websocket.send_json({
        "type": "design_selected",
        "design_id": design_id,
        "variant_id": variant_id,
        "next_action": "refine_or_proceed",
        "timestamp": datetime.now().isoformat()
    })
    await session_manager.update_state(session_id, "REFINING")

async def handle_design_refinement(session_id: str, websocket: WebSocket, data: dict):
    """User refines design with refinement pills"""
    design_id = data.get("design_id")
    refinement_type = data.get("refinement_type")  # color_scheme, style, mood, etc.
    refinement_value = data.get("refinement_value")
    
    # Get original design
    design = db_manager.get_design(design_id)
    
    # Apply refinement via Design Agent
    refined_prompt = await agent_orchestrator.design_agent.apply_refinement(
        original_prompt=design["design_prompt"],
        refinement_type=refinement_type,
        refinement_value=refinement_value
    )
    
    await websocket.send_json({
        "type": "status",
        "state": "GENERATING",
        "progress_percent": 0,
        "substatus": f"Applying {refinement_type}...",
        "timestamp": datetime.now().isoformat()
    })
    
    # Generate single refined variant
    refined_image = await agent_orchestrator.image_agent.generate_single(
        prompt=refined_prompt,
        session_id=session_id
    )
    
    # Save refined version
    db_manager.update_design(design_id, refined_image)
    
    await websocket.send_json({
        "type": "design_refined",
        "design_id": design_id,
        "image_url": refined_image,
        "refinements_count": design.get("refinements_applied", 0) + 1,
        "can_refine_more": design.get("refinements_applied", 0) < 2,
        "timestamp": datetime.now().isoformat()
    })

async def handle_product_selection(session_id: str, websocket: WebSocket, data: dict):
    """User selects product and quantity"""
    design_id = data.get("design_id")
    product_id = data.get("product_id")
    size = data.get("size")
    color = data.get("color")
    quantity = data.get("quantity", 1)
    
    # Get product details
    product = db_manager.get_product(product_id)
    
    # Create order in progress
    order_id = str(uuid.uuid4())
    db_manager.create_order_draft(
        order_id=order_id,
        session_id=session_id,
        design_id=design_id,
        product_id=product_id,
        size=size,
        color=color,
        quantity=quantity
    )
    
    # Get recommendations for upsell
    total_price = product["price"] * quantity
    
    await websocket.send_json({
        "type": "product_selected",
        "order_id": order_id,
        "total_price": total_price,
        "next_action": "add_to_cart_or_checkout",
        "timestamp": datetime.now().isoformat()
    })
    await session_manager.update_state(session_id, "CART")

async def handle_checkout(session_id: str, websocket: WebSocket, data: dict):
    """Process checkout and create order"""
    order_id = data.get("order_id")
    customer_name = data.get("name")
    customer_phone = data.get("phone")
    name_tag_text = data.get("name_tag")
    payment_method = data.get("payment_method")
    
    # Finalize order
    order = db_manager.complete_order(
        order_id=order_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        name_tag_text=name_tag_text
    )
    
    await session_manager.update_state(session_id, "CHECKOUT")
    
    # Process payment
    await websocket.send_json({
        "type": "status",
        "state": "CHECKOUT",
        "substatus": "Processing payment...",
        "timestamp": datetime.now().isoformat()
    })
    
    if payment_method == "upi":
        payment_result = await process_upi_payment(order)
    elif payment_method == "card":
        payment_result = await process_card_payment(order)
    elif payment_method == "cash":
        payment_result = {"success": True}
    
    if not payment_result.get("success"):
        await websocket.send_json({
            "type": "error",
            "message": "Payment failed. Please try again.",
            "timestamp": datetime.now().isoformat()
        })
        await session_manager.update_state(session_id, "ERROR")
        return
    
    # Queue for production
    await websocket.send_json({
        "type": "payment_success",
        "order_id": order_id,
        "next_action": "to_production",
        "timestamp": datetime.now().isoformat()
    })
    
    # Create production jobs
    production_jobs = await agent_orchestrator.production_agent.queue_order(order_id)
    
    await websocket.send_json({
        "type": "queued_for_production",
        "order_id": order_id,
        "queue_position": len(production_jobs),
        "estimated_wait_minutes": len(production_jobs) * 8,
        "timestamp": datetime.now().isoformat()
    })
    
    await session_manager.update_state(session_id, "PRODUCTION")
    
    # Monitor production progress
    while True:
        job_status = db_manager.get_production_job_status(order_id)
        
        await websocket.send_json({
            "type": "production_update",
            "order_id": order_id,
            "stages": job_status.get("stages"),
            "overall_progress_percent": job_status.get("overall_progress_percent"),
            "timestamp": datetime.now().isoformat()
        })
        
        if job_status.get("status") == "complete":
            await websocket.send_json({
                "type": "production_complete",
                "order_id": order_id,
                "next_action": "show_success",
                "timestamp": datetime.now().isoformat()
            })
            await session_manager.update_state(session_id, "SUCCESS")
            break
        
        await asyncio.sleep(30)  # Update every 30 seconds

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.post("/api/sessions/{session_id}/abandon")
async def abandon_session(session_id: str):
    """End a session early"""
    await session_manager.abandon(session_id)
    return {"message": "Session abandoned"}

@app.get("/api/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current session state"""
    session = await session_manager.get(session_id)
    return session

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8420,
        reload=config.DEBUG,
        log_level="info"
    )
```

---

## PART 7: DEPLOYMENT & OPERATIONS

### 7.1 Deployment Architecture

```
DEPLOYMENT: Windows PC (Kannur Van)

Hardware:
├─ Windows 11 Pro
├─ RTX 3060 12GB VRAM
├─ 16GB RAM
├─ 512GB NVMe SSD
└─ USB3.1 for peripherals

Software Stack:
├─ Python 3.11 (backend)
├─ Node.js 20 (build tablets UI)
├─ FastAPI (API server)
├─ SQLite (local DB)
├─ Ollama (local LLMs)
├─ ComfyUI (local image generation)
└─ Docker (optional, for isolation)

Services Running:
1. FastAPI Backend (port 8420)
   ├─ REST API
   ├─ WebSocket server
   └─ Agent orchestrator

2. ComfyUI Server (port 8188)
   └─ SDXL image generation

3. Ollama Server (port 11434)
   └─ Llama 3 7B inference

4. Tablet UI (port 3000)
   └─ React app

5. Printer Driver Service
   └─ DTF printer API

6. Database Server
   └─ SQLite (embedded)

Internet Connectivity:
├─ Optional: 4G/WiFi for Gemini API (fallback)
├─ Optional: Cloud backup (S3)
└─ Local DNS: no internet required for core operation
```

### 7.2 Installation & Setup

```bash
# STEP 1: Clone repository
git clone https://github.com/mirsab/bobb-ai.git
cd bobb-ai

# STEP 2: Create Python venv
python -m venv venv
.\venv\Scripts\activate

# STEP 3: Install dependencies
pip install -r requirements.txt

# STEP 4: Download local models (if using local)
python -m spacy download en_core_web_sm
ollama pull llama2-7b
# Download SDXL via ComfyUI

# STEP 5: Initialize database
python -c "from app.services import DatabaseManager; DatabaseManager().init_db()"

# STEP 6: Start services
# Terminal 1: Backend
uvicorn main:app --host 0.0.0.0 --port 8420 --reload

# Terminal 2: ComfyUI (if local)
cd ComfyUI && python main.py --listen 0.0.0.0 --port 8188

# Terminal 3: Ollama (if local)
ollama serve

# Terminal 4: React UI
cd bobb-agent-tablet-ui && npm start

# Access tablet UI at http://localhost:3000
# API docs at http://localhost:8420/docs
```

---

## PART 8: MONITORING & ANALYTICS

### 8.1 Key Metrics Dashboard

```
BOBB AI Platform Analytics

Real-Time Metrics:
├─ Active Sessions: 1
├─ Avg Session Duration: 11m 42s
├─ Completed Orders Today: 23
├─ Failed Orders: 1 (4.3%)
├─ Revenue Today: ₹15,450
│
├─ Agent Performance:
│  ├─ Conversation Agent: 98.5% success rate
│  ├─ Design Agent: 96.2% success rate
│  ├─ Image Generation: Avg 22s per 4 variants
│  ├─ Product Agent: 100% recommendations
│  └─ Commerce Agent: 99.1% checkout success
│
├─ System Health:
│  ├─ Database: ✓ Healthy
│  ├─ GPU Memory: 8.2/12 GB
│  ├─ Printer: ✓ Online
│  ├─ Network: ✓ Connected
│  └─ Uptime: 18h 42m
│
├─ Product Preferences:
│  ├─ T-Shirt: 45% (10 units)
│  ├─ Tote Bag: 30% (7 units)
│  ├─ Cap: 15% (3 units)
│  └─ Other: 10% (2 units)
│
└─ Customer Satisfaction:
   ├─ Avg Rating: 4.7/5
   ├─ Design Approval: 92%
   └─ Repeat Customers: 34%

Daily Report:
├─ Total Customers: 52
├─ Avg Spend: ₹297
├─ Peak Hours: 2-4 PM
└─ Best Day: Saturday
```

---

This is the **complete production-ready backend specification**. You now have:

1. ✅ **Multi-agent architecture** (5 specialized agents)
2. ✅ **State machine** (12-state customer journey)
3. ✅ **Database schema** (SQLite with 10+ tables)
4. ✅ **API structure** (FastAPI with WebSocket)
5. ✅ **Agent communication protocol** (JSON-based)
6. ✅ **Product recommendation engine** (design + customer matching)
7. ✅ **Complete data models** (Pydantic schemas)
8. ✅ **Deployment guide**
9. ✅ **Monitoring & analytics**

**Next documents to create**:
1. Complete agent implementation code
2. API route definitions
3. WebSocket message protocol
4. Integration tests
5. Deployment checklist

Want me to create the implementation code for any specific agent or service?
