"""POST /api/v1/orders/{id}/whatsapp-retry — manual retry for failed WhatsApp sends."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.db.base import get_db
from app.models.db import Order
from app.models.whatsapp_log import WhatsAppLog
from app.services.whatsapp import send_artwork
from app.api.orders import _get_order_or_404, _get_artwork_for_order, _order_dict

router = APIRouter(prefix="/orders", tags=["orders"])

MAX_RETRIES = 3


@router.post("/{order_id}/whatsapp-retry")
async def retry_whatsapp(
    order_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually retry WhatsApp artwork delivery. Rate-limited to 3 attempts per order."""
    order = await _get_order_or_404(order_id, db)

    if order.order_status not in ("ready", "collected"):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "whatsapp_retry_not_allowed",
                "reason": (
                    f"Order is '{order.order_status}' — "
                    "retry only allowed on ready/collected orders"
                ),
            },
        )

    if not order.customer_phone:
        raise HTTPException(status_code=422, detail={"error": "no_customer_phone"})

    image_url = await _get_artwork_for_order(order)
    if not image_url:
        raise HTTPException(status_code=422, detail={"error": "no_artwork_on_order"})

    retry_count_result = await db.execute(
        select(func.count(WhatsAppLog.id)).where(
            WhatsAppLog.order_id == uuid.UUID(str(order.id))
        )
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

    result = await send_artwork(
        customer_phone=order.customer_phone,
        customer_name=order.customer_name or "",
        short_ref=order.short_ref,
        image_url=image_url,
        order_id=str(order.id),
    )

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

    if result.success:
        order.whatsapp_sent = True
        order.whatsapp_log_id = log_entry.id

    await db.commit()
    await db.refresh(order)

    from app.api.orders import _get_items
    items = await _get_items(order.id, db)

    return {
        "order": _order_dict(order, items),
        "whatsapp": {
            "success": result.success,
            "message_sid": result.message_sid,
            "error": result.error,
            "language": result.language,
            "attempt": existing_attempts + 1,
        },
    }
