"""
Sprint 8 — Pilot Simulation & Hardening
Shared conftest: async test client, isolated DB, WebSocket helper, mock factories.

Requirements:
    pip install pytest pytest-asyncio httpx anyio asyncpg sqlalchemy[asyncio] \
                faker websockets locust psutil
"""

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import date
from typing import Any

import pytest
import pytest_asyncio
from faker import Faker
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# ---------------------------------------------------------------------------
# Adjust these imports to your actual project layout
# ---------------------------------------------------------------------------
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.session import Session as KioskSession
from app.models.design_variant import DesignVariant

fake = Faker("en_IN")

# ---------------------------------------------------------------------------
# Database — isolated test DB using NullPool to avoid asyncpg pool conflicts
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://bobb:bobb@localhost:5432/bobb_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    """Create all tables once per test session, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(setup_db) -> AsyncGenerator[AsyncSession, None]:
    """Per-test DB session with automatic rollback for isolation."""
    async with TestSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to the FastAPI app with the test DB session."""
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# WebSocket helper
# ---------------------------------------------------------------------------
class WSClient:
    """Thin wrapper around FastAPI's test WebSocket interface."""

    def __init__(self, client: AsyncClient, session_id: str):
        self.session_id = session_id
        self._client = client
        self._messages: list[dict] = []

    async def collect(self, count: int, timeout: float = 5.0) -> list[dict]:
        """Collect `count` messages from the WS with a timeout."""
        import json
        collected = []
        try:
            async with asyncio.timeout(timeout):
                async with self._client.websocket_connect(
                    f"/ws/{self.session_id}"
                ) as ws:
                    for _ in range(count):
                        raw = await ws.receive_text()
                        collected.append(json.loads(raw))
        except asyncio.TimeoutError:
            pass
        return collected


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_session_payload() -> dict:
    return {
        "device_id": str(uuid.uuid4()),
        "customer_name": fake.name(),
    }


def make_story_payload() -> dict:
    return {
        "story_text": fake.sentence(nb_words=20),
        "voice_tone": "warm",
    }


def make_order_payload(
    session_id: str,
    variant_id: str,
    size: str = "M",
    quantity: int = 1,
    unit_price_paise: int = 79900,
    idempotency_key: str | None = None,
) -> tuple[dict, dict]:
    """Returns (payload, headers)."""
    payload = {
        "session_id": session_id,
        "customer_name": fake.name(),
        "customer_phone": fake.phone_number(),
        "items": [
            {
                "design_variant_id": variant_id,
                "product_id": "tshirt-crew",
                "product_name": "Crew Neck",
                "size": size,
                "color": "Black",
                "quantity": quantity,
                "unit_price_paise": unit_price_paise,
                "name_tag_text": fake.first_name(),
            }
        ],
    }
    headers = {}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return payload, headers


async def seed_variant(db: AsyncSession, image_url: str = "https://cdn.bobb.ai/test.png") -> DesignVariant:
    """Insert a minimal DesignVariant row and return it."""
    variant = DesignVariant(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        image_url=image_url,
        prompt="test prompt",
        style="test",
        is_fallback=False,
        is_selected=False,
    )
    db.add(variant)
    await db.flush()
    return variant


async def seed_kiosk_session(db: AsyncSession) -> KioskSession:
    """Insert a minimal kiosk session and return it."""
    session = KioskSession(
        id=uuid.uuid4(),
        current_state="greeting",
        customer_name=fake.name(),
    )
    db.add(session)
    await db.flush()
    return session
