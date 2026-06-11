"""
BOBB Kitchen — FastAPI + WebSocket Server
Connects Samsung Tab S9 Ultra (React UI) to the agent system.

Endpoints:
  POST /session/create          — WhatsApp bot creates session after QR scan
  POST /session/verify-qr       — Tablet verifies customer's WhatsApp QR
  WS   /ws/{session_id}         — Live agent conversation (tablet ↔ agents)
  POST /payment/webhook         — UPI payment gateway callback
  GET  /order/{order_id}/status — Poll order / print job status
  POST /order/{order_id}/ready  — Staff marks order ready → triggers WhatsApp
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional

import hmac
import hashlib

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from bobb_agents import (
    create_session,
    get_session,
    run_turn,
    confirm_order_and_notify,
    _sessions,
    DB_PATH,
)
import sqlite3


# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────

app = FastAPI(title="BOBB Kitchen API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# HMAC secret for signing session QR codes
QR_SECRET = b"bobb-kitchen-qr-secret-change-in-production"

# Active WebSocket connections: session_id → WebSocket
_connections: dict[str, WebSocket] = {}

# Conversation histories: session_id → list[dict]
_histories: dict[str, list] = {}


# ─────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    customer_name: str
    phone_number:  str
    language:      str = "en"      # "en" or "ml"


class CreateSessionResponse(BaseModel):
    session_id:     str
    qr_token:       str            # signed token — becomes QR code content
    customer_name:  str
    expires_at:     str


class VerifyQRRequest(BaseModel):
    qr_token: str


class VerifyQRResponse(BaseModel):
    valid:         bool
    session_id:    str
    customer_name: str
    language:      str


class PaymentWebhookPayload(BaseModel):
    payment_id:     str
    order_id:       str
    status:         str            # "paid" | "failed"
    amount:         float
    gateway_sig:    str            # HMAC signature from gateway


class OrderStatusResponse(BaseModel):
    order_id:       str
    status:         str
    print_jobs:     list
    estimated_mins: int


class MarkReadyRequest(BaseModel):
    order_id:    str
    staff_pin:   str = ""          # optional staff auth
    photo_url:   str = ""          # optional product photo URL


# ─────────────────────────────────────────────
# SESSION ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/session/create", response_model=CreateSessionResponse)
async def create_customer_session(req: CreateSessionRequest):
    """
    Called by WhatsApp bot when customer sends the trigger message.
    Creates session, generates signed QR token, returns to bot for sending.
    """
    session_id = f"BB-{uuid.uuid4().hex[:8].upper()}"

    create_session(
        session_id=session_id,
        customer_name=req.customer_name,
        phone_number=req.phone_number,
        language=req.language,
    )

    # Sign the QR token with HMAC so tablet can verify it
    payload    = f"{session_id}:{req.phone_number}"
    signature  = hmac.new(QR_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:16]
    qr_token   = f"{payload}:{signature}"

    # 2-hour expiry
    expires_ts = int(datetime.now().timestamp()) + 7200
    expires_at = datetime.fromtimestamp(expires_ts).isoformat()

    return CreateSessionResponse(
        session_id=session_id,
        qr_token=qr_token,
        customer_name=req.customer_name,
        expires_at=expires_at,
    )


@app.post("/session/verify-qr", response_model=VerifyQRResponse)
async def verify_qr_token(req: VerifyQRRequest):
    """
    Tablet camera scans the WhatsApp QR → sends token here to validate.
    Returns session info if valid, 401 if expired or tampered.
    """
    try:
        parts      = req.qr_token.split(":")
        session_id = parts[0]
        phone      = parts[1]
        given_sig  = parts[2]
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid QR format")

    # Verify HMAC signature
    payload       = f"{session_id}:{phone}"
    expected_sig  = hmac.new(QR_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:16]

    if not hmac.compare_digest(given_sig, expected_sig):
        raise HTTPException(status_code=401, detail="QR token invalid or tampered")

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if session.status not in ("active",):
        raise HTTPException(status_code=410, detail=f"Session is {session.status}")

    return VerifyQRResponse(
        valid=True,
        session_id=session.session_id,
        customer_name=session.customer_name,
        language=session.language,
    )


# ─────────────────────────────────────────────
# WEBSOCKET  —  live agent conversation
# ─────────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_conversation(ws: WebSocket, session_id: str):
    """
    Main conversation channel between the tablet React UI and the agent.

    Message protocol (JSON):
      → client sends: {"type": "message", "text": "...", "session_id": "..."}
      ← server sends: {"type": "response",  "text": "...", "agent": "..."}
      ← server sends: {"type": "tool_call", "tool": "generate_image", "status": "running"}
      ← server sends: {"type": "images",    "images": [...]}
      ← server sends: {"type": "error",     "message": "..."}
      ← server sends: {"type": "payment",   "qr": "...", "payment_id": "..."}
      ← server sends: {"type": "complete",  "order_id": "...", "eta_mins": N}
    """
    session = get_session(session_id)
    if session is None:
        await ws.close(code=4004, reason="Session not found")
        return

    await ws.accept()
    _connections[session_id] = ws

    if session_id not in _histories:
        _histories[session_id] = []

        # Send initial greeting from orchestrator
        greeting_result = await run_turn(
            session_id=session_id,
            customer_message=(
                f"[SYSTEM] New customer session started. "
                f"Customer name: {session.customer_name}. "
                f"Language: {session.language}. "
                f"Greet the customer warmly and ask what they'd like to create."
            ),
            conversation_history=[],
        )
        _histories[session_id] = greeting_result["messages"]

        await ws.send_json({
            "type":  "response",
            "text":  greeting_result["response"],
            "agent": greeting_result["agent_name"],
        })

    try:
        while True:
            raw = await ws.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type")

            # ── Customer sends a text message ──
            if msg_type == "message":
                customer_text = msg.get("text", "").strip()
                if not customer_text:
                    continue

                # Signal to UI that we're processing
                await ws.send_json({"type": "thinking"})

                result = await run_turn(
                    session_id=session_id,
                    customer_message=customer_text,
                    conversation_history=_histories[session_id],
                )

                _histories[session_id] = result["messages"]

                await ws.send_json({
                    "type":  "response",
                    "text":  result["response"],
                    "agent": result["agent_name"],
                })

            # ── Customer selected an image (0-3) ──
            elif msg_type == "select_image":
                product  = msg.get("product_type", "")
                img_idx  = msg.get("image_index", 0)

                selection_msg = (
                    f"[CUSTOMER SELECTED] The customer chose design option "
                    f"{img_idx + 1} (index {img_idx}) for their {product}. "
                    f"Ask if they'd like any changes or if they're happy to proceed."
                )

                result = await run_turn(
                    session_id=session_id,
                    customer_message=selection_msg,
                    conversation_history=_histories[session_id],
                )
                _histories[session_id] = result["messages"]

                await ws.send_json({
                    "type":  "response",
                    "text":  result["response"],
                    "agent": result["agent_name"],
                })

            # ── Customer approved the mockup ──
            elif msg_type == "approve_design":
                product = msg.get("product_type", "")

                approval_msg = (
                    f"[CUSTOMER APPROVED] The customer approved the {product} design. "
                    f"Save the design and add it to their cart. "
                    f"Then check if there are more products to design or proceed to checkout."
                )

                result = await run_turn(
                    session_id=session_id,
                    customer_message=approval_msg,
                    conversation_history=_histories[session_id],
                )
                _histories[session_id] = result["messages"]

                await ws.send_json({
                    "type":  "response",
                    "text":  result["response"],
                    "agent": result["agent_name"],
                })

            # ── Customer wants to change language mid-session ──
            elif msg_type == "set_language":
                lang = msg.get("language", "en")
                if session_id in _sessions:
                    _sessions[session_id].language = lang
                await ws.send_json({"type": "language_set", "language": lang})

            # ── Ping / keepalive ──
            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        _connections.pop(session_id, None)


# ─────────────────────────────────────────────
# PAYMENT ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/payment/webhook")
async def payment_webhook(payload: PaymentWebhookPayload, request: Request):
    """
    Called by UPI payment gateway when payment status changes.
    On success: confirms order, queues printing, sends WhatsApp.
    """
    # In production: verify gateway signature here
    # gateway_payload = await request.body()
    # expected = hmac.new(GATEWAY_SECRET, gateway_payload, hashlib.sha256).hexdigest()
    # if not hmac.compare_digest(expected, payload.gateway_sig):
    #     raise HTTPException(status_code=401, detail="Invalid gateway signature")

    if payload.status != "paid":
        # Update order status to failed
        _update_order_status(payload.order_id, "failed")
        return {"received": True}

    # Find session for this order
    session_id = _get_session_for_order(payload.order_id)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Order not found")

    # Confirm order: sends WhatsApp + queues print jobs
    result = await confirm_order_and_notify(
        session_id=session_id,
        payment_id=payload.order_id,
    )

    # Push update to active WebSocket if tablet is still connected
    if session_id in _connections:
        ws = _connections[session_id]
        try:
            await ws.send_json({
                "type":      "payment_confirmed",
                "order_id":  payload.order_id,
                "amount":    payload.amount,
                "eta_mins":  result.get("estimated_time_mins", 20),
            })
        except Exception:
            pass  # WebSocket may have closed after payment

    return {"received": True, "order_id": payload.order_id}


@app.get("/payment/{payment_id}/status")
async def get_payment_status(payment_id: str):
    """Poll endpoint — tablet checks every 3 seconds after showing UPI QR."""
    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute(
        "SELECT status, total_amount FROM orders WHERE order_id=?",
        (payment_id,),
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {"payment_id": payment_id, "status": row[0], "amount": row[1]}


# ─────────────────────────────────────────────
# ORDER STATUS
# ─────────────────────────────────────────────

@app.get("/order/{order_id}/status", response_model=OrderStatusResponse)
async def get_order_status(order_id: str):
    """Check order and print job status — used by staff dashboard."""
    conn = sqlite3.connect(DB_PATH)

    order = conn.execute(
        "SELECT status FROM orders WHERE order_id=?", (order_id,)
    ).fetchone()

    if order is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    jobs = conn.execute(
        "SELECT job_id, product_type, status FROM print_jobs WHERE session_id IN "
        "(SELECT session_id FROM orders WHERE order_id=?)",
        (order_id,),
    ).fetchall()
    conn.close()

    print_jobs = [
        {"job_id": j[0], "product_type": j[1], "status": j[2]} for j in jobs
    ]

    pending_jobs    = sum(1 for j in print_jobs if j["status"] in ("queued", "printing"))
    estimated_mins  = pending_jobs * 15

    return OrderStatusResponse(
        order_id=order_id,
        status=order[0],
        print_jobs=print_jobs,
        estimated_mins=estimated_mins,
    )


@app.post("/order/{order_id}/ready")
async def mark_order_ready(order_id: str, req: MarkReadyRequest):
    """
    Staff presses 'Ready' on production dashboard.
    Sends WhatsApp pickup notification to customer.
    Optional: include photo URL for product photo message.
    """
    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute(
        "SELECT session_id FROM orders WHERE order_id=?", (order_id,)
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")

    session_id = row[0]
    session    = get_session(session_id)

    if session:
        # Send WhatsApp "ready" message
        # In production: call Twilio API
        whatsapp_msg = (
            f"🎉 Ready to collect!\n"
            f"Show order #{order_id} at the BOBB counter."
        )
        if req.photo_url:
            whatsapp_msg += f"\nHere's a preview: {req.photo_url}"

        # twilio_client.messages.create(
        #     from_="whatsapp:+14155238886",
        #     to=f"whatsapp:{session.phone_number}",
        #     body=whatsapp_msg,
        # )
        print(f"[WhatsApp → {session.phone_number}] {whatsapp_msg}")

    _update_order_status(order_id, "ready")

    return {"success": True, "order_id": order_id, "status": "ready"}


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    """Tablet and monitoring dashboard use this to check server is up."""
    active_sessions = len([s for s in _sessions.values() if s.status == "active"])
    active_ws       = len(_connections)

    return {
        "status":           "ok",
        "timestamp":        datetime.now().isoformat(),
        "active_sessions":  active_sessions,
        "active_ws":        active_ws,
        "version":          "1.0.0",
    }


# ─────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────

def _update_order_status(order_id: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE orders SET status=? WHERE order_id=?", (status, order_id)
    )
    conn.commit()
    conn.close()


def _get_session_for_order(order_id: str) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute(
        "SELECT session_id FROM orders WHERE order_id=?", (order_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "bobb_server:app",
        host="0.0.0.0",
        port=8420,
        reload=False,
        log_level="info",
    )
