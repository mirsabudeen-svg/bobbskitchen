"""
backend/app/api/orders_whatsapp_patch.py

Diff-style patch showing exactly what changes in orders.py for Sprint 9.
Do NOT replace orders.py — apply these targeted changes to the existing file.

Changes:
  1. Import the whatsapp service
  2. Add _get_artwork_for_order() helper
  3. In update_order_status() — fire WhatsApp on "ready" transition
  4. Persist the WhatsAppLog row and update orders.whatsapp_sent
  5. Surface whatsapp_sent in _order_dict_full()
"""

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 1 — Add to imports at the top of orders.py
# ─────────────────────────────────────────────────────────────────────────────

# ADD these imports alongside the existing ones:
#
# from app.services.whatsapp import send_artwork, WhatsAppDeliveryResult
# from app.models.whatsapp_log import WhatsAppLog


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 2 — New helper function (add anywhere above update_order_status)
# ─────────────────────────────────────────────────────────────────────────────

async def _get_artwork_for_order(order) -> str | None:
    """
    Return the image_url for the first order item that has one.
    Sprint 9 ships one design per order; if multiple items exist,
    the first non-null image_url wins.
    Returns None if no artwork is available (should not happen in production
    due to Sprint 6.2 Fix 4, but handled defensively).
    """
    for item in order.items:
        if item.image_url:
            return item.image_url
    return None


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 3 — Inside update_order_status(), after the status is committed
#
# FIND this block (already in orders.py from Sprint 7):
#
#     order.order_status = body.status
#     if body.staff_notes:
#         order.staff_notes = body.staff_notes
#     if body.status == "reprinting":
#         order.reprint_count = (order.reprint_count or 0) + 1
#
#     await db.commit()
#     await db.refresh(order)
#
#     # Push to WebSocket so staff queue updates live
#     await broadcast_order_update(order)
#
#     return OrderResponse(order=_order_dict_full(order))
#
# REPLACE with the block below:
# ─────────────────────────────────────────────────────────────────────────────

async def update_order_status_with_whatsapp(order, body, db, broadcast_order_update):
    """
    Drop-in replacement for the mutation + commit block in update_order_status().
    Adds WhatsApp artwork delivery on the pending→ready transition.

    NOTE: This function is shown as a standalone block for clarity.
    In practice, merge the WhatsApp section into your existing update_order_status().
    """
    from app.services.whatsapp import send_artwork
    from app.models.whatsapp_log import WhatsAppLog

    order.order_status = body.status
    if body.staff_notes:
        order.staff_notes = body.staff_notes
    if body.status == "reprinting":
        order.reprint_count = (order.reprint_count or 0) + 1

    await db.commit()
    await db.refresh(order)

    # ── WhatsApp artwork delivery ────────────────────────────────────────────
    # Fires only on transition to "ready".
    # Runs AFTER commit so the order row is stable before we attempt delivery.
    # Never blocks the HTTP response — delivery result is fire-and-log.
    if body.status == "ready" and order.customer_phone:
        image_url = await _get_artwork_for_order(order)

        if image_url:
            result = await send_artwork(
                customer_phone=order.customer_phone,
                customer_name=order.customer_name or "",
                short_ref=order.short_ref,
                image_url=image_url,
                order_id=str(order.id),
            )

            # Persist the delivery attempt
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

            # Update the order's whatsapp_sent flag and log reference
            order.whatsapp_sent = result.success
            order.whatsapp_log_id = log_entry.id if result.success else None

            await db.commit()
            await db.refresh(order)

        else:
            # Defensive: no artwork found — log and continue
            import logging
            logging.getLogger(__name__).warning(
                "Order %s marked ready but has no artwork — WhatsApp not sent",
                order.short_ref,
            )
    # ── End WhatsApp section ──────────────────────────────────────────────────

    await broadcast_order_update(order)
    return order


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 4 — In _order_dict_full(), add whatsapp_sent to the returned dict
#
# FIND:
#     "reprint_count": order.reprint_count or 0,
#
# ADD after it:
#     "whatsapp_sent": order.whatsapp_sent,
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 5 — New endpoint: GET /orders/{id}/whatsapp-log
# Lets staff see delivery status for a specific order.
# Add this route to orders.py.
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

# (router and get_db already exist in orders.py — shown here for context)
# router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

async def get_whatsapp_log(
    order_id: uuid.UUID,
    db: AsyncSession,
):
    """
    GET /api/v1/orders/{id}/whatsapp-log
    Returns the WhatsApp delivery history for an order.
    Used by the staff dashboard to show delivery status.
    """
    from app.models.whatsapp_log import WhatsAppLog

    result = await db.execute(
        select(WhatsAppLog)
        .where(WhatsAppLog.order_id == order_id)
        .order_by(WhatsAppLog.attempted_at.desc())
    )
    logs = result.scalars().all()

    return {
        "order_id": str(order_id),
        "logs": [
            {
                "id":             str(log.id),
                "success":        log.success,
                "language":       log.language,
                "message_sid":    log.message_sid,
                "error":          log.error,
                "attempted_at":   log.attempted_at.isoformat(),
                "customer_phone": log.customer_phone[-4:].rjust(len(log.customer_phone), "*"),
            }
            for log in logs
        ],
    }
