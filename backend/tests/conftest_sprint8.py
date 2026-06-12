"""
Sprint 8 conftest — adapted for BOBB model layout (app.models.db).
Place this file alongside the sprint8 test directories or import from it.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from faker import Faker
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.base import Base, get_db
from app.models.db import Design, DesignVariantRow, Order, OrderItem, Session as KioskSession

fake = Faker("en_IN")

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://bobb:bobb@localhost:5432/bobb_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(setup_db) -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


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
    payload = {
        "session_id": session_id,
        "customer_name": fake.name(),
        "customer_phone": fake.phone_number(),
        "items": [
            {
                "design_variant_id": variant_id,
                # Unknown product ID — price validation skipped gracefully
                "product_id": "tshirt-crew",
                "product_name": "Crew Neck",
                "size": size,
                "color": "Black",
                "quantity": quantity,
                "unit_price_paise": unit_price_paise,
                "name_tag_text": fake.first_name()[:15],
            }
        ],
    }
    headers = {}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return payload, headers


async def seed_variant(
    db: AsyncSession,
    image_url: str = "https://cdn.bobb.ai/test.png",
) -> DesignVariantRow:
    """Create a minimal Session + Design + DesignVariantRow for test seeding."""
    session_row = KioskSession(id=uuid.uuid4(), current_state="greeting")
    db.add(session_row)
    await db.flush()

    design = Design(
        id=uuid.uuid4(),
        session_id=session_row.id,
        story_json={"debug": True},
        design_prompt_base="test prompt",
    )
    db.add(design)
    await db.flush()

    variant = DesignVariantRow(
        id=uuid.uuid4(),
        design_id=design.id,
        variant_number=1,
        prompt_used="test prompt",
        style="illustration",
        image_url=image_url,
        is_fallback=False,
    )
    db.add(variant)
    await db.flush()
    return variant


async def seed_kiosk_session(db: AsyncSession) -> KioskSession:
    session = KioskSession(
        id=uuid.uuid4(),
        current_state="greeting",
        customer_name=fake.name(),
    )
    db.add(session)
    await db.flush()
    return session
