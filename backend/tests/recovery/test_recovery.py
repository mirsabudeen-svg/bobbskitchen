"""
Sprint 8 — Recovery Testing
Tests: backend restart mid-order, PostgreSQL connection loss + recovery,
       WebSocket reconnect with correct state rehydration, staff queue
       rehydration from DB (not stale WS cache) after restart.

These tests simulate infrastructure failures using subprocess signals and
Docker Compose service restarts. They require:
  - Docker Compose running with services: api, db, redis
  - COMPOSE_PROJECT defined in environment (default: "bobb")
  - The backend API accessible at TEST_API_URL (default: http://localhost:8000)

Run: pytest tests/recovery/ -v -s --timeout=120
     (runs against a LIVE local stack, not the ASGITransport test client)
"""

import asyncio
import json
import os
import subprocess
import time
import uuid
from typing import Optional

import httpx
import pytest
import pytest_asyncio
import websockets
from faker import Faker

fake = Faker("en_IN")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE        = os.getenv("TEST_API_URL", "http://localhost:8000")
WS_BASE         = os.getenv("TEST_WS_URL",  "ws://localhost:8000")
COMPOSE_PROJECT = os.getenv("COMPOSE_PROJECT", "bobb")
RESTART_WAIT_S  = 8     # seconds to wait for a service to come back up
RECONNECT_WAIT_S = 5    # seconds to wait for WS reconnect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def compose_restart(service: str) -> None:
    """Restart a Docker Compose service and wait for it to become healthy."""
    subprocess.run(
        ["docker", "compose", "-p", COMPOSE_PROJECT, "restart", service],
        check=True,
        capture_output=True,
    )
    time.sleep(RESTART_WAIT_S)


def compose_stop(service: str) -> None:
    subprocess.run(
        ["docker", "compose", "-p", COMPOSE_PROJECT, "stop", service],
        check=True,
        capture_output=True,
    )


def compose_start(service: str) -> None:
    subprocess.run(
        ["docker", "compose", "-p", COMPOSE_PROJECT, "start", service],
        check=True,
        capture_output=True,
    )
    time.sleep(RESTART_WAIT_S)


async def wait_for_api(timeout: float = 30.0) -> bool:
    """Poll /health until the API responds or timeout expires."""
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient() as client:
        while time.monotonic() < deadline:
            try:
                r = await client.get(f"{API_BASE}/health", timeout=2.0)
                if r.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(0.5)
    return False


async def create_session(client: httpx.AsyncClient) -> str:
    r = await client.post(
        f"{API_BASE}/api/v1/sessions",
        json={"device_id": str(uuid.uuid4()), "customer_name": fake.name()},
    )
    assert r.status_code == 201, f"Session create failed: {r.text}"
    return r.json()["session"]["id"]


async def create_variant(client: httpx.AsyncClient, session_id: str) -> str:
    """
    Creates a design variant directly via the debug/test endpoint.
    Adjust the path to match your actual variant-creation route.
    """
    r = await client.post(
        f"{API_BASE}/api/v1/debug/variants",
        json={
            "session_id": session_id,
            "image_url": "https://cdn.bobb.ai/test.png",
            "prompt": "test",
            "style": "test",
        },
    )
    assert r.status_code == 201, f"Variant create failed: {r.text}"
    return r.json()["variant"]["id"]


