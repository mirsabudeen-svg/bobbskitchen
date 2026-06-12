"""
Sprint 10 — Analytics Tests
Tests: event tracking (fire-and-forget safety), daily summary builder accuracy,
       API endpoints, product intelligence aggregation, hourly distribution.

Run: pytest tests/test_analytics.py -v --timeout=60
"""

import asyncio
import uuid
from datetime import date, datetime, timezone, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.models.analytics import AnalyticsDaily, AnalyticsEvent, EventType
from app.services.analytics import (
    get_daily_summaries,
    get_product_intelligence,
    get_today_live,
    rebuild_daily_summary,
    track,
    track_designs_generated,
    track_order_collected,
    track_order_paid,
    track_order_placed,
    track_order_ready,
    track_reprint,
    track_session_started,
    track_story_submitted,
    track_variant_generated,
    track_variant_selected,
    track_whatsapp_result,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Core track() — fire-and-forget safety
# ─────────────────────────────────────────────────────────────────────────────

class TestTrackFireAndForget:

    @pytest.mark.asyncio
    async def test_track_writes_event_row(self, db):
        sid = str(uuid.uuid4())
        await track(db, EventType.SESSION_STARTED, session_id=sid)

        from sqlalchemy import select
        result = await db.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.session_id == uuid.UUID(sid))
        )
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].event_type == EventType.SESSION_STARTED

    @pytest.mark.asyncio
    async def test_track_does_not_raise_on_db_error(self, db):
        """
        If the DB write fails, track() must silently log and return — never raise.
        Simulate by passing a closed/broken session.
        """
        from unittest.mock import AsyncMock, patch

        with patch.object(db, "add", side_effect=RuntimeError("DB exploded")):
            # Must not raise
            await track(db, EventType.ORDER_PLACED, order_id=str(uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_track_sets_correct_buckets(self, db):
        """hour_bucket and date_bucket must be derived from now(), not from caller."""
        from zoneinfo import ZoneInfo
        IST = ZoneInfo("Asia/Kolkata")

        sid = str(uuid.uuid4())
        await track(db, EventType.SESSION_STARTED, session_id=sid)

        from sqlalchemy import select
        result = await db.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.session_id == uuid.UUID(sid))
        )
        event = result.scalar_one()

        now_utc  = datetime.now(timezone.utc)
        now_ist  = now_utc.astimezone(IST)
        assert event.hour_bucket  == now_utc.hour
        assert event.date_bucket  == now_ist.date()

    @pytest.mark.asyncio
    async def test_all_convenience_wrappers_write_correct_event_type(self, db):
        """Each convenience wrapper must write the expected event_type."""
        sid  = str(uuid.uuid4())
        oid  = str(uuid.uuid4())
        vid  = str(uuid.uuid4())
        ref  = "B-001"
        now  = datetime.now(timezone.utc)

        await track_session_started(db, sid)
        await track_story_submitted(db, sid, 15, "test story")
        await track_designs_generated(db, sid, 4, 0, 3000, ["minimalist"], "fal-ai/flux")
        await track_variant_generated(db, sid, vid, "minimalist", "a prompt", True, 750)
        await track_variant_selected(db, sid, vid, "minimalist", 1)
        await track_order_placed(db, sid, oid, ref, "tshirt-crew", "M", "Black", 1, 79900, 60000)
        await track_order_paid(db, oid, ref, "cash", 79900)
        await track_order_ready(db, oid, ref, now - timedelta(minutes=8))
        await track_order_collected(db, oid, ref)
        await track_reprint(db, oid, ref, "Black", "tshirt-crew", "Film jam")
        await track_whatsapp_result(db, oid, ref, True, "en", None)

        from sqlalchemy import select
        result = await db.execute(select(AnalyticsEvent))
        all_events = result.scalars().all()
        event_types = {e.event_type for e in all_events}

        expected = {
            EventType.SESSION_STARTED,
            EventType.STORY_SUBMITTED,
            EventType.DESIGNS_GENERATED,
            EventType.STORY_TO_DESIGNS_MS,
            EventType.VARIANT_GENERATED,
            EventType.VARIANT_SELECTED,
            EventType.ORDER_PLACED,
            EventType.DESIGNS_TO_ORDER_MS,
            EventType.ORDER_PAID,
            EventType.ORDER_READY,
            EventType.ORDER_TO_READY_MS,
            EventType.ORDER_COLLECTED,
            EventType.REPRINT_TRIGGERED,
            EventType.WHATSAPP_SENT,
        }
        assert expected.issubset(event_types), (
            f"Missing event types: {expected - event_types}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Daily summary builder
# ─────────────────────────────────────────────────────────────────────────────

class TestDailySummaryBuilder:

    @pytest.fixture
    def target_date(self) -> date:
        return date.today()

    @pytest_asyncio.fixture
    async def seeded_day(self, db, target_date):
        """Seed a realistic day: 5 sessions, 4 stories, 3 orders, 1 reprint."""
        sessions = [str(uuid.uuid4()) for _ in range(5)]
        orders   = [str(uuid.uuid4()) for _ in range(3)]
        now      = datetime.now(timezone.utc)

        for sid in sessions:
            await track_session_started(db, sid)

        for sid in sessions[:4]:
            await track_story_submitted(db, sid, 12, "story " + sid[:4])
            await track_designs_generated(db, sid, 4, 0, 3000, ["minimalist", "bold"], "fal-ai/flux")

        for i, oid in enumerate(orders):
            sid = sessions[i]
            vid = str(uuid.uuid4())
            await track_variant_selected(db, sid, vid, "minimalist", 0)
            await track_order_placed(db, sid, oid, f"B-00{i+1}", "tshirt-crew",
                                     "M", "Black", 1, 79900, 60000)
            await track_order_paid(db, oid, f"B-00{i+1}", "cash", 79900)
            await track_order_ready(db, oid, f"B-00{i+1}", now - timedelta(minutes=7))
            await track_order_collected(db, oid, f"B-00{i+1}")

        # One reprint
        await track_reprint(db, orders[0], "B-001", "Black", "tshirt-crew", "Jam")
        await track_whatsapp_result(db, orders[0], "B-001", True, "en", None)
        await track_whatsapp_result(db, orders[1], "B-002", False, "ml", "twilio_21211")

        return {"sessions": sessions, "orders": orders}

    @pytest.mark.asyncio
    async def test_summary_counts_are_accurate(self, db, target_date, seeded_day):
        summary = await rebuild_daily_summary(db, target_date)

        assert summary.sessions_started  == 5
        assert summary.stories_submitted == 4
        assert summary.orders_placed     == 3
        assert summary.orders_collected  == 3
        assert summary.reprints          == 1
        assert summary.whatsapp_sent     == 1
        assert summary.whatsapp_failed   == 1

    @pytest.mark.asyncio
    async def test_summary_revenue_is_accurate(self, db, target_date, seeded_day):
        summary = await rebuild_daily_summary(db, target_date)
        # 3 orders × ₹799 = ₹2397 = 239700 paise
        assert summary.revenue_paise == 3 * 79900
        assert summary.cash_paise    == 3 * 79900

    @pytest.mark.asyncio
    async def test_summary_conversion_rates(self, db, target_date, seeded_day):
        summary = await rebuild_daily_summary(db, target_date)
        # 3 orders / 4 stories = 0.75
        assert abs(summary.story_to_order_rate - 0.75) < 0.01
        # 3 orders / 5 sessions = 0.60
        assert abs(summary.session_to_order_rate - 0.60) < 0.01

    @pytest.mark.asyncio
    async def test_summary_latency_fields_populated(self, db, target_date, seeded_day):
        summary = await rebuild_daily_summary(db, target_date)
        assert summary.avg_story_to_designs_ms is not None
        assert summary.avg_order_to_ready_ms   is not None
        assert summary.p95_order_to_ready_ms   is not None
        # avg ready time: ~7 minutes (420s) ± some tolerance
        assert 300_000 < summary.avg_order_to_ready_ms < 600_000

    @pytest.mark.asyncio
    async def test_summary_styles_populated(self, db, target_date, seeded_day):
        summary = await rebuild_daily_summary(db, target_date)
        assert summary.top_styles_by_selection is not None
        assert len(summary.top_styles_by_selection) > 0
        # minimalist was the selected style in all variants
        style_names = [s["style"] for s in summary.top_styles_by_selection]
        assert "minimalist" in style_names

    @pytest.mark.asyncio
    async def test_summary_is_idempotent(self, db, target_date, seeded_day):
        """Rebuilding twice must produce identical results — not double-count."""
        s1 = await rebuild_daily_summary(db, target_date)
        s2 = await rebuild_daily_summary(db, target_date)
        assert s1.orders_placed  == s2.orders_placed
        assert s1.revenue_paise  == s2.revenue_paise

    @pytest.mark.asyncio
    async def test_empty_day_produces_zero_summary(self, db):
        yesterday = date.today() - timedelta(days=1)
        summary   = await rebuild_daily_summary(db, yesterday)
        assert summary.orders_placed  == 0
        assert summary.revenue_paise  == 0
        assert summary.sessions_started == 0

    @pytest.mark.asyncio
    async def test_orders_by_hour_has_24_slots(self, db, target_date, seeded_day):
        summary = await rebuild_daily_summary(db, target_date)
        assert len(summary.orders_by_hour)  == 24
        assert len(summary.revenue_by_hour) == 24
        # At least one hour should have orders
        assert sum(summary.orders_by_hour) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 3. API endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyticsAPI:

    @pytest.mark.asyncio
    async def test_today_endpoint_returns_200(self, client: AsyncClient):
        r = await client.get("/api/v1/analytics/today")
        assert r.status_code == 200
        data = r.json()
        assert "orders_placed"   in data
        assert "orders_by_hour"  in data
        assert "funnel"          in data
        assert len(data["orders_by_hour"]) == 24

    @pytest.mark.asyncio
    async def test_daily_endpoint_default_14_days(self, client: AsyncClient):
        r = await client.get("/api/v1/analytics/daily")
        assert r.status_code == 200
        data = r.json()
        assert "summaries" in data
        assert "start"     in data
        assert "end"       in data

    @pytest.mark.asyncio
    async def test_daily_endpoint_custom_range(self, client: AsyncClient):
        today     = date.today().isoformat()
        last_week = (date.today() - timedelta(days=6)).isoformat()
        r = await client.get(f"/api/v1/analytics/daily?start={last_week}&end={today}")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_daily_endpoint_rejects_excessive_range(self, client: AsyncClient):
        start = (date.today() - timedelta(days=120)).isoformat()
        end   = date.today().isoformat()
        r = await client.get(f"/api/v1/analytics/daily?start={start}&end={end}")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_product_endpoint_returns_200(self, client: AsyncClient):
        r = await client.get("/api/v1/analytics/product")
        assert r.status_code == 200
        data = r.json()
        assert "styles"           in data
        assert "colors"           in data
        assert "products"         in data
        assert "reprint_analysis" in data

    @pytest.mark.asyncio
    async def test_funnel_endpoint_returns_200(self, client: AsyncClient):
        r = await client.get("/api/v1/analytics/funnel")
        assert r.status_code == 200
        data = r.json()
        assert "totals"           in data
        assert "drop_off"         in data
        assert "conversion_rates" in data

    @pytest.mark.asyncio
    async def test_hourly_endpoint_returns_24_slots(self, client: AsyncClient):
        r = await client.get("/api/v1/analytics/hourly")
        assert r.status_code == 200
        data = r.json()
        assert len(data["orders_by_hour"])  == 24
        assert len(data["revenue_by_hour"]) == 24
        assert "peak_hour_orders" in data

    @pytest.mark.asyncio
    async def test_rebuild_endpoint_triggers_aggregation(self, client: AsyncClient):
        today = date.today().isoformat()
        r = await client.post(f"/api/v1/analytics/rebuild?target_date={today}")
        assert r.status_code == 200
        data = r.json()
        assert data["rebuilt"] == today
        assert "orders_placed"  in data


# ─────────────────────────────────────────────────────────────────────────────
# 4. Product intelligence aggregation
# ─────────────────────────────────────────────────────────────────────────────

class TestProductIntelligence:

    @pytest.mark.asyncio
    async def test_style_selection_rate_computed_correctly(self, db):
        today = date.today()
        sid1  = str(uuid.uuid4())
        sid2  = str(uuid.uuid4())

        # Generate 4 minimalist variants, select 2
        for sid in [sid1, sid2]:
            await track_designs_generated(db, sid, 4, 0, 3000, ["minimalist"], "fal-ai/flux")
            for i in range(2):
                await track_variant_generated(db, sid, str(uuid.uuid4()),
                                              "minimalist", "p", True, 750)

        await track_variant_selected(db, sid1, str(uuid.uuid4()), "minimalist", 0)
        await track_variant_selected(db, sid2, str(uuid.uuid4()), "minimalist", 1)

        summary = await rebuild_daily_summary(db, today)
        pi = await get_product_intelligence(db, today, today)

        minimalist = next((s for s in pi["styles"] if s["style"] == "minimalist"), None)
        assert minimalist is not None
        assert minimalist["selected"] == 2
        assert minimalist["selection_rate"] > 0

    @pytest.mark.asyncio
    async def test_reprint_analysis_identifies_high_reprint_color(self, db):
        today = date.today()
        oid   = str(uuid.uuid4())

        # Black gets 2 reprints, White gets 0
        await track_order_placed(db, str(uuid.uuid4()), oid, "B-001",
                                 "tshirt-crew", "M", "Black", 1, 79900, 60000)
        await track_reprint(db, oid, "B-001", "Black", "tshirt-crew", "Jam")
        await track_reprint(db, oid, "B-001", "Black", "tshirt-crew", "Scorched")

        oid2 = str(uuid.uuid4())
        await track_order_placed(db, str(uuid.uuid4()), oid2, "B-002",
                                 "tshirt-crew", "M", "White", 1, 79900, 60000)

        await rebuild_daily_summary(db, today)
        pi = await get_product_intelligence(db, today, today)

        assert "Black" in pi["reprint_analysis"]
        assert pi["reprint_analysis"]["Black"]["reprints"] == 2
        assert pi["reprint_analysis"]["Black"]["reprint_rate"] > 0

        # White has no reprints
        if "White" in pi["reprint_analysis"]:
            assert pi["reprint_analysis"]["White"]["reprints"] == 0
