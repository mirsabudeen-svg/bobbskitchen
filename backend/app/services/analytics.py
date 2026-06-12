"""
backend/app/services/analytics.py

Sprint 10 — Analytics instrumentation service.

All public functions are async and fire-and-forget safe:
  - track() is the primary call point — one line per event in the caller
  - rebuild_daily_summary() is called by the nightly scheduler
  - get_dashboard_data() serves the /analytics API endpoints

Architecture note:
  Events are written in background tasks (FastAPI BackgroundTasks or
  asyncio.create_task). A failure here must never propagate to the caller.
  Every public function wraps its body in try/except and logs errors silently.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsDaily, AnalyticsEvent, EventType

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")  # UTC+5:30 — van operates in Kerala


# ─────────────────────────────────────────────────────────────────────────────
# Core tracking function
# ─────────────────────────────────────────────────────────────────────────────

async def track(
    db: AsyncSession,
    event_type: str,
    *,
    session_id: Optional[str] = None,
    order_id: Optional[str] = None,
    short_ref: Optional[str] = None,
    variant_id: Optional[str] = None,
    product_id: Optional[str] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    value_int: Optional[int] = None,
    value_float: Optional[float] = None,
    payload: Optional[dict] = None,
) -> None:
    """
    Write a single analytics event. Fire-and-forget safe.

    Call pattern in API handlers:
        asyncio.create_task(track(db, EventType.ORDER_PLACED, order_id=oid, ...))

    Never await this directly in a request handler — use create_task or
    FastAPI BackgroundTasks so analytics never add to response latency.
    """
    try:
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc.astimezone(IST)

        import uuid as _uuid
        event = AnalyticsEvent(
            id=_uuid.uuid4(),
            event_type=event_type,
            occurred_at=now_utc,
            hour_bucket=now_utc.hour,
            date_bucket=now_ist.date(),  # IST date for daily grouping
            session_id=_uuid.UUID(session_id) if session_id else None,
            order_id=_uuid.UUID(order_id) if order_id else None,
            short_ref=short_ref,
            variant_id=_uuid.UUID(variant_id) if variant_id else None,
            product_id=product_id,
            size=size,
            color=color,
            value_int=value_int,
            value_float=value_float,
            payload=payload,
        )
        db.add(event)
        await db.commit()

    except Exception as exc:
        logger.error(
            "Analytics track failed — event dropped",
            extra={"event_type": event_type, "error": str(exc)},
            exc_info=False,  # don't spam tracebacks for analytics failures
        )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience wrappers — one per major event to avoid magic strings in callers
# ─────────────────────────────────────────────────────────────────────────────

async def track_session_started(db: AsyncSession, session_id: str) -> None:
    await track(db, EventType.SESSION_STARTED, session_id=session_id)


async def track_story_submitted(
    db: AsyncSession,
    session_id: str,
    story_word_count: int,
    story_digest: str,  # first 100 chars — never full PII text
) -> None:
    await track(
        db, EventType.STORY_SUBMITTED,
        session_id=session_id,
        value_int=story_word_count,
        payload={"story_digest": story_digest[:100]},
    )


async def track_designs_generated(
    db: AsyncSession,
    session_id: str,
    succeeded: int,
    failed: int,
    latency_ms: int,
    styles: list[str],
    fal_model: str,
) -> None:
    await track(
        db, EventType.DESIGNS_GENERATED,
        session_id=session_id,
        value_int=latency_ms,
        payload={
            "succeeded": succeeded,
            "failed": failed,
            "styles": styles,
            "fal_model": fal_model,
        },
    )
    # Also record the story→designs latency as its own event for p95 queries
    await track(
        db, EventType.STORY_TO_DESIGNS_MS,
        session_id=session_id,
        value_int=latency_ms,
    )


async def track_variant_generated(
    db: AsyncSession,
    session_id: str,
    variant_id: str,
    style: str,
    prompt_digest: str,
    success: bool,
    latency_ms: int,
) -> None:
    await track(
        db, EventType.VARIANT_GENERATED,
        session_id=session_id,
        variant_id=variant_id,
        value_int=latency_ms,
        payload={
            "style": style,
            "prompt_digest": prompt_digest[:100],
            "success": success,
        },
    )


async def track_variant_selected(
    db: AsyncSession,
    session_id: str,
    variant_id: str,
    style: str,
    position: int,  # 0–3: which of the 4 variants was chosen
) -> None:
    await track(
        db, EventType.VARIANT_SELECTED,
        session_id=session_id,
        variant_id=variant_id,
        value_int=position,
        payload={"style": style},
    )


async def track_order_placed(
    db: AsyncSession,
    session_id: str,
    order_id: str,
    short_ref: str,
    product_id: str,
    size: str,
    color: str,
    quantity: int,
    total_paise: int,
    story_to_order_ms: int,
) -> None:
    await track(
        db, EventType.ORDER_PLACED,
        session_id=session_id,
        order_id=order_id,
        short_ref=short_ref,
        product_id=product_id,
        size=size,
        color=color,
        value_int=total_paise,
        payload={
            "quantity": quantity,
            "story_to_order_ms": story_to_order_ms,
        },
    )
    await track(
        db, EventType.DESIGNS_TO_ORDER_MS,
        session_id=session_id,
        order_id=order_id,
        value_int=story_to_order_ms,
    )


async def track_order_paid(
    db: AsyncSession,
    order_id: str,
    short_ref: str,
    payment_method: str,
    amount_paise: int,
) -> None:
    await track(
        db, EventType.ORDER_PAID,
        order_id=order_id,
        short_ref=short_ref,
        value_int=amount_paise,
        payload={"payment_method": payment_method},
    )


async def track_order_ready(
    db: AsyncSession,
    order_id: str,
    short_ref: str,
    order_placed_at: datetime,
) -> None:
    order_to_ready_ms = int(
        (datetime.now(timezone.utc) - order_placed_at).total_seconds() * 1000
    )
    await track(
        db, EventType.ORDER_READY,
        order_id=order_id,
        short_ref=short_ref,
        value_int=order_to_ready_ms,
    )
    await track(
        db, EventType.ORDER_TO_READY_MS,
        order_id=order_id,
        value_int=order_to_ready_ms,
    )


async def track_order_collected(
    db: AsyncSession,
    order_id: str,
    short_ref: str,
) -> None:
    await track(db, EventType.ORDER_COLLECTED, order_id=order_id, short_ref=short_ref)


async def track_session_abandoned(db: AsyncSession, session_id: str) -> None:
    await track(db, EventType.SESSION_ABANDONED, session_id=session_id)


async def track_reprint(
    db: AsyncSession,
    order_id: str,
    short_ref: str,
    color: str,
    product_id: str,
    staff_notes: Optional[str],
) -> None:
    await track(
        db, EventType.REPRINT_TRIGGERED,
        order_id=order_id,
        short_ref=short_ref,
        color=color,
        product_id=product_id,
        payload={"staff_notes": (staff_notes or "")[:200]},
    )


async def track_whatsapp_result(
    db: AsyncSession,
    order_id: str,
    short_ref: str,
    success: bool,
    language: str,
    error: Optional[str],
) -> None:
    await track(
        db, EventType.WHATSAPP_SENT,
        order_id=order_id,
        short_ref=short_ref,
        value_int=1 if success else 0,
        payload={"language": language, "success": success, "error": error},
    )


async def track_fal_result(
    db: AsyncSession,
    session_id: str,
    succeeded: int,
    failed: int,
    total_latency_ms: int,
    model: str,
) -> None:
    await track(
        db, EventType.FAL_GENERATION_RESULT,
        session_id=session_id,
        value_int=total_latency_ms,
        payload={
            "succeeded": succeeded,
            "failed": failed,
            "model": model,
            "success_rate": succeeded / max(succeeded + failed, 1),
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Daily summary builder — called nightly by the scheduler
# ─────────────────────────────────────────────────────────────────────────────

async def rebuild_daily_summary(db: AsyncSession, target_date: date) -> AnalyticsDaily:
    """
    Compute and upsert the AnalyticsDaily row for `target_date`.
    Idempotent — safe to run multiple times for the same date.
    Typically called at 23:59 IST by the scheduler, and again at 00:30
    to catch any late-arriving events.
    """
    try:
        # Delete existing row for the date (upsert via delete+insert)
        existing = await db.execute(
            select(AnalyticsDaily).where(AnalyticsDaily.summary_date == target_date)
        )
        existing_row = existing.scalar_one_or_none()
        if existing_row:
            await db.delete(existing_row)
            await db.flush()

        # Fetch all events for the target date
        events_result = await db.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.date_bucket == target_date)
        )
        events: list[AnalyticsEvent] = events_result.scalars().all()

        def by_type(t: str) -> list[AnalyticsEvent]:
            return [e for e in events if e.event_type == t]

        def p95(values: list[int]) -> Optional[int]:
            if not values:
                return None
            s = sorted(values)
            return s[int(0.95 * len(s))]

        def avg(values: list[int]) -> Optional[int]:
            return int(sum(values) / len(values)) if values else None

        # ── Volume ────────────────────────────────────────────────────────────
        sessions_started    = len(by_type(EventType.SESSION_STARTED))
        sessions_abandoned  = len(by_type(EventType.SESSION_ABANDONED))
        stories_submitted   = len(by_type(EventType.STORY_SUBMITTED))
        design_jobs         = by_type(EventType.DESIGNS_GENERATED)
        design_jobs_run     = len(design_jobs)
        variants_all        = by_type(EventType.VARIANT_GENERATED)
        variants_generated  = sum(1 for e in variants_all if e.payload and e.payload.get("success"))
        variants_failed     = sum(1 for e in variants_all if e.payload and not e.payload.get("success"))
        orders_placed       = len(by_type(EventType.ORDER_PLACED))
        orders_collected    = len(by_type(EventType.ORDER_COLLECTED))
        reprints            = len(by_type(EventType.REPRINT_TRIGGERED))
        wa_events           = by_type(EventType.WHATSAPP_SENT)
        whatsapp_sent       = sum(1 for e in wa_events if e.value_int == 1)
        whatsapp_failed     = sum(1 for e in wa_events if e.value_int == 0)

        # ── Revenue ───────────────────────────────────────────────────────────
        paid_events   = by_type(EventType.ORDER_PAID)
        revenue_paise = sum(e.value_int or 0 for e in paid_events)
        cash_paise    = sum(
            e.value_int or 0 for e in paid_events
            if e.payload and e.payload.get("payment_method") == "cash"
        )
        upi_paise     = sum(
            e.value_int or 0 for e in paid_events
            if e.payload and e.payload.get("payment_method") == "upi"
        )
        avg_order_value = revenue_paise // max(orders_placed, 1)

        # ── Timing ────────────────────────────────────────────────────────────
        s2d_latencies = [e.value_int for e in by_type(EventType.STORY_TO_DESIGNS_MS) if e.value_int]
        o2r_latencies = [e.value_int for e in by_type(EventType.ORDER_TO_READY_MS) if e.value_int]

        # ── Funnel rates ──────────────────────────────────────────────────────
        story_to_order_rate   = orders_placed / max(stories_submitted, 1)
        session_to_order_rate = orders_placed / max(sessions_started, 1)
        variants_selected     = len(by_type(EventType.VARIANT_SELECTED))
        variant_selection_rate = variants_selected / max(variants_generated, 1)

        # ── Product intelligence: styles ──────────────────────────────────────
        from collections import Counter, defaultdict

        style_generated: Counter = Counter()
        style_selected:  Counter = Counter()

        for e in variants_all:
            style = e.payload.get("style") if e.payload else None
            if style and e.payload.get("success"):
                style_generated[style] += 1

        for e in by_type(EventType.VARIANT_SELECTED):
            style = e.payload.get("style") if e.payload else None
            if style:
                style_selected[style] += 1

        top_styles = [
            {
                "style": style,
                "generated": style_generated.get(style, 0),
                "selected": style_selected.get(style, 0),
                "selection_rate": round(
                    style_selected.get(style, 0) / max(style_generated.get(style, 1), 1), 3
                ),
            }
            for style in sorted(
                set(list(style_generated.keys()) + list(style_selected.keys())),
                key=lambda s: style_selected.get(s, 0),
                reverse=True,
            )
        ][:10]

        # ── Product intelligence: size + color ────────────────────────────────
        order_events = by_type(EventType.ORDER_PLACED)

        size_counter:  Counter = Counter()
        color_counter: Counter = Counter()
        product_size:  Counter = Counter()
        color_reprint: defaultdict = defaultdict(lambda: {"orders": 0, "reprints": 0})

        for e in order_events:
            if e.size:
                size_counter[e.size] += 1
            if e.color:
                color_counter[e.color] += 1
            if e.product_id and e.size:
                product_size[f"{e.product_id}:{e.size}"] += 1
            if e.color:
                color_reprint[e.color]["orders"] += 1

        for e in by_type(EventType.REPRINT_TRIGGERED):
            if e.color:
                color_reprint[e.color]["reprints"] += 1

        top_products = [
            {"product_size": k, "count": v}
            for k, v in product_size.most_common(10)
        ]

        color_dist = [
            {"color": c, "count": color_counter[c]}
            for c in color_counter.most_common()
        ]

        reprint_by_color = {
            color: {
                "orders": data["orders"],
                "reprints": data["reprints"],
                "reprint_rate": round(data["reprints"] / max(data["orders"], 1), 3),
            }
            for color, data in color_reprint.items()
        }

        # ── Hour-of-day distribution ───────────────────────────────────────────
        orders_by_hour  = [0] * 24
        revenue_by_hour = [0] * 24
        for e in order_events:
            orders_by_hour[e.hour_bucket] += 1
        for e in paid_events:
            revenue_by_hour[e.hour_bucket] += e.value_int or 0

        # ── Assemble and save ─────────────────────────────────────────────────
        import uuid as _uuid
        summary = AnalyticsDaily(
            id=_uuid.uuid4(),
            summary_date=target_date,
            sessions_started=sessions_started,
            sessions_abandoned=sessions_abandoned,
            stories_submitted=stories_submitted,
            design_jobs_run=design_jobs_run,
            variants_generated=variants_generated,
            variants_failed=variants_failed,
            orders_placed=orders_placed,
            orders_collected=orders_collected,
            reprints=reprints,
            whatsapp_sent=whatsapp_sent,
            whatsapp_failed=whatsapp_failed,
            revenue_paise=revenue_paise,
            cash_paise=cash_paise,
            upi_paise=upi_paise,
            avg_order_value_paise=avg_order_value,
            avg_story_to_designs_ms=avg(s2d_latencies),
            p95_story_to_designs_ms=p95(s2d_latencies),
            avg_order_to_ready_ms=avg(o2r_latencies),
            p95_order_to_ready_ms=p95(o2r_latencies),
            story_to_order_rate=round(story_to_order_rate, 3),
            session_to_order_rate=round(session_to_order_rate, 3),
            variant_selection_rate=round(variant_selection_rate, 3),
            top_styles_by_selection=top_styles,
            top_products_by_size=top_products,
            color_distribution=color_dist,
            reprint_rate_by_color=reprint_by_color,
            orders_by_hour=orders_by_hour,
            revenue_by_hour=revenue_by_hour,
        )
        db.add(summary)
        await db.commit()
        await db.refresh(summary)

        logger.info(
            "Daily summary rebuilt",
            extra={
                "date": target_date.isoformat(),
                "orders": orders_placed,
                "revenue_paise": revenue_paise,
            },
        )
        return summary

    except Exception as exc:
        logger.exception("Daily summary rebuild failed", extra={"date": str(target_date)})
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard data fetchers — called by the API endpoints
# ─────────────────────────────────────────────────────────────────────────────

async def get_daily_summaries(
    db: AsyncSession,
    start_date: date,
    end_date: date,
) -> list[AnalyticsDaily]:
    """Return daily summaries for a date range, newest first."""
    result = await db.execute(
        select(AnalyticsDaily)
        .where(AnalyticsDaily.summary_date >= start_date)
        .where(AnalyticsDaily.summary_date <= end_date)
        .order_by(AnalyticsDaily.summary_date.desc())
    )
    return result.scalars().all()


async def get_today_live(db: AsyncSession) -> dict:
    """
    Live today stats — reads directly from analytics_events (not the daily summary)
    so the dashboard shows real-time data before the nightly aggregation runs.
    """
    today_ist = datetime.now(IST).date()

    result = await db.execute(
        select(AnalyticsEvent).where(AnalyticsEvent.date_bucket == today_ist)
    )
    events = result.scalars().all()

    def count(t: str) -> int:
        return sum(1 for e in events if e.event_type == t)

    order_events = [e for e in events if e.event_type == EventType.ORDER_PLACED]
    paid_events  = [e for e in events if e.event_type == EventType.ORDER_PAID]

    orders_by_hour = [0] * 24
    for e in order_events:
        orders_by_hour[e.hour_bucket] += 1

    o2r = [e.value_int for e in events if e.event_type == EventType.ORDER_TO_READY_MS and e.value_int]

    return {
        "date": today_ist.isoformat(),
        "live": True,
        "sessions_started":    count(EventType.SESSION_STARTED),
        "stories_submitted":   count(EventType.STORY_SUBMITTED),
        "orders_placed":       count(EventType.ORDER_PLACED),
        "orders_collected":    count(EventType.ORDER_COLLECTED),
        "revenue_paise":       sum(e.value_int or 0 for e in paid_events),
        "reprints":            count(EventType.REPRINT_TRIGGERED),
        "whatsapp_sent":       sum(1 for e in events
                                   if e.event_type == EventType.WHATSAPP_SENT and e.value_int == 1),
        "orders_by_hour":      orders_by_hour,
        "avg_order_to_ready_ms": int(sum(o2r) / len(o2r)) if o2r else None,
        "funnel": {
            "sessions":   count(EventType.SESSION_STARTED),
            "stories":    count(EventType.STORY_SUBMITTED),
            "selections": count(EventType.VARIANT_SELECTED),
            "orders":     count(EventType.ORDER_PLACED),
            "collected":  count(EventType.ORDER_COLLECTED),
        },
    }


async def get_product_intelligence(
    db: AsyncSession,
    start_date: date,
    end_date: date,
) -> dict:
    """
    Aggregate product intelligence across a date range from the daily summaries.
    Returns style performance, size/color breakdown, reprint analysis.
    """
    summaries = await get_daily_summaries(db, start_date, end_date)

    from collections import defaultdict, Counter

    style_agg:   defaultdict = defaultdict(lambda: {"generated": 0, "selected": 0})
    color_agg:   Counter = Counter()
    product_agg: Counter = Counter()
    reprint_agg: defaultdict = defaultdict(lambda: {"orders": 0, "reprints": 0})

    for s in summaries:
        if s.top_styles_by_selection:
            for item in s.top_styles_by_selection:
                style_agg[item["style"]]["generated"] += item.get("generated", 0)
                style_agg[item["style"]]["selected"]  += item.get("selected", 0)
        if s.color_distribution:
            for item in s.color_distribution:
                color_agg[item["color"]] += item.get("count", 0)
        if s.top_products_by_size:
            for item in s.top_products_by_size:
                product_agg[item["product_size"]] += item.get("count", 0)
        if s.reprint_rate_by_color:
            for color, data in s.reprint_rate_by_color.items():
                reprint_agg[color]["orders"]   += data.get("orders", 0)
                reprint_agg[color]["reprints"] += data.get("reprints", 0)

    styles = sorted(
        [
            {
                "style": style,
                "generated": data["generated"],
                "selected": data["selected"],
                "selection_rate": round(
                    data["selected"] / max(data["generated"], 1), 3
                ),
            }
            for style, data in style_agg.items()
        ],
        key=lambda x: x["selection_rate"],
        reverse=True,
    )

    colors = [
        {"color": c, "count": n} for c, n in color_agg.most_common()
    ]

    products = [
        {"product_size": k, "count": v} for k, v in product_agg.most_common(10)
    ]

    reprint_analysis = {
        color: {
            "orders":       data["orders"],
            "reprints":     data["reprints"],
            "reprint_rate": round(data["reprints"] / max(data["orders"], 1), 3),
        }
        for color, data in sorted(
            reprint_agg.items(),
            key=lambda x: x[1]["reprints"] / max(x[1]["orders"], 1),
            reverse=True,
        )
    }

    return {
        "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "styles": styles,
        "colors": colors,
        "products": products,
        "reprint_analysis": reprint_analysis,
    }
