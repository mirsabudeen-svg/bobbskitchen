"""Order endpoints — Sprint 7 full implementation."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.db import DesignVariantRow, Inventory, Order, OrderItem, Session
from app.models.whatsapp_log import WhatsAppLog
from app.services.analytics import (
    track_order_collected,
    track_order_paid,
    track_order_placed,
    track_order_ready,
    track_reprint,
    track_whatsapp_result,
)
from app.services.pricing import get_catalog_price
from app.services.whatsapp import WhatsAppDeliveryResult, send_artwork

router = APIRouter(prefix="/orders", tags=["orders"])

# ---------------------------------------------------------------------------
# Status lifecycle
# ---------------------------------------------------------------------------

STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending":    {"printing", "failed"},
    "printing":   {"ready", "failed", "reprinting"},
    "reprinting": {"ready", "failed"},
    "ready":      {"collected"},
    "failed":     {"reprinting"},
    "collected":  set(),
}

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class OrderItemRequest(BaseModel):
    design_variant_id: str
    product_id: str
    product_name: str
    size: str
    color: str = "natural"
    quantity: int = 1
    unit_price_paise: int
    name_tag_text: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def qty_range(cls, v: int) -> int:
        if not (1 <= v <= 5):
            raise ValueError("quantity must be between 1 and 5")
        return v

    @field_validator("unit_price_paise")
    @classmethod
    def price_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("unit_price_paise must be positive")
        return v

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: str) -> str:
        valid = {"S", "M", "L", "XL", "XXL"}
        if v.upper() not in valid:
            raise ValueError(f"size must be one of {valid}")
        return v.upper()

    @field_validator("name_tag_text")
    @classmethod
    def tag_length(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) > 15:
            raise ValueError("name_tag_text must be 15 characters or fewer")
        return v.strip() if v else None


class OrderCreateRequest(BaseModel):
    session_id: str
    customer_name: str
    customer_phone: Optional[str] = None
    items: list[OrderItemRequest]
    payment_method: Optional[str] = None

    @field_validator("customer_name")
    @classmethod
    def name_nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("customer_name is required")
        return v


class StatusUpdateRequest(BaseModel):
    status: str
    staff_notes: Optional[str] = None


class PaymentUpdateRequest(BaseModel):
    payment_method: str
    amount_paise: Optional[int] = None

    @field_validator("payment_method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v not in {"cash", "upi", "card"}:
            raise ValueError("payment_method must be cash, upi, or card")
        return v


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _item_dict(item: OrderItem) -> dict:
    return {
        "id": str(item.id),
        "design_variant_id": str(item.design_variant_id),
        "product_id": item.product_id,
        "product_name": item.product_name,
        "size": item.size,
        "color": item.color,
        "quantity": item.quantity,
        "unit_price_paise": item.unit_price_paise,
        "subtotal_paise": item.subtotal_paise,
        "name_tag_text": item.name_tag_text,
        "image_url": item.image_url,
        "print_width_in": float(item.print_width_in) if item.print_width_in else None,
        "print_height_in": float(item.print_height_in) if item.print_height_in else None,
        "print_placement": item.print_placement,
    }


def _order_dict(order: Order, items: list[OrderItem] | None = None) -> dict:
    d: dict = {
        "order_id": str(order.id),
        "short_ref": order.short_ref,
        "session_id": str(order.session_id),
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "order_status": order.order_status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "subtotal_paise": order.subtotal_paise,
        "total_paise": order.total_paise,
        "total_rupees": round(order.total_paise / 100, 2),
        "currency": order.currency,
        "staff_notes": order.staff_notes,
        "reprint_count": order.reprint_count,
        "whatsapp_sent": order.whatsapp_sent,
        "paid_at": (
            order.paid_at.isoformat().replace("+00:00", "Z") if order.paid_at else None
        ),
        "created_at": order.created_at.isoformat().replace("+00:00", "Z"),
    }
    if items is not None:
        d["items"] = [_item_dict(i) for i in items]
    return d


async def _get_order_or_404(order_id: str, db: AsyncSession) -> Order:
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid order_id format") from None
    order = await db.get(Order, oid)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def _get_items(order_id: uuid.UUID, db: AsyncSession) -> list[OrderItem]:
    result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    return list(result.scalars().all())


async def _generate_short_ref(db: AsyncSession) -> tuple[str, int]:
    today = date.today()
    result = await db.execute(
        select(func.count(Order.id)).where(func.date(Order.created_at) == today)
    )
    count = result.scalar_one() or 0
    seq = count + 1
    return f"B-{seq:03d}", seq


async def _get_artwork_for_order(order: Order) -> str | None:
    """Return the image_url for the first order item that has one."""
    for item in order.items:
        if item.image_url:
            return item.image_url
    return None


async def _broadcast(order: Order, items: list[OrderItem]) -> None:
    from app.api.ws import broadcast_order_update
    try:
        await broadcast_order_update(_order_dict(order, items))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Endpoints — note: fixed routes before parameterised ones
# ---------------------------------------------------------------------------


@router.get("/lookup")
async def lookup_order_by_ref(
    ref: str = Query(..., min_length=2, max_length=10),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """GET /api/v1/orders/lookup?ref=B-014 — staff search by short ref."""
    result = await db.execute(
        select(Order).where(Order.short_ref == ref.upper().strip())
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail={"error": "order_not_found"})
    items = await _get_items(order.id, db)
    return {"order": _order_dict(order, items)}


@router.get("/reconciliation")
async def daily_reconciliation(
    date_filter: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """GET /api/v1/orders/reconciliation?date=YYYY-MM-DD — end-of-day totals."""
    result = await db.execute(
        select(Order).where(func.date(Order.created_at) == date_filter)
    )
    orders = list(result.scalars().all())

    paid = [o for o in orders if o.payment_status == "paid"]
    unpaid = [o for o in orders if o.payment_status != "paid"]
    cash = [o for o in paid if o.payment_method == "cash"]
    upi = [o for o in paid if o.payment_method == "upi"]
    failed = [o for o in orders if o.order_status == "failed"]
    reprinted = [o for o in orders if (o.reprint_count or 0) > 0]

    return {
        "date": date_filter.isoformat(),
        "total_orders": len(orders),
        "paid_orders": len(paid),
        "unpaid_orders": len(unpaid),
        "cash_total_paise": sum(o.amount_paid_paise or 0 for o in cash),
        "upi_total_paise": sum(o.amount_paid_paise or 0 for o in upi),
        "grand_total_paise": sum(o.amount_paid_paise or 0 for o in paid),
        "failed_orders": len(failed),
        "reprinted_orders": len(reprinted),
    }


@router.get("")
async def list_orders(
    status: Optional[str] = Query(None),
    date_filter: Optional[date] = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """GET /api/v1/orders — staff queue, defaults to today."""
    valid_statuses = {
        "pending", "printing", "ready", "collected", "failed", "reprinting"
    }
    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=422, detail=f"status must be one of {sorted(valid_statuses)}"
        )

    query = select(Order).order_by(Order.created_at.asc())
    if status:
        query = query.where(Order.order_status == status)
    target_date = date_filter or date.today()
    query = query.where(func.date(Order.created_at) == target_date)

    result = await db.execute(query)
    orders = list(result.scalars().all())

    orders_out = []
    for order in orders:
        items = await _get_items(order.id, db)
        orders_out.append(_order_dict(order, items))

    return {
        "orders": orders_out,
        "count": len(orders_out),
        "date": target_date.isoformat(),
    }


@router.post("", status_code=201)
async def create_order(
    body: OrderCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create an order — validates session, prices, and variant printability."""
    # --- idempotency dedup ---
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        existing = await db.execute(
            select(Order).where(Order.idempotency_key == idempotency_key)
        )
        existing_order = existing.scalar_one_or_none()
        if existing_order:
            items = await _get_items(existing_order.id, db)
            return _order_dict(existing_order, items)

    # --- validate session ---
    try:
        sid = uuid.UUID(body.session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session_id format") from None
    session_row = await db.get(Session, sid)
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not body.items:
        raise HTTPException(status_code=422, detail="Order must have at least one item")

    # --- validate variants and prices ---
    validated_variants: dict[str, DesignVariantRow] = {}
    for item in body.items:
        try:
            vid = uuid.UUID(item.design_variant_id)
        except ValueError:
            raise HTTPException(  # noqa: B904
                status_code=422,
                detail=f"Invalid design_variant_id: {item.design_variant_id}",
            )
        variant = await db.get(DesignVariantRow, vid)
        if variant is None:
            raise HTTPException(
                status_code=404,
                detail=f"Design variant {item.design_variant_id} not found",
            )
        if variant.is_fallback or variant.image_url is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "variant_not_printable",
                    "message": "Cannot place an order with a failed design variant.",
                    "suggested_action": "regenerate",
                },
            )
        validated_variants[item.design_variant_id] = variant

        # server-side price check
        try:
            catalog_price = await get_catalog_price(item.product_id, db)
            if item.unit_price_paise != catalog_price:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "price_mismatch",
                        "client_price_paise": item.unit_price_paise,
                        "catalog_price_paise": catalog_price,
                        "message": "Price has changed. Please confirm the updated price.",
                    },
                )
        except ValueError:
            pass  # unknown product — accept client price (test/demo products)

    # --- inventory lookup for print dimensions ---
    inventory_cache: dict[str, Inventory] = {}
    for item in body.items:
        if item.product_id not in inventory_cache:
            inv = await db.get(Inventory, item.product_id)
            if inv:
                inventory_cache[item.product_id] = inv

    # --- totals ---
    subtotal_paise = sum(i.unit_price_paise * i.quantity for i in body.items)

    # --- short ref ---
    short_ref, daily_seq = await _generate_short_ref(db)

    # --- create order row ---
    order = Order(
        session_id=sid,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        subtotal_paise=subtotal_paise,
        tax_paise=0,
        total_paise=subtotal_paise,
        payment_status="pending",
        order_status="pending",
        short_ref=short_ref,
        daily_sequence=daily_seq,
        idempotency_key=idempotency_key,
    )
    db.add(order)
    await db.flush()

    # --- create items with denormalised print spec ---
    created_items: list[OrderItem] = []
    for item in body.items:
        variant = validated_variants[item.design_variant_id]
        inv = inventory_cache.get(item.product_id)

        print_w: float | None = None
        print_h: float | None = None
        if inv and inv.print_area:
            try:
                parts = inv.print_area.lower().replace("in", "").strip().split("x")
                print_w = float(parts[0].strip())
                print_h = float(parts[1].strip())
            except Exception:
                pass

        oi = OrderItem(
            order_id=order.id,
            design_variant_id=uuid.UUID(item.design_variant_id),
            product_id=item.product_id,
            product_name=item.product_name,
            size=item.size,
            color=item.color,
            quantity=item.quantity,
            unit_price_paise=item.unit_price_paise,
            subtotal_paise=item.unit_price_paise * item.quantity,
            name_tag_text=item.name_tag_text,
            image_url=variant.image_url,
            print_width_in=print_w,
            print_height_in=print_h,
            print_placement="center-chest",
        )
        db.add(oi)
        created_items.append(oi)

    session_row.customer_name = body.customer_name
    session_row.customer_phone = body.customer_phone
    session_row.current_state = "production"

    await db.commit()
    await db.refresh(order)
    for oi in created_items:
        await db.refresh(oi)

    story_to_order_ms = 0
    if session_row.story_started_at:
        story_to_order_ms = int(
            (datetime.now(UTC) - session_row.story_started_at).total_seconds() * 1000
        )
    for oi in created_items:
        asyncio.create_task(
            track_order_placed(
                db,
                str(order.session_id),
                str(order.id),
                order.short_ref,
                oi.product_id,
                oi.size,
                oi.color,
                oi.quantity,
                order.total_paise,
                story_to_order_ms,
            )
        )

    await _broadcast(order, created_items)
    return _order_dict(order, created_items)


