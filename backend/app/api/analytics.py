"""Analytics API — Sprint 10.

GET  /api/v1/analytics/today    — live today stats
GET  /api/v1/analytics/daily    — daily summaries (default last 14 days)
GET  /api/v1/analytics/product  — style/size/colour/reprint intelligence
GET  /api/v1/analytics/funnel   — conversion funnel
GET  /api/v1/analytics/hourly   — hour-of-day distribution
POST /api/v1/analytics/rebuild  — manual daily summary rebuild (staff)
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.services.analytics import (
    get_daily_summaries,
    get_product_intelligence,
    get_today_live,
    rebuild_daily_summary,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

DEFAULT_DAYS = 14
MAX_DAYS = 90


def _parse_range(
    start: Optional[date],
    end: Optional[date],
    days: int,
) -> tuple[date, date]:
    end_date = end or date.today()
    start_date = start or (end_date - timedelta(days=days - 1))
    if (end_date - start_date).days > MAX_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Date range cannot exceed {MAX_DAYS} days",
        )
    return start_date, end_date


@router.get("/today")
async def today_live(db: AsyncSession = Depends(get_db)):
    """Live today stats — reads from analytics_events, not the nightly summary."""
    return await get_today_live(db)


@router.get("/daily")
async def daily_summaries(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS),
    db: AsyncSession = Depends(get_db),
):
    """Pre-aggregated daily summaries. Default: last 14 days."""
    start_date, end_date = _parse_range(start, end, days)
    summaries = await get_daily_summaries(db, start_date, end_date)
    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "days": len(summaries),
        "summaries": [_serialise_daily(s) for s in summaries],
    }


def _serialise_daily(s) -> dict:
    return {
        "date": s.summary_date.isoformat(),
        "sessions_started": s.sessions_started,
        "sessions_abandoned": s.sessions_abandoned,
        "stories_submitted": s.stories_submitted,
        "design_jobs_run": s.design_jobs_run,
        "variants_generated": s.variants_generated,
        "variants_failed": s.variants_failed,
        "orders_placed": s.orders_placed,
        "orders_collected": s.orders_collected,
        "reprints": s.reprints,
        "whatsapp_sent": s.whatsapp_sent,
        "whatsapp_failed": s.whatsapp_failed,
        "revenue_paise": s.revenue_paise,
        "cash_paise": s.cash_paise,
        "upi_paise": s.upi_paise,
        "avg_order_value_paise": s.avg_order_value_paise,
        "avg_story_to_designs_ms": s.avg_story_to_designs_ms,
        "p95_story_to_designs_ms": s.p95_story_to_designs_ms,
        "avg_order_to_ready_ms": s.avg_order_to_ready_ms,
        "p95_order_to_ready_ms": s.p95_order_to_ready_ms,
        "story_to_order_rate": s.story_to_order_rate,
        "session_to_order_rate": s.session_to_order_rate,
        "variant_selection_rate": s.variant_selection_rate,
        "orders_by_hour": s.orders_by_hour,
        "revenue_by_hour": s.revenue_by_hour,
    }


@router.get("/product")
async def product_intelligence(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS),
    db: AsyncSession = Depends(get_db),
):
    """Style performance, size/colour distribution, reprint rate by colour."""
    start_date, end_date = _parse_range(start, end, days)
    return await get_product_intelligence(db, start_date, end_date)


@router.get("/funnel")
async def conversion_funnel(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated conversion funnel with drop-off rates."""
    start_date, end_date = _parse_range(start, end, days)
    summaries = await get_daily_summaries(db, start_date, end_date)

    totals = {
        "sessions": sum(s.sessions_started for s in summaries),
        "stories": sum(s.stories_submitted for s in summaries),
        "orders": sum(s.orders_placed for s in summaries),
        "collected": sum(s.orders_collected for s in summaries),
    }

    def drop_off(a: int, b: int) -> Optional[float]:
        if a == 0:
            return None
        return round(1 - b / a, 3)

    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "totals": totals,
        "drop_off": {
            "session_to_story": drop_off(totals["sessions"], totals["stories"]),
            "story_to_order": drop_off(totals["stories"], totals["orders"]),
            "order_to_collected": drop_off(totals["orders"], totals["collected"]),
            "session_to_order": drop_off(totals["sessions"], totals["orders"]),
        },
        "conversion_rates": {
            "story_to_order": round(totals["orders"] / max(totals["stories"], 1), 3),
            "session_to_order": round(totals["orders"] / max(totals["sessions"], 1), 3),
            "order_to_collected": round(totals["collected"] / max(totals["orders"], 1), 3),
        },
    }


@router.get("/hourly")
async def hourly_distribution(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    days: int = Query(7, ge=1, le=MAX_DAYS),
    db: AsyncSession = Depends(get_db),
):
    """Hour-of-day order and revenue totals. Add 5 to UTC hour for IST."""
    start_date, end_date = _parse_range(start, end, days)
    summaries = await get_daily_summaries(db, start_date, end_date)

    orders_by_hour = [0] * 24
    revenue_by_hour = [0] * 24
    for s in summaries:
        if s.orders_by_hour:
            for h, v in enumerate(s.orders_by_hour):
                orders_by_hour[h] += v
        if s.revenue_by_hour:
            for h, v in enumerate(s.revenue_by_hour):
                revenue_by_hour[h] += v

    peak_order = orders_by_hour.index(max(orders_by_hour))
    peak_revenue = revenue_by_hour.index(max(revenue_by_hour))

    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "orders_by_hour": orders_by_hour,
        "revenue_by_hour": revenue_by_hour,
        "peak_hour_orders": peak_order,
        "peak_hour_revenue": peak_revenue,
        "note": "Hour index is UTC. Add 5 to convert to IST (mod 24).",
    }


@router.post("/rebuild")
async def trigger_rebuild(
    target_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually rebuild the daily summary for a date (defaults to today).
    Expose this prominently in the staff dashboard — use after any unexpected
    downtime to ensure the scheduler's missed run is recovered.
    """
    d = target_date or date.today()
    summary = await rebuild_daily_summary(db, d)
    return {
        "rebuilt": d.isoformat(),
        "orders_placed": summary.orders_placed,
        "revenue_paise": summary.revenue_paise,
    }
