# BOBB AI — Order Workflow Operational Review

**Reviewer:** Retail Operations (kiosk / on-demand print, DTF)
**Date:** 2026-06-12
**Scope:** CartScreen.tsx, CheckoutScreen.tsx, ProductionScreen.tsx, SuccessScreen.tsx, backend `api/orders.py`, `store/session.ts`, `types/index.ts`
**Context:** Roaming retail van, Kerala. 40–60 orders/day, 10–14 min journey, one customer-facing tablet, DTF printing on-site, payment collected manually at the counter.

---

## Executive Summary

The customer-facing order flow is polished, but the operational back half does not exist. Once `POST /orders` writes a row with `order_status="pending"` and `payment_status="pending"`, **nothing in the system ever reads, lists, updates, or notifies anyone about that order again** — there is no queue view, no staff dashboard, no status transition endpoint, and no notification of any kind. The print operator literally cannot discover that an order exists without querying PostgreSQL by hand. On day one with real customers, staff will fall back to shouting names across the van and writing orders on paper within the first hour, and the database will fill with permanently-"pending" orders that cannot be reconciled against cash taken.

---

## Priority Matrix

| # | Finding | Severity | Operational Impact |
|---|---------|----------|--------------------|
| 1 | No staff order queue / dashboard — orders are write-only | **Critical** | Operator cannot see what to print; system is decorative |
| 2 | No order status lifecycle — `pending` is terminal | **Critical** | No way to mark printing/ready/collected; no reconciliation |
| 3 | No print spec delivered to staff (image file, size, colour, placement) | **Critical** | Operator cannot produce the garment from the order record |
| 4 | Payment recorded nowhere — `payment_status` stuck at `pending`, `payment_method` always `null` | **Critical** | Cash taken at counter is invisible; end-of-day count impossible |
| 5 | No idempotency on order creation | **High** | Duplicate orders → duplicate prints → wasted blanks and film |
| 6 | Order reference is lost on screen reset / tablet refresh | **High** | Customer cannot prove ownership at pickup |
| 7 | Garment size silently taken from AI `mockup_hint`, never confirmed by customer | **High** | Wrong-size garments printed; DTF prints are non-returnable |
| 8 | Prices trusted from the client (`unit_price_paise` in request body) | **High** | Stale/tampered pricing accepted; revenue leakage |
| 9 | ProductionScreen is fake — timer-free animation with a "skip to completion (demo)" button | **High** | Customer told "printing" before any print job exists; demo button ships to prod |
| 10 | No pickup verification or handover record | **High** | Wrong-garment handover; disputes unresolvable |
| 11 | Last-6 UUID ref: fine daily, weak over time, no staff lookup by it | **Medium** | Staff can't find an order from "#A1B2C3" without SQL |
| 12 | No failure/reprint workflow (printer jam, bad press, customer dispute) | **Medium** | Every misprint becomes an off-system improvisation |
| 13 | Quantity limits disagree (UI max 5, API max 10) | **Low** | Confusing but not harmful |
| 14 | "Hand-stitched name tag" promised with no production-time accounting | **Low** | Tag forgotten or blows the 10–14 min journey budget |

---

## Production Workflow

### [CRITICAL] Orders are write-only — there is no way for staff to know an order exists

**Current behaviour:** `backend/app/api/orders.py` exposes exactly two routes: `POST /orders` and `GET /orders/{order_id}`. There is no `GET /orders` list, no filter by status or date, no WebSocket/event emitted on creation, no print job enqueued. The order row is created and the function returns to the customer's tablet.

**Operational risk:** The print operator at the back of the van has zero signal. On a Saturday with 50 customers, the only person who knows an order was placed is the customer staring at a "Printing your design" animation. Real-day failure: customer waits 12 minutes, walks to the counter, and the operator says "what order?" Staff will immediately revert to leaning over the customer's shoulder and photographing the screen — at which point the order system is theatre.

**Recommended fix:** Add `GET /orders?status=pending|printing|ready&date=today` plus a minimal staff page (even an unstyled table on a second device) showing: short ref, customer name, product, size, colour, qty, design thumbnail, name-tag text, created-at, payment status. Push new orders to it via the existing WebSocket infrastructure.

### [CRITICAL] No print spec — staff cannot produce the garment from the order

