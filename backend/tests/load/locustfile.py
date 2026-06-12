"""
Sprint 8 — Locust Sustained Load Test
Simulates a realistic Saturday van day: concurrent kiosk sessions,
order creation, and staff status updates at realistic arrival rates.

Install: pip install locust faker
Run:     locust -f tests/load/locustfile.py --host http://localhost:8000
         --users 10 --spawn-rate 2 --run-time 5m --headless
         --html reports/locust_report.html

Or open the Locust web UI:
         locust -f tests/load/locustfile.py --host http://localhost:8000
         then visit http://localhost:8089
"""

import random
import uuid
from faker import Faker

from locust import HttpUser, TaskSet, between, task, events

fake = Faker("en_IN")

SIZES   = ["S", "M", "L", "XL", "XXL"]
COLORS  = ["Black", "White", "Navy", "Maroon", "Olive"]


# ---------------------------------------------------------------------------
# Customer kiosk user — simulates the customer-facing tablet
# ---------------------------------------------------------------------------
class CustomerKioskTasks(TaskSet):

    def on_start(self):
        """Create a new session when this virtual user starts."""
        self.session_id  = None
        self.variant_id  = None
        self.order_id    = None
        self._create_session()

    def _create_session(self):
        with self.client.post(
            "/api/v1/sessions",
            json={"device_id": str(uuid.uuid4()), "customer_name": fake.name()},
            name="/api/v1/sessions [POST]",
            catch_response=True,
        ) as r:
            if r.status_code == 201:
                self.session_id = r.json().get("session", {}).get("id")
            else:
                r.failure(f"Session create failed: {r.status_code}")

    @task(3)
    def create_order(self):
        """Place an order — the most common customer action."""
        if not self.session_id:
            self._create_session()
            return

        if not self.variant_id:
            # Seed a variant via the debug endpoint for load testing
            with self.client.post(
                "/api/v1/debug/variants",
                json={
                    "session_id": self.session_id,
                    "image_url": "https://cdn.bobb.ai/load-test.png",
                    "prompt": "load test",
                    "style": "test",
                },
                name="/api/v1/debug/variants [POST]",
                catch_response=True,
            ) as r:
                if r.status_code == 201:
                    self.variant_id = r.json().get("variant", {}).get("id")
                else:
                    r.failure(f"Variant seed failed: {r.status_code}")
                    return

        payload = {
            "session_id": self.session_id,
            "customer_name": fake.name(),
            "customer_phone": fake.phone_number(),
            "items": [{
                "design_variant_id": self.variant_id,
                "product_id": "tshirt-crew",
                "product_name": "Crew Neck",
                "size": random.choice(SIZES),
                "color": random.choice(COLORS),
                "quantity": 1,
                "unit_price_paise": 79900,
                "name_tag_text": fake.first_name(),
            }],
        }
        idem_key = str(uuid.uuid4())
        with self.client.post(
            "/api/v1/orders",
            json=payload,
            headers={"Idempotency-Key": idem_key},
            name="/api/v1/orders [POST]",
            catch_response=True,
        ) as r:
            if r.status_code == 201:
                self.order_id = r.json().get("order", {}).get("id")
                self.variant_id = None  # reset for next customer
                self.session_id = None  # simulate kiosk reset after order
            else:
                r.failure(f"Order create failed: {r.status_code} — {r.text[:200]}")

    @task(1)
    def get_order_status(self):
        """Customer checks their order status (less frequent)."""
        if self.order_id:
            self.client.get(
                f"/api/v1/orders/{self.order_id}",
                name="/api/v1/orders/{id} [GET]",
            )

    @task(1)
    def reset_session(self):
        """Simulate a kiosk idle timeout / customer abandonment."""
        if self.session_id:
            self.client.post(
                f"/api/v1/sessions/{self.session_id}/abandon",
                name="/api/v1/sessions/{id}/abandon [POST]",
            )
        self.session_id = None
        self.variant_id = None
        self.order_id   = None
        self._create_session()


