"""
Sprint 8 — Load Testing
Tests: concurrent sessions, order burst, WebSocket broadcast under load,
       short-ref uniqueness under race conditions.

Run:  pytest tests/load/ -v --timeout=120
"""

import asyncio
import time
import uuid
from collections import Counter

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import (
    make_order_payload,
    make_session_payload,
    seed_kiosk_session,
    seed_variant,
)

# ---------------------------------------------------------------------------
# Thresholds — adjust for your hardware
# ---------------------------------------------------------------------------
CONCURRENT_SESSIONS      = 40   # simultaneous kiosk sessions
ORDER_BURST_SIZE         = 60   # orders fired in one wave
P95_SESSION_MS           = 300  # p95 session-create latency budget
P95_ORDER_MS             = 500  # p95 order-create latency budget
WS_BROADCAST_TIMEOUT_S   = 2.0  # all staff clients must receive event within this window
SHORT_REF_RACE_WORKERS   = 20   # concurrent short-ref generators to stress the counter


# ---------------------------------------------------------------------------
# 1. Concurrent Session Creation
# ---------------------------------------------------------------------------
class TestConcurrentSessions:

    @pytest.mark.asyncio
    async def test_40_concurrent_sessions_all_succeed(self, client: AsyncClient):
        """
        40 session-create requests fired simultaneously.
        All must return 201, all session IDs must be unique,
        and p95 latency must stay under P95_SESSION_MS.
        """
        async def create_one():
            t0 = time.monotonic()
            r = await client.post("/api/v1/sessions", json=make_session_payload())
            elapsed_ms = (time.monotonic() - t0) * 1000
            return r.status_code, r.json().get("session", {}).get("id"), elapsed_ms

        results = await asyncio.gather(*[create_one() for _ in range(CONCURRENT_SESSIONS)])

        statuses   = [r[0] for r in results]
        ids        = [r[1] for r in results]
        latencies  = sorted(r[2] for r in results)

        assert all(s == 201 for s in statuses), (
            f"Some sessions failed: {Counter(statuses)}"
        )
        assert len(set(ids)) == CONCURRENT_SESSIONS, (
            f"Duplicate session IDs detected: {len(set(ids))} unique out of {CONCURRENT_SESSIONS}"
        )

        p95_idx = int(0.95 * len(latencies))
        p95 = latencies[p95_idx]
        assert p95 < P95_SESSION_MS, (
            f"p95 session-create latency {p95:.1f}ms exceeds budget {P95_SESSION_MS}ms"
        )

    @pytest.mark.asyncio
    async def test_session_ids_are_uuidv4(self, client: AsyncClient):
        """Session IDs must be valid UUID4 strings."""
        tasks = [client.post("/api/v1/sessions", json=make_session_payload()) for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        for r in responses:
            sid = r.json().get("session", {}).get("id", "")
            parsed = uuid.UUID(sid)
            assert parsed.version == 4, f"Session ID {sid} is not UUID4"


# ---------------------------------------------------------------------------
# 2. Order Burst — 60 orders, all different sessions
# ---------------------------------------------------------------------------
class TestOrderBurst:

    @pytest_asyncio.fixture(autouse=True)
    async def seed(self, db, client):
        """Pre-seed sessions and variants for the burst."""
        self.sessions = []
        self.variants = []
        for _ in range(ORDER_BURST_SIZE):
            session = await seed_kiosk_session(db)
            variant = await seed_variant(db)
            self.sessions.append(session)
            self.variants.append(variant)

    @pytest.mark.asyncio
    async def test_60_concurrent_orders_all_succeed(self, client: AsyncClient):
        """
        60 orders fired simultaneously, each from a distinct session.
        All must succeed (201), all order IDs unique, p95 under budget.
        """
        idem_keys = [str(uuid.uuid4()) for _ in range(ORDER_BURST_SIZE)]

        async def place_one(i: int):
            payload, headers = make_order_payload(
                session_id=str(self.sessions[i].id),
                variant_id=str(self.variants[i].id),
                idempotency_key=idem_keys[i],
            )
            t0 = time.monotonic()
            r = await client.post("/api/v1/orders", json=payload, headers=headers)
            elapsed_ms = (time.monotonic() - t0) * 1000
            return r.status_code, r.json().get("order", {}).get("id"), elapsed_ms

        results = await asyncio.gather(*[place_one(i) for i in range(ORDER_BURST_SIZE)])

        statuses  = [r[0] for r in results]
        order_ids = [r[1] for r in results]
        latencies = sorted(r[2] for r in results)

        assert all(s == 201 for s in statuses), (
            f"Some orders failed: {Counter(statuses)}"
        )
        assert len(set(order_ids)) == ORDER_BURST_SIZE, (
            f"Duplicate order IDs in burst: {len(set(order_ids))} unique"
        )

        p95_idx = int(0.95 * len(latencies))
        p95 = latencies[p95_idx]
        assert p95 < P95_ORDER_MS, (
            f"p95 order-create latency {p95:.1f}ms exceeds budget {P95_ORDER_MS}ms"
        )

    @pytest.mark.asyncio
    async def test_short_refs_unique_across_burst(self, client: AsyncClient):
        """
        All 60 orders placed today must have unique short refs (B-001…B-060).
        Tests the atomic daily counter under concurrent inserts.
        """
        async def place_one(i: int):
            payload, headers = make_order_payload(
                session_id=str(self.sessions[i].id),
                variant_id=str(self.variants[i].id),
                idempotency_key=str(uuid.uuid4()),
            )
            r = await client.post("/api/v1/orders", json=payload, headers=headers)
            return r.json().get("order", {}).get("short_ref")

        refs = await asyncio.gather(*[place_one(i) for i in range(ORDER_BURST_SIZE)])
        refs = [r for r in refs if r]  # filter None on any unexpected failure

        assert len(refs) == len(set(refs)), (
            f"Duplicate short refs under concurrent load: {[r for r, c in Counter(refs).items() if c > 1]}"
        )
        # All must match B-NNN format
        import re
        pattern = re.compile(r"^B-\d{3}$")
        malformed = [r for r in refs if not pattern.match(r)]
        assert not malformed, f"Malformed short refs: {malformed}"

    @pytest.mark.asyncio
    async def test_idempotency_under_concurrent_retry(self, client: AsyncClient):
        """
        Same idempotency key sent 5 times concurrently must produce exactly one order row.
        """
        session = self.sessions[0]
        variant = self.variants[0]
        key = str(uuid.uuid4())

        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=key,
        )

        results = await asyncio.gather(*[
            client.post("/api/v1/orders", json=payload, headers=headers)
            for _ in range(5)
        ])

        statuses   = [r.status_code for r in results]
        order_ids  = {r.json().get("order", {}).get("id") for r in results}

        assert all(s in (200, 201) for s in statuses), f"Unexpected statuses: {statuses}"
        assert len(order_ids) == 1, (
            f"Idempotency failure: {len(order_ids)} distinct order rows created from one key"
        )