**Current behaviour:** `OrderItem` stores `design_variant_id` (a UUID FK), `product_name`, `size`, `color`, `quantity`. The actual print asset is `variant.image_url`, which is never surfaced anywhere staff-facing; the validated `variant` objects in `create_order` are discarded after validation. No print placement, no print dimensions (the `print_area_width_in/height_in` on the recommendation never reach the order), no DTF-ready file.

**Operational risk:** To print one garment the operator must: query the order item in SQL, join to `design_variants`, open the cached image URL, guess placement and size against the product's print area, and hope the 1024×1024 PNG is the variant the customer actually selected. Each order becomes a 5-minute forensic exercise — at 40–60/day that alone destroys throughput.

**Recommended fix:** Denormalise onto the order item at creation time: `image_url`, print width/height inches, placement (from `mockup_hint.placement`). Show all of it in the staff queue with the thumbnail. The data already exists in `validated_variants` and the recommendation — it is one extra line per field in `create_order`.

---

## Queue & Sequencing

### [CRITICAL] No status lifecycle — `order_status` is set to `"pending"` and never updated by anything

**Current behaviour:** `create_order` hardcodes `order_status="pending"`. No endpoint, job, or UI anywhere in the reviewed code mutates it. There is no PATCH route, no "mark printing", no "mark ready", no "mark collected".

**Operational risk:** With 3 orders in flight, the operator cannot record which is on the press, which is heat-curing, and which is folded and waiting. Sequence is FIFO-by-memory. When a customer skips ahead ("mine was the elephant one"), nothing stops the operator printing out of order and a later customer's 14-minute promise quietly becomes 30. End of day: every order in the DB says `pending` forever — you cannot even count how many garments you actually produced.

**Recommended fix:** Add `PATCH /orders/{id}/status` with an enforced transition chain `pending → printing → ready → collected` (plus `failed`, `reprinting`, `refunded`). One-tap buttons in the staff queue. Sort the queue by `created_at` and visibly number positions so skipping ahead is a deliberate act, not a default.

---

## Order Identity

### [MEDIUM] Last-6-of-UUID reference: collision risk is acceptable daily, but it's unusable for staff lookup

**Current behaviour:** `ProductionScreen.tsx` and `SuccessScreen.tsx` compute `orderId.slice(-6).toUpperCase()` client-side. The backend has no concept of this short ref — `GET /orders/{order_id}` requires the full UUID.

**Operational risk:** Collision math: 16^6 ≈ 16.7M combinations; at 60 orders/day the within-day collision probability is ~C(60,2)/16.7M ≈ 0.01% — fine for a single day. But there is no day-scoping, so over a season (~10k orders) cumulative collision odds reach a few percent, and more importantly **staff cannot look anything up by it**: a customer says "#A1B2C3" and the operator has no endpoint, no search box, nothing. The reference is purely cosmetic. Also note the slice takes the last 6 chars of the *string*, which for a UUID is the trailing hex of the node field — fine, but two orders from the same backend run can share suffixes more often than pure randomness if UUID1 were ever used; you're on uuid4 today, just don't change that silently.

**Recommended fix:** Generate the short ref server-side at creation (e.g. daily sequence `B-014` or date-scoped 6-char code), store it on the order with a unique-per-day constraint, return it in `_order_dict`, and add `GET /orders/lookup?ref=` for staff. A daily counter (`#1…#60`) is honestly better for a van: it doubles as queue position.

---

## Customer Pickup

### [HIGH] The order reference evaporates; nothing verifies pickup

**Current behaviour:** The ref is shown on-screen only. `store/session.ts` `partialize` persists only `sessionId`, `currentState`, `storyText` — **not `orderId`** — so a tablet refresh mid-PRODUCTION loses the reference entirely. SuccessScreen's "Start New Story" calls `reset()`, wiping it for the next customer. The WhatsApp number is optional and nothing is ever sent to it ("We'll send your design preview before printing" is an unfulfilled promise in CheckoutScreen copy). There is no handover step: no "collected" status, no signature, no name check.

**Operational risk:** Customer browses the stalls for 15 minutes, comes back, has forgotten #A1B2C3, and the screen has been reset by the next customer. Proof of ownership is now "it's the one with the boat." With multiple similar Kerala-themed prints on the table, wrong-garment handovers will happen weekly — and since `payment_status` is also untracked, someone can plausibly collect a garment they never paid for. There is no record of who took what.

