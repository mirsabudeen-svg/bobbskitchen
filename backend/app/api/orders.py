"""Order endpoints — Sprint 7 implementation."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.db import DesignVariantRow, Order, OrderItem, Session

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderItemRequest(BaseModel):
    design_variant_id: str
    product_id: str
    product_name: str
    size: str | None = None
    color: str = "natural"
    quantity: int = 1
    unit_price_paise: int

    @field_validator("quantity")
    @classmethod
    def qty_range(cls, v: int) -> int:
        if not (1 <= v <= 10):
            raise ValueError("quantity must be between 1 and 10")
        return v

    @field_validator("unit_price_paise")
    @classmethod
    def price_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("unit_price_paise must be positive")
        return v


class OrderCreateRequest(BaseModel):
    session_id: str
    customer_name: str
    customer_phone: str | None = None
    name_tag_text: str | None = None
    items: list[OrderItemRequest]
    payment_method: str | None = None  # set at counter; pending in MVP

    @field_validator("customer_name")
    @classmethod
    def name_nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("customer_name is required")
        return v

    @field_validator("name_tag_text")
    @classmethod
    def tag_length(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) > 15:
            raise ValueError("name_tag_text must be 15 characters or fewer")
        return v.strip() if v else None


def _order_dict(order: Order) -> dict:
    return {
        "order_id": str(order.id),
        "session_id": str(order.session_id),
        "order_status": order.order_status,
        "payment_status": order.payment_status,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "name_tag_text": order.name_tag_text,
        "subtotal_paise": order.subtotal_paise,
        "tax_paise": order.tax_paise,
        "total_paise": order.total_paise,
        "total_rupees": round(order.total_paise / 100, 2),
        "currency": order.currency,
        "created_at": order.created_at.isoformat().replace("+00:00", "Z"),
    }


@router.post("", status_code=201)
async def create_order(
    body: OrderCreateRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Create an order from the checkout screen and persist it to the DB."""
    # --- validate session ---
    try:
        sid = uuid.UUID(body.session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session_id format") from None

    session_row = await db.get(Session, sid)
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not body.items:
        raise HTTPException(status_code=422, detail="Order must contain at least one item")

    # --- validate each variant is printable ---
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

    # --- calculate totals (no tax / discount in MVP) ---
    subtotal_paise = sum(i.unit_price_paise * i.quantity for i in body.items)
    total_paise = subtotal_paise

    # --- create order row ---
    order = Order(
        session_id=sid,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        name_tag_text=body.name_tag_text,
        subtotal_paise=subtotal_paise,
        tax_paise=0,
        total_paise=total_paise,
        payment_method=None,   # collected at counter
        payment_status="pending",
        order_status="pending",
    )
    db.add(order)
    await db.flush()  # populate order.id before FK references

    # --- create order items ---
    for item in body.items:
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
        )
        db.add(oi)

    # --- update session ---
    session_row.customer_name = body.customer_name
    session_row.customer_phone = body.customer_phone
    session_row.current_state = "production"

    await db.commit()
    await db.refresh(order)

    return _order_dict(order)


@router.get("/{order_id}")
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Retrieve order details including all line items."""
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid order_id format") from None

    order = await db.get(Order, oid)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    result = await db.execute(select(OrderItem).where(OrderItem.order_id == oid))
    items = result.scalars().all()

    return {
        **_order_dict(order),
        "items": [
            {
                "order_item_id": str(i.id),
                "design_variant_id": str(i.design_variant_id),
                "product_id": i.product_id,
                "product_name": i.product_name,
                "size": i.size,
                "color": i.color,
                "quantity": i.quantity,
                "unit_price_paise": i.unit_price_paise,
                "subtotal_paise": i.subtotal_paise,
            }
            for i in items
        ],
    }
