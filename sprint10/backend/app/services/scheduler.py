"""
backend/app/services/scheduler.py

Sprint 10 — Nightly analytics aggregation scheduler.

Uses APScheduler (async). Add to your app startup in main.py.

Install: pip install apscheduler

Startup integration (add to main.py):
    from app.services.scheduler import start_scheduler, shutdown_scheduler

    @app.on_event("startup")
    async def on_startup():
        await start_scheduler()

    @app.on_event("shutdown")
    async def on_shutdown():
        await shutdown_scheduler()
"""

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.models.db import AsyncSessionLocal  # adjust to your session factory import
from app.services.analytics import rebuild_daily_summary

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_nightly_aggregation() -> None:
    """
    Rebuild yesterday's summary (in case of late events) and today's summary.
    Runs at 23:59 IST (18:29 UTC) and 00:30 IST (19:00 UTC previous day).
    """
    today     = date.today()
    yesterday = today - timedelta(days=1)

    async with AsyncSessionLocal() as db:
        try:
            logger.info("Nightly aggregation: rebuilding %s", yesterday)
            await rebuild_daily_summary(db, yesterday)
        except Exception:
            logger.exception("Failed to rebuild daily summary for %s", yesterday)

        try:
            logger.info("Nightly aggregation: rebuilding %s (today)", today)
            await rebuild_daily_summary(db, today)
        except Exception:
            logger.exception("Failed to rebuild daily summary for %s", today)


async def start_scheduler() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    # 23:59 IST — capture the full day
    _scheduler.add_job(
        _run_nightly_aggregation,
        CronTrigger(hour=23, minute=59, timezone="Asia/Kolkata"),
        id="nightly_aggregation_end",
        replace_existing=True,
    )

    # 00:30 IST — catch any events that arrived after midnight
    _scheduler.add_job(
        _run_nightly_aggregation,
        CronTrigger(hour=0, minute=30, timezone="Asia/Kolkata"),
        id="nightly_aggregation_catchup",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Analytics scheduler started (IST timezone)")


async def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Analytics scheduler stopped")