**Recommended fix:** (1) Persist `orderId` in the zustand partialize. (2) Print or hand-write a paper ticket with ref + name + total at the counter (lowest-tech, most reliable). (3) Staff verifies name + ref at handover and taps "collected", which also requires `payment_status="paid"` first. (4) If a phone was given, actually send the ref via WhatsApp — or remove the promise from the checkout copy.

---

## Failure Recovery

### [HIGH] ProductionScreen is a fiction; no link between the screen and any real print job

**Current behaviour:** `ProductionScreen.tsx` shows a `LoadingPulse` with the product's nominal production minutes and a low-opacity **"Skip to completion (demo)"** button that anyone can tap to jump to SUCCESS. No print job exists; success is whatever the customer's finger says.

**Operational risk:** The customer is told "Printing your design" the instant the order row commits — before staff even know about it. The demo button shipping to production means bored customers (or kids) tap it, see "Order Complete!", and queue for pickup of a garment that hasn't started. Per CLAUDE.md the printer is manual in MVP — fine — but then this screen should say "Order received, please pay at the counter", not "Printing".

**Recommended fix:** Remove the demo button behind a `DEBUG` flag. Reword the screen to reflect reality ("Order #X received — pay at the counter; we'll call your name when it's ready"). Drive the SUCCESS transition from a staff "ready" status update over the existing WebSocket, not from a customer tap.

### [MEDIUM] No reprint / failure workflow at all

**Current behaviour:** The only failure handling in `orders.py` is pre-order (`variant_not_printable` for fallback variants). Post-creation there is no `failed` status, no reprint flag, no refund/dispute field, no notes column surfaced.

**Operational risk:** DTF reality: film jams, adhesive powder clumps, presses scorch, a gradient bands badly on a navy tee. Today each of these means the operator silently prints again with no record — inventory counts drift (blanks consumed ≠ orders fulfilled), and if a customer disputes a print there is nowhere to record the resolution. At 40–60/day expect 2–5 misprints daily; that's 10%+ of stock unaccounted for.

**Recommended fix:** Add `failed`/`reprinting` statuses plus a `staff_notes` text field and a `reprint_of_order_item_id` link. Even a free-text note ("jam, reprinted 14:32") makes end-of-day stock reconciliation possible.

---

## Duplicate Prevention

### [HIGH] No idempotency anywhere in order creation

**Current behaviour:** `handleConfirm` sets `loading` to disable the button — the only guard. The backend `POST /orders` has no idempotency key, no uniqueness constraint per session, no duplicate detection. If the request succeeds server-side but the response is lost on the van's flaky 4G/Wi-Fi, the catch block shows "Could not place order. Please try again." — explicitly inviting the customer to create a second identical order. A session can also legitimately re-enter CHECKOUT (Back button) and order again.

**Operational risk:** This is the canonical kiosk failure: spotty connectivity + retry prompt = duplicate orders. With no queue dedup view either (Finding 1), the operator prints both. Two garments, one customer, one payment — and you only discover it when stock counts are off.

**Recommended fix:** Frontend generates a UUID idempotency key per checkout attempt and sends it; backend stores it with a unique constraint and returns the existing order on conflict (200, not 409). Additionally, flag in the staff queue when two pending orders share a `session_id`. On the press side, the `printing` status transition (Finding on lifecycle) is itself the double-print guard — an order already past `pending` can't be picked up twice.

### [HIGH] Client-supplied prices and product names are trusted verbatim

**Current behaviour:** `create_order` validates the design variant against the DB but takes `unit_price_paise`, `product_id`, and `product_name` straight from the request body and sums them into `subtotal_paise`. The only check is `unit_price_paise > 0`.

