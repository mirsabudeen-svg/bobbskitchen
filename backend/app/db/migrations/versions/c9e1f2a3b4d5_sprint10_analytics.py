"""Sprint 10 — Analytics tables + story_started_at on sessions.

Revision ID: c9e1f2a3b4d5
Revises: b7d2e9f4c1a8
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "c9e1f2a3b4d5"
down_revision = "b7d2e9f4c1a8"
branch_labels = None
depends_on = None


def upgrade():
    # ── sessions: story_started_at for journey latency measurement ────────────
    op.add_column(
        "sessions",
        sa.Column("story_started_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── analytics_events ──────────────────────────────────────────────────────
    op.create_table(
        "analytics_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("hour_bucket", sa.Integer(), nullable=False),
        sa.Column("date_bucket", sa.Date(), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True),
        sa.Column("order_id", UUID(as_uuid=True), nullable=True),
        sa.Column("short_ref", sa.String(10), nullable=True),
        sa.Column("variant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("product_id", sa.String(50), nullable=True),
        sa.Column("size", sa.String(10), nullable=True),
        sa.Column("color", sa.String(30), nullable=True),
        sa.Column("value_int", sa.Integer(), nullable=True),
        sa.Column("value_float", sa.Float(), nullable=True),
        sa.Column("payload", JSONB(), nullable=True),
    )
    op.create_index("ix_ae_event_type", "analytics_events", ["event_type"])
    op.create_index("ix_ae_occurred_at", "analytics_events", ["occurred_at"])
    op.create_index("ix_ae_date_bucket", "analytics_events", ["date_bucket"])
    op.create_index("ix_ae_session_id", "analytics_events", ["session_id"])
    op.create_index("ix_ae_order_id", "analytics_events", ["order_id"])
    op.create_index("ix_ae_date_type", "analytics_events", ["date_bucket", "event_type"])

    # ── analytics_daily ───────────────────────────────────────────────────────
    op.create_table(
        "analytics_daily",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("summary_date", sa.Date(), nullable=False, unique=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("sessions_started", sa.Integer(), default=0),
        sa.Column("sessions_abandoned", sa.Integer(), default=0),
        sa.Column("stories_submitted", sa.Integer(), default=0),
        sa.Column("design_jobs_run", sa.Integer(), default=0),
        sa.Column("variants_generated", sa.Integer(), default=0),
        sa.Column("variants_failed", sa.Integer(), default=0),
        sa.Column("orders_placed", sa.Integer(), default=0),
        sa.Column("orders_collected", sa.Integer(), default=0),
        sa.Column("reprints", sa.Integer(), default=0),
        sa.Column("whatsapp_sent", sa.Integer(), default=0),
        sa.Column("whatsapp_failed", sa.Integer(), default=0),
        sa.Column("revenue_paise", sa.Integer(), default=0),
        sa.Column("cash_paise", sa.Integer(), default=0),
        sa.Column("upi_paise", sa.Integer(), default=0),
        sa.Column("avg_order_value_paise", sa.Integer(), default=0),
        sa.Column("avg_story_to_designs_ms", sa.Integer(), nullable=True),
        sa.Column("p95_story_to_designs_ms", sa.Integer(), nullable=True),
        sa.Column("avg_order_to_ready_ms", sa.Integer(), nullable=True),
        sa.Column("p95_order_to_ready_ms", sa.Integer(), nullable=True),
        sa.Column("story_to_order_rate", sa.Float(), nullable=True),
        sa.Column("session_to_order_rate", sa.Float(), nullable=True),
        sa.Column("variant_selection_rate", sa.Float(), nullable=True),
        sa.Column("top_styles_by_selection", JSONB(), nullable=True),
        sa.Column("top_products_by_size", JSONB(), nullable=True),
        sa.Column("color_distribution", JSONB(), nullable=True),
        sa.Column("reprint_rate_by_color", JSONB(), nullable=True),
        sa.Column("orders_by_hour", JSONB(), nullable=True),
        sa.Column("revenue_by_hour", JSONB(), nullable=True),
    )
    op.create_index("ix_ad_summary_date", "analytics_daily", ["summary_date"])


def downgrade():
    op.drop_index("ix_ad_summary_date", table_name="analytics_daily")
    op.drop_table("analytics_daily")
    op.drop_index("ix_ae_date_type", table_name="analytics_events")
    op.drop_index("ix_ae_order_id", table_name="analytics_events")
    op.drop_index("ix_ae_session_id", table_name="analytics_events")
    op.drop_index("ix_ae_date_bucket", table_name="analytics_events")
    op.drop_index("ix_ae_occurred_at", table_name="analytics_events")
    op.drop_index("ix_ae_event_type", table_name="analytics_events")
    op.drop_table("analytics_events")
    op.drop_column("sessions", "story_started_at")
