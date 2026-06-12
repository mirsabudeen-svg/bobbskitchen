"""
Sprint 8 — Multi-Order Simulation
Simulates a full Saturday: 40 customers, realistic timing, concurrent story/design/order
flows, mixed payment methods, reprints, and end-of-day reconciliation.

Run: pytest tests/simulation/ -v -s --timeout=300
"""

import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pytest
import pytest_asyncio
from faker import Faker
from httpx import AsyncClient

from tests.conftest import seed_kiosk_session, seed_variant

fake = Faker("en_IN")
random.seed(42)

# ---------------------------------------------------------------------------
# Simulation parameters
# ---------------------------------------------------------------------------
CUSTOMERS              = 40
REPRINT_PROBABILITY    = 0.05   # 5% of orders → reprint (realistic DTF failure rate)
UPI_PROBABILITY        = 0.40   # 40% pay UPI, 60% cash
SIZES                  = ["S", "M", "L", "XL", "XXL"]
COLORS                 = ["Black", "White", "Navy", "Maroon", "Olive"]


# ---------------------------------------------------------------------------
# Customer scenario model
# ---------------------------------------------------------------------------
@dataclass
class CustomerScenario:
    idx: int
    name: str
    phone: str
    size: str
    color: str
    payment_method: str
    quantity: int
    triggers_reprint: bool
    order_id: Optional[str] = None
    short_ref: Optional[str] = None
    final_status: Optional[str] = None


