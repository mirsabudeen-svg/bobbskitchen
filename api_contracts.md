# BOBB AI Platform — API Contracts

**Base URL**: `http://localhost:8420/api/v1`  
**WebSocket**: `ws://localhost:8420/ws/{session_id}`  
**Content-Type**: `application/json`  
**Auth**: None for MVP (internal LAN only)

---

## REST Endpoints

### Sessions

#### `POST /sessions`
Create a new customer session.

**Request**: (empty body)

**Response `201`**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "greeting",
  "created_at": "2026-06-11T10:00:00Z",
  "ws_url": "ws://localhost:8420/ws/550e8400-e29b-41d4-a716-446655440000"
}
```

---

#### `GET /sessions/{session_id}`
Get current session state.

**Response `200`**:
```json
{
  "session_id": "...",
  "state": "preview",
  "created_at": "...",
  "updated_at": "...",
  "customer_name": null,
  "duration_seconds": 47
}
```

**Response `404`**: `{ "detail": "Session not found" }`

---

#### `POST /sessions/{session_id}/abandon`
End a session early (customer walks away).

**Response `200`**: `{ "message": "Session abandoned" }`

---

### Story / Conversation

#### `POST /sessions/{session_id}/story`
Submit customer story text (REST alternative to WebSocket for testing).

**Request**:
```json
{
  "text": "I love the backwaters of Kerala and I grew up in Kannur near the beach."
}
```

**Response `200`**:
```json
{
  "story": {
    "themes": ["backwaters", "beach", "Kannur"],
    "emotions": ["nostalgia", "pride"],
    "keywords": ["backwaters", "beach", "hometown"],
    "cultural_refs": ["Kerala backwaters"],
    "design_complexity": "medium",
    "intent": "DESIGN_REQUEST",
    "needs_clarification": false,
    "clarification_questions": []
  },
  "session_state": "thinking"
}
```

---

### Designs

#### `GET /sessions/{session_id}/designs/latest`
Get the latest design and its variants for a session.

**Response `200`**:
```json
{
  "design_id": "abc123...",
  "story": { ... },
  "variants": [
    {
      "variant_number": 1,
      "style": "illustration",
      "image_url": "/cache/designs/sess_abc/v1.png",
      "generation_time_ms": 5200
    },
    { "variant_number": 2, "style": "geometric", ... },
    { "variant_number": 3, "style": "watercolor", ... },
    { "variant_number": 4, "style": "minimalist", ... }
  ],
  "selected_variant": null,
  "refinements_count": 0,
  "design_locked": false
}
```

**Response `404`**: `{ "detail": "No design found for session" }`

---

#### `POST /sessions/{session_id}/designs/{design_id}/select`
Select a design variant.

**Request**:
```json
{ "variant_number": 2 }
```

**Response `200`**:
```json
{
  "design_id": "abc123...",
  "selected_variant": 2,
  "session_state": "refining"
}
```

---

#### `POST /sessions/{session_id}/designs/{design_id}/refine`
Apply a refinement pill to the selected design. Returns a new refined variant.

**Request**:
```json
{
  "refinement_type": "color_scheme",
  "refinement_value": "Vibrant & bold"
}
```

Valid `refinement_type` values: `color_scheme`, `style`, `mood`, `focus`, `elements`, `size`

**Response `200`**:
```json
{
  "design_id": "abc123...",
  "new_variant": {
    "variant_number": 1,
    "style": "illustration",
    "image_url": "/cache/designs/sess_abc/refined_1.png",
    "is_refined": true
  },
  "refinements_count": 1,
  "refinements_remaining": 2,
  "session_state": "refining"
}
```

**Response `422`**: `{ "detail": "Max 3 refinements reached" }`

---

### Products

#### `GET /products`
Full product catalog.

**Response `200`**:
```json
{
  "products": [
    {
      "product_id": "tshirt_premium",
      "product_name": "Premium T-Shirt",
      "category": "apparel",
      "price_paise": 65000,
      "print_area": "10x12 inches",
      "sizes": ["XS", "S", "M", "L", "XL", "XXL"],
      "colors": ["black", "white", "navy", "burgundy"],
      "production_time_min": 7,
      "units_remaining": 145,
      "is_active": true
    }
  ]
}
```

---

#### `POST /sessions/{session_id}/recommendations`
Get AI product recommendations for the locked design.

**Request**:
```json
{
  "design_id": "abc123..."
}
```

**Response `200`**:
```json
{
  "recommendations": [
    {
      "rank": 1,
      "product_id": "tshirt_premium",
      "product_name": "Premium T-Shirt",
      "score": 0.87,
      "reasons": ["Great for medium-complexity illustration", "Kerala theme prints beautifully on cotton"],
      "price_paise": 65000,
      "print_area": "10x12 inches",
      "production_time_minutes": 7
    },
    { "rank": 2, ... },
    { "rank": 3, ... }
  ],
  "session_state": "product_selection"
}
```

---

### Orders

#### `POST /orders`
Create an order (called from cart/checkout).

**Request**:
```json
{
  "session_id": "550e8400-...",
  "customer_name": "Arjun",
  "customer_phone": "9876543210",
  "name_tag_text": "ARJUN",
  "items": [
    {
      "design_variant_id": "...",
      "product_id": "tshirt_premium",
      "size": "L",
      "color": "black",
      "quantity": 1
    }
  ],
  "payment_method": "cash"
}
```

**Response `201`**:
```json
{
  "order_id": "ord_...",
  "subtotal_paise": 65000,
  "discount_paise": 0,
  "total_paise": 65000,
  "payment_status": "completed",
  "order_status": "queued",
  "session_state": "production"
}
```

**Discount logic** (applied automatically):
- 2 items → 5% off
- 3+ items → 10% off  
- 5+ items → 15% off

---

#### `GET /orders/{order_id}`
Get order details and production status.

**Response `200`**:
```json
{
  "order_id": "...",
  "order_status": "printing",
  "customer_name": "Arjun",
  "total_paise": 65000,
  "items": [ ... ],
  "production": {
    "print_status": "printing",
    "press_status": "queued",
    "stitch_status": "queued",
    "overall_percent": 25,
    "estimated_completion": "2026-06-11T10:18:00Z"
  }
}
```

---

#### `GET /orders/{order_id}/production`
Production-only status (polled by tablet during PRODUCTION state).

**Response `200`**:
```json
{
  "order_id": "...",
  "stages": [
    { "stage": "print",  "status": "printing", "percent": 60, "substatus": "Layer 2 of 3" },
    { "stage": "press",  "status": "queued",   "percent": 0,  "substatus": "Waiting" },
    { "stage": "stitch", "status": "queued",   "percent": 0,  "substatus": "After press" },
    { "stage": "ready",  "status": "queued",   "percent": 0,  "substatus": "Quality check" }
  ],
  "overall_percent": 25,
  "is_complete": false
}
```

---

### Health

#### `GET /health`
System health check.

**Response `200`**:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-11T10:00:00Z",
  "services": {
    "database": "ok",
    "anthropic_api": "ok",
    "image_gen": "ok"
  }
}
```