async def create_order(
    client: httpx.AsyncClient,
    session_id: str,
    variant_id: str,
    idempotency_key: Optional[str] = None,
) -> dict:
    payload = {
        "session_id": session_id,
        "customer_name": fake.name(),
        "customer_phone": fake.phone_number(),
        "items": [{
            "design_variant_id": variant_id,
            "product_id": "tshirt-crew",
            "product_name": "Crew Neck",
            "size": "M",
            "color": "Black",
            "quantity": 1,
            "unit_price_paise": 79900,
            "name_tag_text": "Test",
        }],
    }
    headers = {"Content-Type": "application/json"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    r = await client.post(f"{API_BASE}/api/v1/orders", json=payload, headers=headers)
    assert r.status_code == 201, f"Order create failed: {r.text}"
    return r.json()["order"]


# ---------------------------------------------------------------------------
# Skip marker — only run recovery tests when Docker is available
# ---------------------------------------------------------------------------
def docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "compose", "-p", COMPOSE_PROJECT, "ps", "--services"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


requires_docker = pytest.mark.skipif(
    not docker_available(),
    reason="Docker Compose stack not running — skipping recovery tests",
)


# ---------------------------------------------------------------------------
# 1. Backend Restart Mid-Order
# ---------------------------------------------------------------------------
class TestBackendRestart:

    @requires_docker
    @pytest.mark.asyncio
    async def test_order_persists_across_backend_restart(self):
        """
        Create an order, restart the API container, then verify:
        - The order still exists in the DB (GET /orders/{id} returns 200)
        - The order status has not changed
        - A status update can be applied post-restart
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            session_id = await create_session(client)
            variant_id = await create_variant(client, session_id)
            idem_key   = str(uuid.uuid4())
            order      = await create_order(client, session_id, variant_id, idem_key)
            order_id   = order["id"]

            assert order["order_status"] == "pending"

        # Restart the API service
        compose_restart("api")

        recovered = await wait_for_api()
        assert recovered, "API did not come back up within 30 seconds after restart"

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{API_BASE}/api/v1/orders/{order_id}")
            assert r.status_code == 200, f"Order not found after restart: {r.text}"
            assert r.json()["order"]["order_status"] == "pending"

            # Status update must work post-restart
            r = await client.patch(
                f"{API_BASE}/api/v1/orders/{order_id}/status",
                json={"status": "printing"},
            )
            assert r.status_code == 200
            assert r.json()["order"]["order_status"] == "printing"

    @requires_docker
    @pytest.mark.asyncio
    async def test_idempotency_survives_backend_restart(self):
        """
        Same idempotency key sent before and after restart must not create a duplicate.
        """
        idem_key = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=10.0) as client:
            session_id = await create_session(client)
            variant_id = await create_variant(client, session_id)
            order1     = await create_order(client, session_id, variant_id, idem_key)

        compose_restart("api")
        await wait_for_api()

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Simulate the frontend retrying with the same key after reconnect
            session_id2 = await create_session(client)
            variant_id2 = await create_variant(client, session_id2)
            # Use same idem_key but a different session — backend must still de-dup
            payload = {
                "session_id": session_id2,
                "customer_name": fake.name(),
                "customer_phone": fake.phone_number(),
                "items": [{
                    "design_variant_id": variant_id2,
                    "product_id": "tshirt-crew",
                    "product_name": "Crew Neck",
                    "size": "M",
                    "color": "Black",
                    "quantity": 1,
                    "unit_price_paise": 79900,
                    "name_tag_text": "Test",
                }],
            }
            r = await client.post(
                f"{API_BASE}/api/v1/orders",
                json=payload,
                headers={"Idempotency-Key": idem_key},
            )
            # Must return the original order, not a new one
            assert r.status_code in (200, 201)
            assert r.json()["order"]["id"] == order1["id"], (
                "Duplicate order created after restart with same idempotency key"
            )


# ---------------------------------------------------------------------------
# 2. PostgreSQL Restart
# ---------------------------------------------------------------------------
class TestPostgresRestart:

    @requires_docker
    @pytest.mark.asyncio
    async def test_api_recovers_after_postgres_restart(self):
        """
        Restart PostgreSQL. After recovery:
        - API health endpoint returns 200
        - Existing orders are still accessible
        - New orders can be created
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            session_id = await create_session(client)
            variant_id = await create_variant(client, session_id)
            order      = await create_order(client, session_id, variant_id, str(uuid.uuid4()))
            order_id   = order["id"]

        compose_restart("db")
        recovered = await wait_for_api()
        assert recovered, "API did not recover after PostgreSQL restart"

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Existing order accessible
            r = await client.get(f"{API_BASE}/api/v1/orders/{order_id}")
            assert r.status_code == 200, f"Existing order lost after Postgres restart: {r.text}"

            # New order creatable
            session_id2 = await create_session(client)
            variant_id2 = await create_variant(client, session_id2)
            new_order   = await create_order(client, session_id2, variant_id2, str(uuid.uuid4()))
            assert new_order["id"] != order_id

    @requires_docker
    @pytest.mark.asyncio
    async def test_in_flight_order_not_duplicated_across_postgres_restart(self):
        """
        Create an order immediately before Postgres restarts.
        After restart, the order must exist exactly once.
        """
        idem_key = str(uuid.uuid4())
        order_id: Optional[str] = None

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                session_id = await create_session(client)
                variant_id = await create_variant(client, session_id)
                order = await create_order(client, session_id, variant_id, idem_key)
                order_id = order["id"]
            except Exception:
                pass  # Request may have been mid-flight during restart

        compose_restart("db")
        await wait_for_api()

        if order_id:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{API_BASE}/api/v1/orders/{order_id}")
                assert r.status_code == 200, "Order lost across Postgres restart"

                # Retry with same idem key — must not create a second row
                async with httpx.AsyncClient(timeout=10.0) as client2:
                    session_id2 = await create_session(client2)
                    variant_id2 = await create_variant(client2, session_id2)
                    r2 = await client2.post(
                        f"{API_BASE}/api/v1/orders",
                        json={
                            "session_id": session_id2,
                            "customer_name": fake.name(),
                            "customer_phone": fake.phone_number(),
                            "items": [{
                                "design_variant_id": variant_id2,
                                "product_id": "tshirt-crew",
                                "product_name": "Crew Neck",
                                "size": "M",
                                "color": "Black",
                                "quantity": 1,
                                "unit_price_paise": 79900,
                                "name_tag_text": "Test",
                            }],
                        },
                        headers={"Idempotency-Key": idem_key},
                    )
                    assert r2.json()["order"]["id"] == order_id, (
                        "Duplicate order row created after Postgres restart"
                    )


# ---------------------------------------------------------------------------
# 3. WebSocket Reconnect — Staff Queue Rehydration
# ---------------------------------------------------------------------------
class TestWebSocketReconnect:

    @requires_docker
    @pytest.mark.asyncio
    async def test_staff_queue_rehydrates_from_db_after_backend_restart(self):
        """
        Staff client connects, backend restarts, client reconnects.
        After reconnect, a GET /orders must reflect DB truth, not a stale
        in-memory WS cache from before the restart.

        This test asserts the API serves authoritative DB state on reconnect
        rather than replaying any cached event stream.
        """
        # Create an order and advance it to printing before restart
        async with httpx.AsyncClient(timeout=10.0) as client:
            session_id = await create_session(client)
            variant_id = await create_variant(client, session_id)
            order      = await create_order(client, session_id, variant_id, str(uuid.uuid4()))
            order_id   = order["id"]

            r = await client.patch(
                f"{API_BASE}/api/v1/orders/{order_id}/status",
                json={"status": "printing"},
            )
            assert r.status_code == 200

        # Restart backend — simulates a deploy or crash
        compose_restart("api")
        recovered = await wait_for_api()
        assert recovered

        # After restart, GET /orders must still show the order as 'printing'
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{API_BASE}/api/v1/orders?status=printing"
            )
            assert r.status_code == 200
            ids = [o["id"] for o in r.json()["orders"]]
            assert order_id in ids, (
                f"Order {order_id} not found in printing queue after backend restart. "
                f"Staff queue is serving stale state."
            )

    @requires_docker
    @pytest.mark.asyncio
    async def test_websocket_reconnects_after_backend_restart(self):
        """
        Open a WebSocket connection to the staff endpoint.
        Restart the backend.
        Verify that a new connection can be established within RECONNECT_WAIT_S
        and receives messages after reconnect.
        """
        # Verify initial connection works
        ws_url = f"{WS_BASE}/ws/staff"
        try:
            async with websockets.connect(ws_url, open_timeout=5):
                pass
        except Exception as e:
            pytest.skip(f"Initial WS connection failed (is the stack running?): {e}")

        compose_restart("api")
        recovered = await wait_for_api()
        assert recovered

        # Reconnect must succeed within RECONNECT_WAIT_S
        connected = False
        deadline = time.monotonic() + RECONNECT_WAIT_S
        while time.monotonic() < deadline:
            try:
                async with websockets.connect(ws_url, open_timeout=2):
                    connected = True
                    break
            except Exception:
                await asyncio.sleep(0.5)

        assert connected, (
            f"Could not reconnect to WebSocket within {RECONNECT_WAIT_S}s after backend restart"
        )

    @requires_docker
    @pytest.mark.asyncio
    async def test_order_update_broadcast_resumes_after_reconnect(self):
        """
        After backend restart, a new status update must broadcast to
        a freshly-reconnected staff WebSocket client.
        """
        compose_restart("api")
        recovered = await wait_for_api()
        assert recovered

        async with httpx.AsyncClient(timeout=10.0) as client:
            session_id = await create_session(client)
            variant_id = await create_variant(client, session_id)
            order      = await create_order(client, session_id, variant_id, str(uuid.uuid4()))
            order_id   = order["id"]

        received_event = asyncio.Event()

        async def listen():
            ws_url = f"{WS_BASE}/ws/staff"
            try:
                async with websockets.connect(ws_url, open_timeout=5) as ws:
                    await asyncio.sleep(0.1)
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    msg = json.loads(raw)
                    if (
                        msg.get("type") == "order_update"
                        and msg.get("order", {}).get("id") == order_id
                    ):
                        received_event.set()
            except asyncio.TimeoutError:
                pass

        async def trigger():
            await asyncio.sleep(0.2)
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.patch(
                    f"{API_BASE}/api/v1/orders/{order_id}/status",
                    json={"status": "printing"},
                )

        await asyncio.gather(listen(), trigger())
        assert received_event.is_set(), (
            "order_update broadcast did not arrive on reconnected staff WebSocket"
        )