# ---------------------------------------------------------------------------
# 3. WebSocket Broadcast Fan-Out Under Load
# ---------------------------------------------------------------------------
class TestWebSocketBroadcast:

    @pytest.mark.asyncio
    async def test_order_update_reaches_all_staff_clients(self, client: AsyncClient, db):
        """
        10 staff clients connected simultaneously.
        One order status update is fired.
        All 10 clients must receive the order_update event within WS_BROADCAST_TIMEOUT_S.
        """
        import json

        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)

        # Create the order first
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        assert r.status_code == 201
        order_id = r.json()["order"]["id"]

        received: list[bool] = []

        async def listen_for_update(staff_session_id: str):
            got_it = False
            try:
                async with asyncio.timeout(WS_BROADCAST_TIMEOUT_S):
                    async with client.websocket_connect(f"/ws/staff") as ws:
                        # Trigger the status update while listening
                        await asyncio.sleep(0.05)
                        raw = await ws.receive_text()
                        msg = json.loads(raw)
                        if msg.get("type") == "order_update" and msg.get("order", {}).get("id") == order_id:
                            got_it = True
            except asyncio.TimeoutError:
                pass
            received.append(got_it)

        # Start 10 staff listeners
        listeners = [listen_for_update(str(uuid.uuid4())) for _ in range(10)]

        # Trigger an update after a brief delay so all listeners are connected
        async def trigger_update():
            await asyncio.sleep(0.1)
            await client.patch(
                f"/api/v1/orders/{order_id}/status",
                json={"status": "printing"},
            )

        await asyncio.gather(*listeners, trigger_update())

        assert all(received), (
            f"Not all staff clients received the broadcast: {received.count(True)}/10 received it"
        )

    @pytest.mark.asyncio
    async def test_payment_update_broadcasts_to_staff(self, client: AsyncClient, db):
        """Payment recording must also push an order_update event."""
        import json

        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)

        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        order_id = r.json()["order"]["id"]

        got_event = asyncio.Event()

        async def listen():
            try:
                async with asyncio.timeout(WS_BROADCAST_TIMEOUT_S):
                    async with client.websocket_connect("/ws/staff") as ws:
                        await asyncio.sleep(0.05)
                        raw = await ws.receive_text()
                        msg = json.loads(raw)
                        if (
                            msg.get("type") == "order_update"
                            and msg.get("order", {}).get("payment_status") == "paid"
                        ):
                            got_event.set()
            except asyncio.TimeoutError:
                pass

        async def trigger():
            await asyncio.sleep(0.1)
            await client.patch(
                f"/api/v1/orders/{order_id}/payment",
                json={"payment_method": "cash"},
            )

        await asyncio.gather(listen(), trigger())
        assert got_event.is_set(), "Payment update did not broadcast to staff WebSocket"


