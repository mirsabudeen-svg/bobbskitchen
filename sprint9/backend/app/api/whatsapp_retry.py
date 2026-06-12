"""
backend/app/api/whatsapp_retry.py

POST /api/v1/orders/{id}/whatsapp-retry

Allows staff to manually retry a failed WhatsApp artwork delivery.
Add this route to orders.py (or as a separate router included in main.py).

Use cases:
  - Twilio was temporarily down when the order was marked ready
  - Customer's phone number had a typo that was corrected
  - Intermittent network failure on the van's 4G

Guards:
  - Order must be in 'ready' or 'collected' state
  - Artwork (image_url) must exist on the order item
  - Rate-limited to 3 retries per order (stored in whatsapp_logs count)
  - Always creates a new WhatsAppLog row regardless of outcome
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.order import Order
from app.models.whatsapp_log import WhatsAppLog
from app.services.whatsapp import send_artwork
from app.api.orders import _get_order_or_404, _get_artwork_for_order, _order_dict_full

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

MAX_RETRIES = 3


@router.post("/{order_id}/whatsapp-retry")
async def retry_whatsapp(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually retry WhatsApp artwork delivery for an order.
    Returns the updated order dict with whatsapp_sent reflecting the retry outcome.
    """
    order = await _get_order_or_404(order_id, db)

    # Guard: only retry on ready or collected orders
    if order.order_status not in ("ready", "collected"):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "whatsapp_retry_not_allowed",
                "reason": f"Order is '{order.order_status}' — retry only allowed on ready/collected orders",
            },
        )

    # Guard: must have a phone number
    if not order.customer_phone:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_customer_phone"},
        )

    # Guard: must have artwork
    image_url = await _get_artwork_for_order(order)
    if not image_url:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_artwork_on_order"},
        )

    # Guard: rate limit retries
    retry_count_result = await db.execute(
        select(func.count(WhatsAppLog.id)).where(WhatsAppLog.order_id == order_id)
    )
    existing_attempts = retry_count_result.scalar_one()
    if existing_attempts >= MAX_RETRIES:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "whatsapp_retry_limit_reached",
                "attempts": existing_attempts,
                "max": MAX_RETRIES,
            },
        )

    # Fire the send
    result = await send_artwork(
        customer_phone=order.customer_phone,
        customer_name=order.customer_name or "",
        short_ref=order.short_ref,
        image_url=image_url,
        order_id=str(order.id),
    )

    # Log the attempt
    log_entry = WhatsAppLog(
        order_id=order.id,
        short_ref=order.short_ref,
        customer_phone=order.customer_phone,
        customer_name=order.customer_name or "",
        language=result.language,
        image_url=image_url,
        success=result.success,
        message_sid=result.message_sid,
        error=result.error,
    )
    db.add(log_entry)

    # Update order flags on success
    if result.success:
        order.whatsapp_sent = True
        order.whatsapp_log_id = log_entry.id

    await db.commit()
    await db.refresh(order)

    return {
        "order": _order_dict_full(order),
        "whatsapp": {
            "success":     result.success,
            "message_sid": result.message_sid,
            "error":       result.error,
            "language":    result.language,
            "attempt":     existing_attempts + 1,
        },
    }
