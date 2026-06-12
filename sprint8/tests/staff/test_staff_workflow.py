"""
Sprint 8 — Staff Workflow Testing
Tests every staff-facing operation: queue listing, filtering, short-ref lookup,
all valid and invalid status transitions, payment recording, reconciliation,
and the name-tag / print-spec surface in the order card.

Run: pytest tests/staff/ -v --timeout=60
"""

import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from faker import Faker
from httpx import AsyncClient

from tests.conftest import (
    make_order_payload,
    seed_kiosk_session,
    seed_variant,
)

fake = Faker("en_IN")


# ---------------------------------------------------------------------------
# Helper: fast-track an order to a given status
# ---------------------------------------------------------------------------
async def advance_order(client: AsyncClient, order_id: str, *statuses: str) -> None:
    for status in statuses:
        r = await client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": status},
        )
        assert r.status_code == 200, f"Failed to advance to '{status}': {r.text}"


async def create_paid_ready_order(client: AsyncClient, db) -> str:
    """Convenience: seed → create → printing → pay → ready. Returns order_id."""
    session = await seed_kiosk_session(db)
    variant = await seed_variant(db)
    payload, headers = make_order_payload(
        session_id=str(session.id),
        variant_id=str(variant.id),
        idempotency_key=str(uuid.uuid4()),
    )
    r = await client.post("/api/v1/orders", json=payload, headers=headers)
    assert r.status_code == 201
    oid = r.json()["order"]["id"]

    await advance_order(client, oid, "printing", "ready")
    await client.patch(f"/api/v1/orders/{oid}/payment", json={"payment_method": "cash"})
    return oid


# ---------------------------------------------------------------------------
# 1. Queue listing and filtering
# ---------------------------------------------------------------------------
class TestStaffQueue:

    @pytest.mark.asyncio
    async def test_get_orders_today_returns_all(self, client: AsyncClient, db):
        """GET /orders returns all orders created today."""
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)

        for _ in range(3):
            payload, headers = make_order_payload(
                session_id=str(session.id),
                variant_id=str(variant.id),
                idempotency_key=str(uuid.uuid4()),
            )
            await client.post("/api/v1/orders", json=payload, headers=headers)

        r = await client.get(f"/api/v1/orders?date={date.today().isoformat()}")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] >= 3
        assert len(data["orders"]) >= 3

    @pytest.mark.asyncio
    async def test_get_orders_filters_by_status(self, client: AsyncClient, db):
        """Filtering by status returns only orders in that state."""
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)

        # Create two orders: leave one pending, advance one to printing
        ids = []
        for _ in range(2):
            payload, headers = make_order_payload(
                session_id=str(session.id),
                variant_id=str(variant.id),
                idempotency_key=str(uuid.uuid4()),
            )
            r = await client.post("/api/v1/orders", json=payload, headers=headers)
            ids.append(r.json()["order"]["id"])

        await advance_order(client, ids[1], "printing")

        r = await client.get(f"/api/v1/orders?status=pending&date={date.today().isoformat()}")
        assert r.status_code == 200
        statuses = [o["order_status"] for o in r.json()["orders"]]
        assert all(s == "pending" for s in statuses), f"Non-pending orders in result: {statuses}"

        r = await client.get(f"/api/v1/orders?status=printing&date={date.today().isoformat()}")
        assert r.status_code == 200
        statuses = [o["order_status"] for o in r.json()["orders"]]
        assert all(s == "printing" for s in statuses)

    @pytest.mark.asyncio
    async def test_orders_sorted_ascending_by_created_at(self, client: AsyncClient, db):
        """Queue must be FIFO — earliest order first."""
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)

        order_ids = []
        for _ in range(5):
            payload, headers = make_order_payload(
                session_id=str(session.id),
                variant_id=str(variant.id),
                idempotency_key=str(uuid.uuid4()),
            )
            r = await client.post("/api/v1/orders", json=payload, headers=headers)
            order_ids.append(r.json()["order"]["id"])

        r = await client.get(f"/api/v1/orders?date={date.today().isoformat()}")
        returned_ids = [o["id"] for o in r.json()["orders"]]

        # The first created order must appear before the last
        assert returned_ids.index(order_ids[0]) < returned_ids.index(order_ids[-1]), (
            "Queue is not sorted by created_at ASC"
        )

    @pytest.mark.asyncio
    async def test_print_spec_present_on_order_items(self, client: AsyncClient, db):
        """Order items in the staff queue must include image_url and print spec fields."""
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db, image_url="https://cdn.bobb.ai/test-design.png")

        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        order_id = r.json()["order"]["id"]

        r = await client.get(f"/api/v1/orders/{order_id}")
        assert r.status_code == 200
        item = r.json()["order"]["items"][0]

        assert item["image_url"] is not None, "image_url missing from order item"
        assert item["image_url"] == "https://cdn.bobb.ai/test-design.png"
        assert item["print_placement"] is not None, "print_placement missing"

    @pytest.mark.asyncio
    async def test_name_tag_text_visible_on_item(self, client: AsyncClient, db):
        """name_tag_text must be present on the order item for the staff queue."""
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)

        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        payload["items"][0]["name_tag_text"] = "Rahul"

        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        order_id = r.json()["order"]["id"]

        r = await client.get(f"/api/v1/orders/{order_id}")
        item = r.json()["order"]["items"][0]
        assert item["name_tag_text"] == "Rahul", "name_tag_text not surfaced on order item"


