"""Sprint 7 acceptance tests — Order creation and retrieval."""

from __future__ import annotations

import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.db.base import create_engine as _create_engine, create_session_factory
from app.models.db import Design, DesignVariantRow, Session as SessionRow
from app.providers.mock import MockProvider

_PRODUCT_ID = "tshirt_standard"
_UNIT_PRICE = 59900  # paise


async def _with_fresh_db(fn):
    settings = get_settings()
    engine = _create_engine(settings)
    factory: async_sessionmaker = create_session_factory(engine)
    try:
        return await fn(factory)
    finally:
        await engine.dispose()


async def _seed_printable(factory: async_sessionmaker) -> tuple[str, str]:
    async with factory() as db:
        sess = SessionRow(current_state="preview")
        db.add(sess)
        await db.flush()
        design = Design(
            session_id=sess.id,
            pipeline_run_id=uuid.uuid4(),
            design_strategy={},
            primary_kerala_theme="backwaters",
            primary_emotion="nostalgia",
            key_symbols=[],
        )
        db.add(design)
        await db.flush()
        variant = DesignVariantRow(
            design_id=design.id,
            variant_number=1,
            style="illustration",
            image_url="https://example.com/test.png",
            provider_name="mock",
            model_used="mock",
            generation_time_ms=100,
            success=True,
            is_fallback=False,
        )
        db.add(variant)
        await db.commit()
        return str(sess.id), str(variant.id)


async def _seed_fallback(factory: async_sessionmaker) -> tuple[str, str]:
    async with factory() as db:
        sess = SessionRow(current_state="preview")
        db.add(sess)
        await db.flush()
        design = Design(
            session_id=sess.id,
            pipeline_run_id=uuid.uuid4(),
            design_strategy={},
            primary_kerala_theme=None,
            primary_emotion=None,
            key_symbols=[],
        )
        db.add(design)
        await db.flush()
        variant = DesignVariantRow(
            design_id=design.id,
            variant_number=1,
            style="illustration",
            image_url=None,
            provider_name="mock",
            model_used="mock",
            generation_time_ms=0,
            success=False,
            is_fallback=True,
        )
        db.add(variant)
        await db.commit()
        return str(sess.id), str(variant.id)


def _seed(coro_fn) -> tuple[str, str]:
    async def _run():
        return await _with_fresh_db(coro_fn)
    return asyncio.run(_run())


def _inject(client: TestClient) -> None:
    from app.main import app
    app.state.llm_provider = MockProvider()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_order_success(client: TestClient):
    _inject(client)
    session_id, variant_id = _seed(_seed_printable)

    resp = client.post(
        "/api/v1/orders",
        json={
            "session_id": session_id,
            "customer_name": "Arjun Menon",
            "customer_phone": "+919876543210",
            "items": [
                {
                    "design_variant_id": variant_id,
                    "product_id": _PRODUCT_ID,
                    "product_name": "Standard T-Shirt",
                    "size": "M",
                    "color": "natural",
                    "quantity": 1,
                    "unit_price_paise": _UNIT_PRICE,
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["customer_name"] == "Arjun Menon"
    assert data["payment_status"] == "pending"
    assert data["order_status"] == "pending"
    assert data["total_paise"] == _UNIT_PRICE
    assert "order_id" in data


def test_create_order_transitions_session_to_production(client: TestClient):
    _inject(client)
    session_id, variant_id = _seed(_seed_printable)

    resp = client.post(
        "/api/v1/orders",
        json={
            "session_id": session_id,
            "customer_name": "Priya Nair",
            "items": [
                {
                    "design_variant_id": variant_id,
                    "product_id": _PRODUCT_ID,
                    "product_name": "Standard T-Shirt",
                    "color": "natural",
                    "quantity": 1,
                    "unit_price_paise": _UNIT_PRICE,
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text

    async def _check() -> str:
        async def fn(factory: async_sessionmaker) -> str:
            async with factory() as db:
                row = await db.get(SessionRow, uuid.UUID(session_id))
                return row.current_state
        return await _with_fresh_db(fn)

    assert asyncio.run(_check()) == "production"


def test_create_order_invalid_session(client: TestClient):
    resp = client.post(
        "/api/v1/orders",
        json={
            "session_id": str(uuid.uuid4()),
            "customer_name": "Nobody",
            "items": [
                {
                    "design_variant_id": str(uuid.uuid4()),
                    "product_id": "x",
                    "product_name": "X",
                    "color": "natural",
                    "quantity": 1,
                    "unit_price_paise": 100,
                }
            ],
        },
    )
    assert resp.status_code == 404


def test_create_order_null_variant_rejected(client: TestClient):
    _inject(client)
    session_id, variant_id = _seed(_seed_fallback)

    resp = client.post(
        "/api/v1/orders",
        json={
            "session_id": session_id,
            "customer_name": "Test Customer",
            "items": [
                {
                    "design_variant_id": variant_id,
                    "product_id": _PRODUCT_ID,
                    "product_name": "Standard T-Shirt",
                    "color": "natural",
                    "quantity": 1,
                    "unit_price_paise": _UNIT_PRICE,
                }
            ],
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "variant_not_printable"


def test_get_order(client: TestClient):
    _inject(client)
    session_id, variant_id = _seed(_seed_printable)

    create_resp = client.post(
        "/api/v1/orders",
        json={
            "session_id": session_id,
            "customer_name": "Meera Thomas",
            "items": [
                {
                    "design_variant_id": variant_id,
                    "product_id": _PRODUCT_ID,
                    "product_name": "Standard T-Shirt",
                    "color": "natural",
                    "quantity": 2,
                    "unit_price_paise": _UNIT_PRICE,
                }
            ],
        },
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["order_id"]

    get_resp = client.get(f"/api/v1/orders/{order_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["customer_name"] == "Meera Thomas"
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["subtotal_paise"] == _UNIT_PRICE * 2


def test_get_order_not_found(client: TestClient):
    resp = client.get(f"/api/v1/orders/{uuid.uuid4()}")
    assert resp.status_code == 404