---

## WebSocket Protocol

Connect: `ws://localhost:8420/ws/{session_id}`

On connect, server immediately sends:
```json
{ "type": "connected", "session_id": "...", "state": "greeting" }
```

---

### Client → Server Messages

#### `text_input`
```json
{
  "type": "text_input",
  "text": "I love the beaches of Kannur and the smell of monsoon rains."
}
```

#### `design_select`
```json
{
  "type": "design_select",
  "design_id": "abc123",
  "variant_number": 2
}
```

#### `design_refine`
```json
{
  "type": "design_refine",
  "design_id": "abc123",
  "refinement_type": "style",
  "refinement_value": "Minimalist"
}
```

#### `design_accept`
```json
{
  "type": "design_accept",
  "design_id": "abc123"
}
```
Locks the design and triggers product recommendation.

#### `regenerate`
```json
{
  "type": "regenerate",
  "design_id": "abc123"
}
```
Requests all 4 new variants (resets back to THINKING).

#### `product_select`
```json
{
  "type": "product_select",
  "product_id": "tshirt_premium",
  "size": "L",
  "color": "black",
  "quantity": 1
}
```

#### `checkout_submit`
```json
{
  "type": "checkout_submit",
  "customer_name": "Arjun",
  "customer_phone": "9876543210",
  "name_tag_text": "ARJUN",
  "payment_method": "cash"
}
```

#### `ping`
```json
{ "type": "ping" }
```

---

### Server → Client Messages