# ---------------------------------------------------------------------------
# Staff operator user — simulates the counter tablet
# ---------------------------------------------------------------------------
class StaffOperatorTasks(TaskSet):

    def on_start(self):
        self.pending_order_ids: list[str] = []

    @task(4)
    def poll_queue(self):
        """Staff checks the queue for pending orders."""
        with self.client.get(
            "/api/v1/orders?status=pending",
            name="/api/v1/orders?status=pending [GET]",
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                orders = r.json().get("orders", [])
                self.pending_order_ids = [o["id"] for o in orders]
            else:
                r.failure(f"Queue fetch failed: {r.status_code}")

    @task(3)
    def advance_order_to_printing(self):
        """Pick the oldest pending order and start printing."""
        if not self.pending_order_ids:
            return
        oid = self.pending_order_ids.pop(0)
        with self.client.patch(
            f"/api/v1/orders/{oid}/status",
            json={"status": "printing"},
            name="/api/v1/orders/{id}/status→printing [PATCH]",
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 409):
                r.failure(f"Status update failed: {r.status_code}")

    @task(2)
    def record_payment(self):
        """Record cash or UPI payment for a random order."""
        with self.client.get(
            "/api/v1/orders?status=printing",
            name="/api/v1/orders?status=printing [GET]",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                return
            orders = r.json().get("orders", [])
            if not orders:
                return
            oid    = random.choice(orders)["id"]
            method = random.choice(["cash", "upi"])

        self.client.patch(
            f"/api/v1/orders/{oid}/payment",
            json={"payment_method": method},
            name="/api/v1/orders/{id}/payment [PATCH]",
        )

    @task(2)
    def mark_ready(self):
        """Mark a printing order as ready."""
        with self.client.get(
            "/api/v1/orders?status=printing",
            name="/api/v1/orders?status=printing [GET]",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                return
            orders = r.json().get("orders", [])
            if not orders:
                return
            oid = random.choice(orders)["id"]

        self.client.patch(
            f"/api/v1/orders/{oid}/status",
            json={"status": "ready"},
            name="/api/v1/orders/{id}/status→ready [PATCH]",
        )

    @task(1)
    def lookup_by_ref(self):
        """Simulate staff looking up an order by short ref."""
        ref = f"B-{random.randint(1, 60):03d}"
        self.client.get(
            f"/api/v1/orders/lookup?ref={ref}",
            name="/api/v1/orders/lookup [GET]",
        )


# ---------------------------------------------------------------------------
# User classes — Locust spawns these
# ---------------------------------------------------------------------------
class KioskUser(HttpUser):
    """Simulates a customer-facing kiosk tablet."""
    tasks       = [CustomerKioskTasks]
    wait_time   = between(2, 8)   # customers take 2–8 seconds between actions
    weight      = 3               # 3 kiosk users for every 1 staff user


class StaffUser(HttpUser):
    """Simulates the staff counter tablet."""
    tasks       = [StaffOperatorTasks]
    wait_time   = between(1, 4)   # staff acts faster
    weight      = 1


# ---------------------------------------------------------------------------
# Custom event hooks — print summary on test end
# ---------------------------------------------------------------------------
@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    stats = environment.stats
    total = stats.total
    print("\n" + "="*60)
    print("SPRINT 8 LOAD TEST SUMMARY")
    print("="*60)
    print(f"Total requests:    {total.num_requests}")
    print(f"Failures:          {total.num_failures}")
    print(f"Failure rate:      {total.fail_ratio * 100:.1f}%")
    print(f"Median response:   {total.median_response_time:.0f}ms")
    print(f"p95 response:      {total.get_response_time_percentile(0.95):.0f}ms")
    print(f"p99 response:      {total.get_response_time_percentile(0.99):.0f}ms")
    print(f"RPS:               {total.current_rps:.1f}")
    print("="*60)

    # Fail CI if error rate exceeds 1%
    if total.fail_ratio > 0.01:
        environment.process_exit_code = 1
        print(f"❌ FAIL — error rate {total.fail_ratio*100:.1f}% exceeds 1% threshold")
    else:
        print(f"✅ PASS — error rate {total.fail_ratio*100:.1f}% within threshold")