@router.get("/{order_id}/whatsapp-log")
async def get_whatsapp_log(order_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """GET /api/v1/orders/{id}/whatsapp-log — WhatsApp delivery history for an order."""
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid order_id format") from None
    result = await db.execute(
        select(WhatsAppLog)
        .where(WhatsAppLog.order_id == oid)
        .order_by(WhatsAppLog.attempted_at.desc())
    )
    logs = result.scalars().all()
    return {
        "order_id": order_id,
        "logs": [
            {
                "id": str(log.id),
                "success": log.success,
                "language": log.language,
                "message_sid": log.message_sid,
                "error": log.error,
                "attempted_at": log.attempted_at.isoformat(),
                "customer_phone": log.customer_phone[-4:].rjust(len(log.customer_phone), "*"),
            }
            for log in logs
        ],
    }


@router.get("/{order_id}")
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    order = await _get_order_or_404(order_id, db)
    items = await _get_items(order.id, db)
    return _order_dict(order, items)


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: str,
    body: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await _get_order_or_404(order_id, db)

    allowed = STATUS_TRANSITIONS.get(order.order_status, set())
    if body.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "invalid_status_transition",
                "current": order.order_status,
                "requested": body.status,
                "allowed": sorted(allowed),
            },
        )

    if body.status == "collected" and order.payment_status != "paid":
        raise HTTPException(
            status_code=409,
            detail={"error": "payment_required_before_collection"},
        )

    order.order_status = body.status
    if body.staff_notes:
        order.staff_notes = body.staff_notes
    if body.status == "reprinting":
        order.reprint_count = (order.reprint_count or 0) + 1

    await db.commit()
    await db.refresh(order)

    if body.status == "ready":
        asyncio.create_task(track_order_ready(db, str(order.id), order.short_ref, order.created_at))
    elif body.status == "collected":
        asyncio.create_task(track_order_collected(db, str(order.id), order.short_ref))
    elif body.status == "reprinting":
        items_for_reprint = await _get_items(order.id, db)
        for item in items_for_reprint:
            asyncio.create_task(
                track_reprint(
                    db, str(order.id), order.short_ref,
                    color=item.color, product_id=item.product_id,
                    staff_notes=body.staff_notes,
                )
            )

    # ── WhatsApp artwork delivery (fire-and-log, never blocks response) ──────
    if body.status == "ready" and order.customer_phone:
        image_url = await _get_artwork_for_order(order)
        if image_url:
            result: WhatsAppDeliveryResult = await send_artwork(
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
            order.whatsapp_sent = result.success
            order.whatsapp_log_id = log_entry.id if result.success else None
            await db.commit()
            await db.refresh(order)
            asyncio.create_task(
                track_whatsapp_result(
                    db, str(order.id), order.short_ref,
                    success=result.success, language=result.language, error=result.error,
                )
            )
    # ── End WhatsApp section ─────────────────────────────────────────────────

    items = await _get_items(order.id, db)
    await _broadcast(order, items)
    return _order_dict(order, items)


@router.patch("/{order_id}/payment")
async def record_payment(
    order_id: str,
    body: PaymentUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await _get_order_or_404(order_id, db)

    if order.payment_status == "paid":
        items = await _get_items(order.id, db)
        return _order_dict(order, items)

    if order.order_status == "collected":
        raise HTTPException(
            status_code=409,
            detail={"error": "cannot_record_payment_after_collection"},
        )

    order.payment_status = "paid"
    order.payment_method = body.payment_method
    order.amount_paid_paise = body.amount_paise or order.total_paise
    order.paid_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(order)

    asyncio.create_task(
        track_order_paid(
            db, str(order.id), order.short_ref,
            body.payment_method, order.amount_paid_paise or order.total_paise,
        )
    )

    items = await _get_items(order.id, db)
    await _broadcast(order, items)
    return _order_dict(order, items)