# ---------------------------------------------------------------------------
# 4. Throughput Model — DTF press capacity check
# ---------------------------------------------------------------------------
class TestDTFThroughputModel:
    """
    Not a system test — a queuing model that asserts the 14-minute
    journey promise holds at 60 orders/day.

    Assumptions (adjust to your actual press specs):
        - One press, one operator
        - Average print + press + cure time per garment: 5 minutes
        - Average customer arrival gap: 14 min / 60 orders ≈ 0.23 min apart
        - Journey duration: 14 minutes
    """

    PRESS_TIME_MINUTES        = 5.0
    JOURNEY_MINUTES           = 14.0
    ORDERS_PER_JOURNEY        = 60
    ACCEPTABLE_WAIT_MINUTES   = 14.0  # promise to customer

    def test_single_press_can_fulfil_journey_volume(self):
        """
        Simulate order arrivals as a simple M/D/1 queue.
        Assert median wait stays under the journey promise.
        """
        arrival_gap = self.JOURNEY_MINUTES / self.ORDERS_PER_JOURNEY

        # Simulate 60 orders arriving at uniform intervals
        arrival_times = [i * arrival_gap for i in range(self.ORDERS_PER_JOURNEY)]
        press_free_at = 0.0
        wait_times = []

        for arrival in arrival_times:
            start_press = max(arrival, press_free_at)
            wait = start_press - arrival
            wait_times.append(wait)
            press_free_at = start_press + self.PRESS_TIME_MINUTES

        wait_times.sort()
        median_wait  = wait_times[len(wait_times) // 2]
        p95_wait     = wait_times[int(0.95 * len(wait_times))]
        max_wait     = wait_times[-1]

        print(f"\n--- DTF Throughput Model ---")
        print(f"Arrival gap:   {arrival_gap:.2f} min")
        print(f"Press time:    {self.PRESS_TIME_MINUTES} min")
        print(f"Median wait:   {median_wait:.1f} min")
        print(f"p95 wait:      {p95_wait:.1f} min")
        print(f"Max wait:      {max_wait:.1f} min")
        print(f"Journey promise: {self.ACCEPTABLE_WAIT_MINUTES} min")

        assert median_wait <= self.ACCEPTABLE_WAIT_MINUTES, (
            f"Median wait {median_wait:.1f} min already breaks the journey promise "
            f"at {self.ORDERS_PER_JOURNEY} orders in {self.JOURNEY_MINUTES} min. "
            f"Need a second press or longer journey window."
        )

        if p95_wait > self.ACCEPTABLE_WAIT_MINUTES:
            import warnings
            warnings.warn(
                f"p95 wait {p95_wait:.1f} min exceeds journey promise for the top 5% of customers. "
                f"Consider a second press for peak days.",
                stacklevel=2,
            )
