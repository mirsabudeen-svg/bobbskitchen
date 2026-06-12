"""Server-side pricing — validates client-supplied prices against the catalog.

Prices are looked up from the inventory table. If a client submits a stale
or tampered price, the endpoint returns 409 with the current catalog price
so the frontend can re-confirm.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Inventory


async def get_catalog_price(product_id: str, db: AsyncSession) -> int:
    """Return the price in paise for a product. Raises ValueError if unknown."""
    result = await db.execute(
        select(Inventory.price_paise).where(
            Inventory.product_id == product_id,
            Inventory.is_active.is_(True),
        )
    )
    price = result.scalar_one_or_none()
    if price is None:
        raise ValueError(f"Product not found in catalog: {product_id}")
    return price


async def validate_client_price(
    product_id: str,
    client_price_paise: int,
    db: AsyncSession,
) -> tuple[bool, int]:
    """Return (matches, catalog_price). Raises ValueError if product unknown."""
    catalog = await get_catalog_price(product_id, db)
    return client_price_paise == catalog, catalog
