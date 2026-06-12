"""Nightly analytics aggregation scheduler — Sprint 10.

Uses APScheduler (async). Integrated into app lifespan in main.py.
Install: pip install apscheduler tzdata
"""

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.analytics import rebuild_daily_summary

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_session_factory: async_sessionmaker | None = None


def configure_scheduler(session_factory: async_sessionmaker) -> None:
    """Call once at startup with app.state.session_factory."""
    global _session_factory
    _session_factory = session_factory


async def _run_nightly_aggregation() -> None:
    """Rebuild yesterday and today summaries. Runs at 23:59 and 00:30 IST."""
    if _session_factory is None:
        logger.error("Scheduler: session_factory not configured — skipping aggregation")
        return

    today = date.today()
    yesterday = today - timedelta(days=1)

    async with _session_factory() as db:
        for target in (yesterday, today):
            try:
                logger.info("Nightly aggregation: rebuilding %s", target)
                await rebuild_daily_summary(db, target)
            except Exception:
                logger.exception("Failed to rebuild daily summary for %s", target)


async def start_scheduler(session_factory: async_sessionmaker) -> None:
    global _scheduler
    configure_scheduler(session_factory)

    _scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    # 23:59 IST — capture the full operating day
    _scheduler.add_job(
        _run_nightly_aggregation,
        CronTrigger(hour=23, minute=59, timezone="Asia/Kolkata"),
        id="nightly_aggregation_end",
        replace_existing=True,
    )

    # 00:30 IST — catch any late-arriving events
    _scheduler.add_job(
        _run_nightly_aggregation,
        CronTrigger(hour=0, minute=30, timezone="Asia/Kolkata"),
        id="nightly_aggregation_catchup",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Analytics scheduler started (IST timezone, 23:59 + 00:30 jobs)")


async def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Analytics scheduler stopped")
