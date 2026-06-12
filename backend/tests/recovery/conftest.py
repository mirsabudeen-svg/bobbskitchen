"""Override `client` fixture with AsyncClient for sprint8 load tests."""
from tests.conftest import async_client as client  # noqa: F401