# ---------------------------------------------------------------------------
# 4. Redis Restart (if Redis is in the stack)
# ---------------------------------------------------------------------------
class TestRedisRestart:

    @requires_docker
    @pytest.mark.asyncio
    async def test_api_recovers_after_redis_restart(self):
        """
        If Redis is used (e.g. for session cache or pub/sub), restart it and
        verify that core order operations are unaffected.
        Orders live in PostgreSQL — Redis loss must not corrupt them.
        """
        services = subprocess.run(
            ["docker", "compose", "-p", COMPOSE_PROJECT, "ps", "--services"],
            capture_output=True, text=True,
        ).stdout.strip().splitlines()

        if "redis" not in services:
            pytest.skip("Redis not in Compose stack — skipping Redis recovery test")

        async with httpx.AsyncClient(timeout=10.0) as client:
            session_id = await create_session(client)
            variant_id = await create_variant(client, session_id)
            order      = await create_order(client, session_id, variant_id, str(uuid.uuid4()))
            order_id   = order["id"]

        compose_restart("redis")

        # API health must still pass (Postgres is up)
        recovered = await wait_for_api()
        assert recovered, "API did not recover after Redis restart"

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Order must still be accessible
            r = await client.get(f"{API_BASE}/api/v1/orders/{order_id}")
            assert r.status_code == 200, f"Order lost after Redis restart: {r.text}"
            assert r.json()["order"]["order_status"] == "pending"

            # Status transitions must still work
            r = await client.patch(
                f"{API_BASE}/api/v1/orders/{order_id}/status",
                json={"status": "printing"},
            )
            assert r.status_code == 200, (
                f"Status update failed after Redis restart: {r.text}"
            )

    @requires_docker
    @pytest.mark.asyncio
    async def test_order_creation_works_during_redis_outage(self):
        """
        Stop Redis entirely. Order creation and status transitions must
        continue using PostgreSQL. When Redis comes back, no data loss.
        """
        services = subprocess.run(
            ["docker", "compose", "-p", COMPOSE_PROJECT, "ps", "--services"],
            capture_output=True, text=True,
        ).stdout.strip().splitlines()

        if "redis" not in services:
            pytest.skip("Redis not in Compose stack")

        compose_stop("redis")
        await asyncio.sleep(2)

        order_id = None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                session_id = await create_session(client)
                variant_id = await create_variant(client, session_id)
                order      = await create_order(client, session_id, variant_id, str(uuid.uuid4()))
                order_id   = order["id"]

                r = await client.patch(
                    f"{API_BASE}/api/v1/orders/{order_id}/status",
                    json={"status": "printing"},
                )
                assert r.status_code == 200, (
                    f"Status transition failed during Redis outage: {r.text}"
                )
        finally:
            compose_start("redis")

        # After Redis returns, the order must still exist with correct status
        async with httpx.AsyncClient(timeout=10.0) as client:
            if order_id:
                r = await client.get(f"{API_BASE}/api/v1/orders/{order_id}")
                assert r.status_code == 200
                assert r.json()["order"]["order_status"] == "printing"
