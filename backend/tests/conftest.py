"""Test fixtures.

The DB engine is injected via app.state so tests use the same DATABASE_URL
as CI (postgres service) without touching the module-global engine from Sprint 0.
Using TestClient (sync) keeps tests simple — no anyio/asyncio fixture juggling
for Sprint 1.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.db.base import create_engine, create_session_factory
from app.main import app


@pytest.fixture(scope="session")
def db_engine():
    """One engine for the whole test session (same DB as CI postgres service)."""
    settings = get_settings()
    engine = create_engine(settings)
    yield engine
    # Engine disposal is sync-incompatible; rely on process exit in test runs.


@pytest.fixture(scope="session")
def db_session_factory(db_engine):
    return create_session_factory(db_engine)


@pytest.fixture
def client(db_session_factory: async_sessionmaker) -> TestClient:
    """TestClient with app.state wired to the test DB engine."""
    app.state.session_factory = db_session_factory
    return TestClient(app)