**Operational risk:** Less about malicious tablets (it's a kiosk) and more about staleness: the tablet's cached recommendation can carry yesterday's price after a price change, and the order will persist the wrong total that staff then collect in cash. `1 paise` orders are also technically valid. Price disputes at the counter with no authoritative source are a daily friction.

**Recommended fix:** Look up the product server-side (the `PRODUCT_REGISTRY` exists per CLAUDE.md) and compute price from the catalog; reject or warn on mismatch.

---

## Staff Tools

### [CRITICAL] Payment is structurally unrecordable

**Current behaviour:** `payment_method=None  # collected at counter`, `payment_status="pending"` — and with no update endpoint, both are permanent. The checkout screen tells the customer "Payment collected at the counter", but the counter has no tool to record that collection.

**Operational risk:** End of day, the cashbox holds ₹X and the database says every one of 55 orders is unpaid. You cannot detect a skipped payment, a wrong amount taken, or theft. A garment can be collected without paying because nothing ties handover to payment. For a cash-heavy roaming van this is the single biggest shrinkage hole in the design. (No payment *gateway* is correctly out of MVP scope per CLAUDE.md — but recording that cash/UPI was taken is not a gateway, it's a status flag.)

**Recommended fix:** `PATCH /orders/{id}/payment` setting `payment_status="paid"` and `payment_method ∈ {cash, upi}`, tappable from the staff queue. Block `collected` status until `paid`. A 30-second end-of-day report (`sum(total_paise) where payment_status='paid' and date=today`) then reconciles the cashbox.

### [HIGH] Size is decided by the AI, not the customer

**Current behaviour:** `CheckoutScreen.tsx` line 61: `size: product.mockup_hint?.suggested_size ?? null`. The customer is never shown or asked their garment size anywhere in Cart or Checkout; `MockupHint.suggested_size` is an AI inference (`inferred_demographics` is even a scoring input) and may be `null`.

**Operational risk:** DTF-printed garments cannot be restocked. Every wrong-size order is a total loss of blank + film + press time, plus an unhappy customer who waited 14 minutes. At kiosk volumes expect multiple per day. `null` sizes are worse: the operator must interrupt and find the customer mid-flow to ask.

**Recommended fix:** Add a size selector (S/M/L/XL/XXL) to CartScreen next to quantity, defaulting to the AI suggestion but requiring explicit confirmation. Validate non-null server-side for sized products.

### [LOW] Quantity limits disagree between UI and API

**Current behaviour:** CartScreen caps the picker at 5 (`disabled={quantity >= 5}`); the zustand `setQuantity` clamps to 10; the API validator allows 1–10.

**Operational risk:** Minor — but a resumed/manipulated session can submit qty 6–10 that the UI never intended, and a 10-unit order silently consumes ~an hour of press time inside a 14-minute promise.

**Recommended fix:** Pick one limit (5 is right for a van) and enforce it in the Pydantic validator.

### [LOW] Hand-stitched name tag has no production accounting

**Current behaviour:** Cart promises "hand-stitched inside the garment"; the tag text is stored on the order but appears in no staff view (because there is no staff view) and adds nothing to the displayed production time.

**Operational risk:** Either the tag is forgotten (broken promise, discovered at pickup or at home) or stitching adds 5–10 unbudgeted minutes per order. At volume, an easy daily promise-breaker.

**Recommended fix:** Surface `name_tag_text` prominently in the staff queue with its own checkbox before "ready"; add its time to the customer-facing estimate, or drop the feature from MVP.

---

## Closing Prioritisation

### Before the first paying customer (blockers)
1. **Staff queue view + `GET /orders?status=&date=`** (Finding 1) — without it, run the day on paper, honestly.
2. **Status lifecycle endpoint** `pending → printing → ready → collected` + `failed` (Finding 2).
3. **Payment recording** (`paid`, cash/UPI) and gate handover on it (Finding "payment").
4. **Print spec on the order**: image URL, size, colour, qty, name-tag, placement visible to the operator (Finding 3).
5. **Customer-confirmed size selector** (Finding "size").
6. **Remove/flag the "Skip to completion (demo)" button** and reword ProductionScreen (Finding 9).

### Week 1
7. Idempotency key on `POST /orders` + same-session duplicate flag in the queue (Finding 5).
8. Server-side short ref (daily counter) + staff lookup by ref; persist `orderId` in the store; paper ticket at the counter (Findings 6, 11).
9. Server-side price calculation from the product registry (Finding 8).
10. Reprint/failure statuses + `staff_notes` (Finding 12).

### Defer (Phase 2)
- WhatsApp order-ready notification (or remove the promise from checkout copy now — one-line change, do that immediately).
- Drive SUCCESS screen from staff "ready" event over WebSocket.
- Quantity-limit unification and name-tag time budgeting.
- End-of-day reconciliation report (trivial once statuses exist).

The honest framing: the customer journey is Sprint-7 complete; operations is Sprint 0. Until the six blockers land, this system can take orders but cannot fulfil, charge for, or hand them over — and on a 60-customer Saturday, that gap is the whole business.