def build_saturday_scenarios() -> list[CustomerScenario]:
    scenarios = []
    for i in range(CUSTOMERS):
        scenarios.append(CustomerScenario(
            idx=i,
            name=fake.name(),
            phone=fake.phone_number(),
            size=random.choice(SIZES),
            color=random.choice(COLORS),
            payment_method="upi" if random.random() < UPI_PROBABILITY else "cash",
            quantity=random.choices([1, 2, 3], weights=[0.80, 0.15, 0.05])[0],
            triggers_reprint=random.random() < REPRINT_PROBABILITY,
        ))
    return scenarios


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
class TestSaturdaySimulation:

    @pytest_asyncio.fixture(autouse=True)
    async def seed(self, db):
        """Seed a variant for every customer."""
        self.db = db
        self.variants = [await seed_variant(db) for _ in range(CUSTOMERS)]
        self.sessions = [await seed_kiosk_session(db) for _ in range(CUSTOMERS)]

    @pytest.mark.asyncio
    async def test_full_saturday_40_customers(self, client: AsyncClient):
        """
        End-to-end simulation of 40 customers across a Saturday.

        Each customer:
          1. Creates an order (simulates story + design already done)
          2. Staff picks it up (pending → printing)
          3. Staff records payment
          4. If reprint triggered: marks failed → reprinting → ready
             Otherwise: marks ready
          5. Staff marks collected (only possible after paid)

        Asserts:
          - All 40 orders reach 'collected'
          - All 40 have payment_status='paid'
          - Reprint scenarios went through 'failed' → 'reprinting' before 'ready'
          - End-of-day reconciliation totals match sum of individual orders
          - No duplicate short refs across the day
        """
        scenarios = build_saturday_scenarios()
        collected_refs: list[str] = []
        total_revenue_paise = 0

        # --- Phase 1: Place all orders ---
        async def place_order(s: CustomerScenario):
            payload = {
                "session_id": str(self.sessions[s.idx].id),
                "customer_name": s.name,
                "customer_phone": s.phone,
                "items": [{
                    "design_variant_id": str(self.variants[s.idx].id),
                    "product_id": "tshirt-crew",
                    "product_name": "Crew Neck",
                    "size": s.size,
                    "color": s.color,
                    "quantity": s.quantity,
                    "unit_price_paise": 79900,
                    "name_tag_text": s.name.split()[0],
                }],
            }
            headers = {"Idempotency-Key": str(uuid.uuid4())}
            r = await client.post("/api/v1/orders", json=payload, headers=headers)
            assert r.status_code == 201, f"Customer {s.idx} order failed: {r.text}"
            data = r.json()["order"]
            s.order_id = data["id"]
            s.short_ref = data["short_ref"]

        await asyncio.gather(*[place_order(s) for s in scenarios])

        # Verify all orders placed and refs unique
        refs = [s.short_ref for s in scenarios]
        assert len(set(refs)) == CUSTOMERS, (
            f"Duplicate short refs across simulation: {[r for r in refs if refs.count(r) > 1]}"
        )

        # --- Phase 2: Staff fulfilment loop (sequential, as a single press) ---
        for s in scenarios:
            oid = s.order_id

            # pending → printing
            r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "printing"})
            assert r.status_code == 200, f"printing transition failed for {s.short_ref}: {r.text}"

            # Record payment
            r = await client.patch(
                f"/api/v1/orders/{oid}/payment",
                json={"payment_method": s.payment_method},
            )
            assert r.status_code == 200, f"payment failed for {s.short_ref}: {r.text}"

            if s.triggers_reprint:
                # Simulate press failure
                r = await client.patch(
                    f"/api/v1/orders/{oid}/status",
                    json={"status": "failed", "staff_notes": "Film jam during press"},
                )
                assert r.status_code == 200, f"failed transition failed for {s.short_ref}: {r.text}"

                r = await client.patch(
                    f"/api/v1/orders/{oid}/status",
                    json={"status": "reprinting", "staff_notes": "Reprinting on fresh film"},
                )
                assert r.status_code == 200, f"reprinting transition failed for {s.short_ref}: {r.text}"

            # → ready
            r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "ready"})
            assert r.status_code == 200, f"ready transition failed for {s.short_ref}: {r.text}"

            # → collected
            r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "collected"})
            assert r.status_code == 200, f"collected transition failed for {s.short_ref}: {r.text}"

            s.final_status = "collected"
            order_data = r.json()["order"]
            total_revenue_paise += order_data["total_paise"]
            collected_refs.append(s.short_ref)

        # --- Phase 3: Assertions ---
        assert all(s.final_status == "collected" for s in scenarios), (
            f"Not all orders reached collected: {[s.short_ref for s in scenarios if s.final_status != 'collected']}"
        )

        # Reprint orders went through the correct path
        reprint_scenarios = [s for s in scenarios if s.triggers_reprint]
        for s in reprint_scenarios:
            r = await client.get(f"/api/v1/orders/{s.order_id}")
            data = r.json()["order"]
            assert data["reprint_count"] >= 1, (
                f"Order {s.short_ref} triggered reprint but reprint_count={data['reprint_count']}"
            )

        # --- Phase 4: End-of-day reconciliation ---
        r = await client.get(f"/api/v1/orders/reconciliation?date={date.today().isoformat()}")
        assert r.status_code == 200
        recon = r.json()

        assert recon["total_orders"] == CUSTOMERS, (
            f"Reconciliation total_orders={recon['total_orders']}, expected {CUSTOMERS}"
        )
        assert recon["paid_orders"] == CUSTOMERS, (
            f"Reconciliation paid_orders={recon['paid_orders']}, expected all {CUSTOMERS}"
        )
        assert recon["unpaid_orders"] == 0, (
            f"Reconciliation shows {recon['unpaid_orders']} unpaid orders — should be 0"
        )
        assert recon["grand_total_paise"] == total_revenue_paise, (
            f"Reconciliation revenue {recon['grand_total_paise']} ≠ "
            f"sum of orders {total_revenue_paise}"
        )

        upi_count = sum(1 for s in scenarios if s.payment_method == "upi")
        cash_count = CUSTOMERS - upi_count
        print(f"\n--- Saturday Simulation Complete ---")
        print(f"Orders: {CUSTOMERS}, Cash: {cash_count}, UPI: {upi_count}")
        print(f"Reprints: {len(reprint_scenarios)}")
        print(f"Revenue: ₹{total_revenue_paise / 100:.0f}")
        print(f"Refs: {collected_refs[:5]}…")

    @pytest.mark.asyncio
    async def test_cannot_collect_before_payment(self, client: AsyncClient):
        """
        An order in 'ready' state must not be collectable without payment.
        Asserts the payment gate in the status transition endpoint.
        """
        s = build_saturday_scenarios()[0]
        s.order_id = None

        payload = {
            "session_id": str(self.sessions[0].id),
            "customer_name": s.name,
            "customer_phone": s.phone,
            "items": [{
                "design_variant_id": str(self.variants[0].id),
                "product_id": "tshirt-crew",
                "product_name": "Crew Neck",
                "size": s.size,
                "color": s.color,
                "quantity": 1,
                "unit_price_paise": 79900,
                "name_tag_text": s.name.split()[0],
            }],
        }
        r = await client.post(
            "/api/v1/orders", json=payload,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        assert r.status_code == 201
        oid = r.json()["order"]["id"]

        # Walk to ready without paying
        for status in ("printing", "ready"):
            r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": status})
            assert r.status_code == 200

        # Attempt collect without payment — must be rejected
        r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "collected"})
        assert r.status_code == 409
        assert r.json()["detail"]["error"] == "payment_required_before_collection"

    @pytest.mark.asyncio
    async def test_mixed_payment_reconciliation(self, client: AsyncClient):
        """
        5 cash + 5 UPI orders.
        Reconciliation must split totals correctly between methods.
        """
        order_ids = []
        unit_price = 79900

        for i in range(10):
            payload = {
                "session_id": str(self.sessions[i].id),
                "customer_name": fake.name(),
                "customer_phone": fake.phone_number(),
                "items": [{
                    "design_variant_id": str(self.variants[i].id),
                    "product_id": "tshirt-crew",
                    "product_name": "Crew Neck",
                    "size": "M",
                    "color": "Black",
                    "quantity": 1,
                    "unit_price_paise": unit_price,
                    "name_tag_text": "Test",
                }],
            }
            r = await client.post(
                "/api/v1/orders", json=payload,
                headers={"Idempotency-Key": str(uuid.uuid4())}
            )
            assert r.status_code == 201
            order_ids.append(r.json()["order"]["id"])

        # Walk each to ready, then pay alternately cash/UPI
        for idx, oid in enumerate(order_ids):
            for status in ("printing", "ready"):
                await client.patch(f"/api/v1/orders/{oid}/status", json={"status": status})
            method = "cash" if idx < 5 else "upi"
            r = await client.patch(
                f"/api/v1/orders/{oid}/payment",
                json={"payment_method": method},
            )
            assert r.status_code == 200

        r = await client.get(f"/api/v1/orders/reconciliation?date={date.today().isoformat()}")
        recon = r.json()

        expected_cash = 5 * unit_price
        expected_upi  = 5 * unit_price

        assert recon["cash_total_paise"] >= expected_cash, (
            f"Cash total {recon['cash_total_paise']} < expected {expected_cash}"
        )
        assert recon["upi_total_paise"] >= expected_upi, (
            f"UPI total {recon['upi_total_paise']} < expected {expected_upi}"
        )