#### `state_change`
```json
{
  "type": "state_change",
  "state": "generating",
  "prev_state": "thinking",
  "timestamp": "2026-06-11T10:00:00Z"
}
```

#### `progress`
```json
{
  "type": "progress",
  "percent": 50,
  "substatus": "Creating variant 2 of 4...",
  "timestamp": "2026-06-11T10:00:05Z"
}
```

#### `story_extracted`
```json
{
  "type": "story_extracted",
  "story": {
    "themes": ["beach", "Kannur"],
    "emotions": ["nostalgia", "pride"],
    "keywords": ["waves", "palm trees"],
    "cultural_refs": ["Kerala backwaters"],
    "design_complexity": "medium"
  }
}
```

#### `clarification_needed`
```json
{
  "type": "clarification_needed",
  "questions": [
    "What specific colours or mood are you thinking of?",
    "Is this for yourself or as a gift?"
  ]
}
```

#### `design_variants_ready`
```json
{
  "type": "design_variants_ready",
  "design_id": "abc123",
  "variants": [
    { "variant_number": 1, "style": "illustration", "image_url": "/cache/designs/sess_x/v1.png" },
    { "variant_number": 2, "style": "geometric",    "image_url": "/cache/designs/sess_x/v2.png" },
    { "variant_number": 3, "style": "watercolor",   "image_url": "/cache/designs/sess_x/v3.png" },
    { "variant_number": 4, "style": "minimalist",   "image_url": "/cache/designs/sess_x/v4.png" }
  ]
}
```

#### `design_refined`
```json
{
  "type": "design_refined",
  "design_id": "abc123",
  "variant": {
    "variant_number": 1,
    "style": "illustration",
    "image_url": "/cache/designs/sess_x/refined_1.png",
    "is_refined": true
  },
  "refinements_count": 1,
  "refinements_remaining": 2
}
```

#### `product_recommendations`
```json
{
  "type": "product_recommendations",
  "recommendations": [
    {
      "rank": 1,
      "product_id": "tshirt_premium",
      "product_name": "Premium T-Shirt",
      "score": 0.87,
      "reasons": ["Perfect for medium illustration", "Most popular product"],
      "price_paise": 65000,
      "print_area": "10x12 inches",
      "production_time_minutes": 7,
      "available_sizes": ["XS","S","M","L","XL","XXL"],
      "available_colors": ["black","white","navy","burgundy"]
    }
  ]
}
```

#### `order_created`
```json
{
  "type": "order_created",
  "order_id": "ord_xyz",
  "total_paise": 65000,
  "queue_position": 2,
  "estimated_wait_minutes": 10
}
```

#### `production_update`
```json
{
  "type": "production_update",
  "order_id": "ord_xyz",
  "stages": [
    { "stage": "print",  "status": "printing", "percent": 60 },
    { "stage": "press",  "status": "queued",   "percent": 0 },
    { "stage": "stitch", "status": "queued",   "percent": 0 },
    { "stage": "ready",  "status": "queued",   "percent": 0 }
  ],
  "overall_percent": 25
}
```

#### `production_complete`
```json
{
  "type": "production_complete",
  "order_id": "ord_xyz",
  "customer_name": "Arjun"
}
```

#### `error`
```json
{
  "type": "error",
  "code": "IMAGE_GEN_FAILED",
  "message": "Could not generate designs. Please try again.",
  "recoverable": true,
  "suggested_action": "retry"
}
```

Error codes:
| code | recoverable | description |
|---|---|---|
| `IMAGE_GEN_FAILED` | true | fal.ai request failed |
| `IMAGE_GEN_TIMEOUT` | true | Generation took > 60s |
| `AGENT_FAILED` | true | Claude API error |
| `INVALID_STATE` | false | Unexpected state transition |
| `ORDER_FAILED` | true | Order creation failed |
| `SYSTEM_ERROR` | false | Unrecoverable crash |

#### `pong`
```json
{ "type": "pong", "timestamp": "..." }
```

---

## Static Files

Design images are served at:
```
GET /cache/designs/{session_id}/{filename}
```
Via FastAPI `StaticFiles` mount on `/cache`.

---

## Error Response Format (REST)

All REST errors follow FastAPI default:
```json
{
  "detail": "Human-readable error message"
}
```

HTTP status codes used:
| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Bad request / validation error |
| 404 | Resource not found |
| 422 | Business rule violation (e.g. max refinements) |
| 500 | Internal server error |