# ---------------------------------------------------------------------------
# 2. Short-ref lookup
# ---------------------------------------------------------------------------
class TestShortRefLookup:

    @pytest.mark.asyncio
    async def test_lookup_by_short_ref_returns_correct_order(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        assert r.status_code == 201
        order = r.json()["order"]
        ref = order["short_ref"]
        order_id = order["id"]

        r = await client.get(f"/api/v1/orders/lookup?ref={ref}")
        assert r.status_code == 200
        assert r.json()["order"]["id"] == order_id

    @pytest.mark.asyncio
    async def test_lookup_case_insensitive(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        ref = r.json()["order"]["short_ref"]  # e.g. "B-003"

        r = await client.get(f"/api/v1/orders/lookup?ref={ref.lower()}")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_lookup_unknown_ref_returns_404(self, client: AsyncClient):
        r = await client.get("/api/v1/orders/lookup?ref=X-999")
        assert r.status_code == 404
        assert r.json()["detail"]["error"] == "order_not_found"


# ---------------------------------------------------------------------------
# 3. Status transition state machine
# ---------------------------------------------------------------------------
class TestStatusTransitions:

    @pytest.mark.asyncio
    async def test_valid_happy_path_pending_to_collected(self, client: AsyncClient, db):
        oid = await create_paid_ready_order(client, db)

        # ready → collected (payment already recorded)
        r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "collected"})
        assert r.status_code == 200
        assert r.json()["order"]["order_status"] == "collected"

    @pytest.mark.asyncio
    async def test_invalid_skip_pending_to_collected_rejected(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "collected"})
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert detail["error"] == "invalid_status_transition"
        assert detail["current"] == "pending"

    @pytest.mark.asyncio
    async def test_invalid_skip_pending_to_ready_rejected(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "ready"})
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_collected_is_terminal(self, client: AsyncClient, db):
        oid = await create_paid_ready_order(client, db)
        await advance_order(client, oid, "collected")

        # Any attempt to move out of collected must fail
        for next_status in ("pending", "printing", "ready", "failed"):
            r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": next_status})
            assert r.status_code == 409, (
                f"collected → {next_status} should be rejected but returned {r.status_code}"
            )

    @pytest.mark.asyncio
    async def test_reprint_path_failed_to_reprinting_to_ready(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        await advance_order(client, oid, "printing")
        r = await client.patch(
            f"/api/v1/orders/{oid}/status",
            json={"status": "failed", "staff_notes": "Film jam"},
        )
        assert r.status_code == 200

        r = await client.patch(
            f"/api/v1/orders/{oid}/status",
            json={"status": "reprinting", "staff_notes": "Reprinting now"},
        )
        assert r.status_code == 200
        assert r.json()["order"]["reprint_count"] == 1

        r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "ready"})
        assert r.status_code == 200
        assert r.json()["order"]["order_status"] == "ready"

    @pytest.mark.asyncio
    async def test_staff_notes_persisted_on_transition(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        note = "Press temp was low — recured for 30 extra seconds"
        await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "printing"})
        r = await client.patch(
            f"/api/v1/orders/{oid}/status",
            json={"status": "ready", "staff_notes": note},
        )
        assert r.status_code == 200

        r = await client.get(f"/api/v1/orders/{oid}")
        assert r.json()["order"]["staff_notes"] == note


# ---------------------------------------------------------------------------
# 4. Payment recording
# ---------------------------------------------------------------------------
class TestPaymentRecording:

    @pytest.mark.asyncio
    async def test_record_cash_payment(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        r = await client.patch(f"/api/v1/orders/{oid}/payment", json={"payment_method": "cash"})
        assert r.status_code == 200
        order = r.json()["order"]
        assert order["payment_status"] == "paid"
        assert order["payment_method"] == "cash"

    @pytest.mark.asyncio
    async def test_record_upi_payment(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        r = await client.patch(f"/api/v1/orders/{oid}/payment", json={"payment_method": "upi"})
        assert r.status_code == 200
        assert r.json()["order"]["payment_method"] == "upi"

    @pytest.mark.asyncio
    async def test_payment_recording_idempotent(self, client: AsyncClient, db):
        """Recording payment twice must return 200 both times with the same state."""
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        r1 = await client.patch(f"/api/v1/orders/{oid}/payment", json={"payment_method": "cash"})
        r2 = await client.patch(f"/api/v1/orders/{oid}/payment", json={"payment_method": "cash"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json()["order"]["payment_status"] == "paid"

    @pytest.mark.asyncio
    async def test_invalid_payment_method_rejected(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        r = await client.patch(f"/api/v1/orders/{oid}/payment", json={"payment_method": "bitcoin"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_collect_without_payment_rejected(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        await advance_order(client, oid, "printing", "ready")

        # No payment recorded — collect must fail
        r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "collected"})
        assert r.status_code == 409
        assert "payment_required" in r.json()["detail"]["error"]


# ---------------------------------------------------------------------------
# 5. Reconciliation
# ---------------------------------------------------------------------------
class TestReconciliation:

    @pytest.mark.asyncio
    async def test_reconciliation_empty_day(self, client: AsyncClient):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        r = await client.get(f"/api/v1/orders/reconciliation?date={yesterday}")
        assert r.status_code == 200
        recon = r.json()
        assert recon["total_orders"] == 0
        assert recon["grand_total_paise"] == 0

    @pytest.mark.asyncio
    async def test_reconciliation_counts_failed_prints(self, client: AsyncClient, db):
        session = await seed_kiosk_session(db)
        variant = await seed_variant(db)
        payload, headers = make_order_payload(
            session_id=str(session.id),
            variant_id=str(variant.id),
            idempotency_key=str(uuid.uuid4()),
        )
        r = await client.post("/api/v1/orders", json=payload, headers=headers)
        oid = r.json()["order"]["id"]

        await advance_order(client, oid, "printing")
        await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "failed"})

        r = await client.get(f"/api/v1/orders/reconciliation?date={date.today().isoformat()}")
        assert r.json()["failed_orders"] >= 1
