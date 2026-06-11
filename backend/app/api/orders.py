"""Order endpoints — Sprint 0 stubs."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderItemRequest(BaseModel):
    design_variant_id: str
    product_id: str
    size: str | None = None
    color: str
    quantity: int = 1


class OrderCreateRequest(BaseModel):
    session_id: str
    customer_name: str
    customer_phone: str | None = None
    name_tag_text: str | None = None
    items: list[OrderItemRequest]
    payment_method: str


@router.post("", status_code=501)
async def create_order(
    body: OrderCreateRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Create an order. Sprint 8 implements (with discount logic)."""
    return {"detail": "Not implemented — Sprint 8"}


@router.get("/{order_id}", status_code=501)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Get order details + production status. Sprint 8 implements."""
    return {"detail": "Not implemented — Sprint 8"}
