"""
backend/app/models/analytics.py

Sprint 10 — Production Analytics
Two tables:
  1. analytics_events  — hour-level event stream (funnel, journey, story, design)
  2. analytics_daily   — pre-aggregated daily summaries (fast dashboard queries)

Design principles:
  - Never block the order/session flow. All writes are fire-and-forget via
    background tasks. A failed analytics write never surfaces to the customer.
  - Store denormalised snapshots on events — don't rely on joins at query time.
  - The daily summary table is rebuilt each night by a scheduled job so that
    dashboards query one row per day, not millions of events.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey,
    Integer, Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.db import Base  # adjust to your actual base import


# ─────────────────────────────────────────────────────────────────────────────
# Event types
# ─────────────────────────────────────────────────────────────────────────────

class EventType:
    # Funnel events
    SESSION_STARTED      = "session_started"
    STORY_SUBMITTED      = "story_submitted"
    DESIGNS_GENERATED    = "designs_generated"
    VARIANT_SELECTED     = "variant_selected"
    ORDER_PLACED         = "order_placed"
    ORDER_PAID           = "order_paid"
    ORDER_READY          = "order_ready"
    ORDER_COLLECTED      = "order_collected"
    SESSION_ABANDONED    = "session_abandoned"

    # Journey timing events
    STORY_TO_DESIGNS_MS  = "story_to_designs_ms"   # latency: story submit → variants ready
    DESIGNS_TO_ORDER_MS  = "designs_to_order_ms"   # latency: first variant shown → order placed
    ORDER_TO_READY_MS    = "order_to_ready_ms"     # latency: order placed → staff marks ready

    # Product intelligence events
    VARIANT_GENERATED    = "variant_generated"     # one row per variant, with style/prompt data
    REPRINT_TRIGGERED    = "reprint_triggered"     # with reason (staff_notes)
    WHATSAPP_SENT        = "whatsapp_sent"         # delivery outcome
    PRICE_MISMATCH       = "price_mismatch"        # stale client cache signal

    # Generation quality
    FAL_GENERATION_RESULT = "fal_generation_result"  # success/fail/partial per job


# ─────────────────────────────────────────────────────────────────────────────
# Table 1: analytics_events
# ─────────────────────────────────────────────────────────────────────────────

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)

    # Temporal
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    hour_bucket: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )  # 0–23 UTC, for hour-level aggregation
    date_bucket: Mapped[date] = mapped_column(
        Date, nullable=False, index=True
    )  # local IST date (UTC+5:30)

    # Session / order context (nullable — not all events have all)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    short_ref: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Product context
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    product_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    size: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Numeric value (used for latency_ms, revenue_paise, quantity, etc.)
    value_int: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    value_float: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Freeform payload — style, prompt, story digest, AI model used, etc.
    # Keep payloads small (< 2KB). Never store PII here.
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<AnalyticsEvent {self.event_type} @ {self.occurred_at}>"


# ─────────────────────────────────────────────────────────────────────────────
# Table 2: analytics_daily
# Pre-aggregated daily summary — rebuilt nightly, queried by the dashboard.
# ─────────────────────────────────────────────────────────────────────────────

class AnalyticsDaily(Base):
    __tablename__ = "analytics_daily"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    summary_date: Mapped[date] = mapped_column(
        Date, nullable=False, unique=True, index=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Operational: volume ───────────────────────────────────────────────────
    sessions_started: Mapped[int] = mapped_column(Integer, default=0)
    sessions_abandoned: Mapped[int] = mapped_column(Integer, default=0)
    stories_submitted: Mapped[int] = mapped_column(Integer, default=0)
    design_jobs_run: Mapped[int] = mapped_column(Integer, default=0)
    variants_generated: Mapped[int] = mapped_column(Integer, default=0)
    variants_failed: Mapped[int] = mapped_column(Integer, default=0)
    orders_placed: Mapped[int] = mapped_column(Integer, default=0)
    orders_collected: Mapped[int] = mapped_column(Integer, default=0)
    reprints: Mapped[int] = mapped_column(Integer, default=0)
    whatsapp_sent: Mapped[int] = mapped_column(Integer, default=0)
    whatsapp_failed: Mapped[int] = mapped_column(Integer, default=0)

    # ── Operational: revenue ─────────────────────────────────────────────────
    revenue_paise: Mapped[int] = mapped_column(Integer, default=0)
    cash_paise: Mapped[int] = mapped_column(Integer, default=0)
    upi_paise: Mapped[int] = mapped_column(Integer, default=0)
    avg_order_value_paise: Mapped[int] = mapped_column(Integer, default=0)

    # ── Operational: timing (milliseconds) ───────────────────────────────────
    avg_story_to_designs_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    p95_story_to_designs_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_order_to_ready_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    p95_order_to_ready_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Funnel: conversion rates (0.0–1.0) ───────────────────────────────────
    story_to_order_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    session_to_order_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    variant_selection_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Product intelligence: top performers (JSONB lists) ───────────────────
    # e.g. [{"style": "minimalist", "selection_rate": 0.42, "count": 18}, ...]
    top_styles_by_selection: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # e.g. [{"product_id": "tshirt-crew", "size": "L", "count": 24}, ...]
    top_products_by_size: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # e.g. [{"color": "Black", "count": 31, "reprint_rate": 0.04}, ...]
    color_distribution: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Reprint rate by product/color combination
    reprint_rate_by_color: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ── Hour-of-day distribution (arrays of 24 ints, index = hour 0–23) ──────
    orders_by_hour: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    revenue_by_hour: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<AnalyticsDaily {self.summary_date} orders={self.orders_placed}>"
