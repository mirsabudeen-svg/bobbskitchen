"""SQLAlchemy 2.0 ORM models — all 10 tables from database_schema.md."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )


def _created_at() -> Mapped[datetime]:
    return mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    current_state: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'idle'")
    )
    customer_name: Mapped[str | None] = mapped_column(String(100))
    customer_phone: Mapped[str | None] = mapped_column(String(20))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    abandoned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    satisfaction_score: Mapped[int | None] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(Text)
    device_id: Mapped[str | None] = mapped_column(String(50))
    prompt_variant: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'v1'")
    )

    __table_args__ = (
        CheckConstraint(
            "satisfaction_score BETWEEN 1 AND 5", name="ck_sessions_satisfaction"
        ),
        Index("idx_sessions_state", "current_state"),
        Index("idx_sessions_created", "created_at"),
        Index("idx_sessions_completed", "completed", "created_at"),
    )


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = _created_at()
    turn_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    input_type: Mapped[str] = mapped_column(String(10), nullable=False)
    customer_input: Mapped[str] = mapped_column(Text, nullable=False)
    agent_response: Mapped[str | None] = mapped_column(Text)
    agent_text_reply: Mapped[str | None] = mapped_column(Text)
    story_extracted: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    clarification_needed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    clarity_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    tokens_input: Mapped[int | None] = mapped_column(Integer)
    tokens_output: Mapped[int | None] = mapped_column(Integer)
    model_used: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        CheckConstraint("input_type IN ('text')", name="ck_conv_input_type"),
        Index("idx_conv_session", "session_id", "turn_number"),
    )


class Design(Base):
    __tablename__ = "designs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = _created_at()
    story_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    story_version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("1")
    )
    design_prompt_base: Mapped[str] = mapped_column(Text, nullable=False)
    design_strategy_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    design_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Circular FK to design_variants — DEFERRABLE INITIALLY DEFERRED (FIX ISSUE-08)
    selected_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "design_variants.id",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
            name="fk_designs_selected_variant",
        ),
    )
    refinements_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    regenerations_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    design_locked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    locked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    is_fallback: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    recommendations_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    recommendations_generated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    recommendations_model: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (Index("idx_designs_session", "session_id"),)


class DesignVariantRow(Base):
    __tablename__ = "design_variants"

    id: Mapped[uuid.UUID] = _uuid_pk()
    design_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = _created_at()
    variant_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_initial_set: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    prompt_used: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str | None] = mapped_column(Text)
    style: Mapped[str | None] = mapped_column(String(30))
    image_url: Mapped[str | None] = mapped_column(Text)
    generation_time_ms: Mapped[int | None] = mapped_column(Integer)
    model_used: Mapped[str | None] = mapped_column(String(80))
    fal_request_id: Mapped[str | None] = mapped_column(String(100))
    generation_seed: Mapped[int | None] = mapped_column(BigInteger)
    is_fallback: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_refined: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    parent_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("design_variants.id")
    )
    refinement_type: Mapped[str | None] = mapped_column(String(30))
    refinement_value: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (
        Index("idx_variants_design", "design_id"),
        Index("idx_variants_initial", "design_id", "is_initial_set"),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(String(20))
    name_tag_text: Mapped[str | None] = mapped_column(String(15))
    subtotal_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_paise: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    discount_type: Mapped[str | None] = mapped_column(String(20))
    tax_paise: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    total_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'INR'")
    )
    payment_method: Mapped[str | None] = mapped_column(String(10))
    payment_status: Mapped[str] = mapped_column(
        String(15), nullable=False, server_default=text("'pending'")
    )
    payment_ref: Mapped[str | None] = mapped_column(String(100))
    order_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Sprint 7 ops columns
    short_ref: Mapped[str | None] = mapped_column(String(10), unique=True)
    daily_sequence: Mapped[int | None] = mapped_column(Integer)
    staff_notes: Mapped[str | None] = mapped_column(Text)
    reprint_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    reprint_of_order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    amount_paid_paise: Mapped[int | None] = mapped_column(Integer)
    idempotency_key: Mapped[str | None] = mapped_column(String(36), unique=True)

    # Sprint 9: WhatsApp delivery
    whatsapp_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    whatsapp_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_logs.id", ondelete="SET NULL", use_alter=True,
                   name="fk_orders_whatsapp_log"),
        nullable=True,
    )

    # Relationships
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        primaryjoin="Order.id == OrderItem.order_id",
        foreign_keys="OrderItem.order_id",
        lazy="select",
    )
    whatsapp_logs: Mapped[list["WhatsAppLog"]] = relationship(  # type: ignore[name-defined]
        "WhatsAppLog",
        primaryjoin="Order.id == foreign(WhatsAppLog.order_id)",
        back_populates="order",
        lazy="select",
        viewonly=True,
    )

    __table_args__ = (
        CheckConstraint(
            "payment_method IS NULL OR payment_method IN ('upi', 'card', 'cash')",
            name="ck_orders_payment_method_v2",
        ),
        CheckConstraint(
            "payment_status IN ('pending', 'paid')",
            name="ck_orders_payment_status_v2",
        ),
        CheckConstraint(
            "order_status IN ('pending', 'printing', 'ready', 'failed', 'reprinting', 'collected')",
            name="ck_orders_order_status_v2",
        ),
        Index("idx_orders_session", "session_id"),
        Index("idx_orders_status", "order_status", "created_at"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    design_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("design_variants.id"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()
    product_id: Mapped[str] = mapped_column(String(50), nullable=False)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[str | None] = mapped_column(String(5))
    color: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("1")
    )
    unit_price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal_paise: Mapped[int] = mapped_column(Integer, nullable=False)

    # Sprint 7 ops: print spec denormalised at order creation
    image_url: Mapped[str | None] = mapped_column(Text)
    print_width_in: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    print_height_in: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    print_placement: Mapped[str | None] = mapped_column(String(50))
    name_tag_text: Mapped[str | None] = mapped_column(String(15))

    # Relationship to design variant (for future use; print spec is denormalized)
    design_variant: Mapped["DesignVariantRow"] = relationship(
        "DesignVariantRow",
        primaryjoin="OrderItem.design_variant_id == DesignVariantRow.id",
        foreign_keys="OrderItem.design_variant_id",
        lazy="select",
    )

    __table_args__ = (
        Index("idx_items_order", "order_id"),
        Index("idx_order_items_variant", "design_variant_id"),
    )


class ProductionJob(Base):
    __tablename__ = "production_jobs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()
    design_file_path: Mapped[str | None] = mapped_column(Text)
    print_status: Mapped[str] = mapped_column(
        String(15), nullable=False, server_default=text("'queued'")
    )
    print_started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    print_completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    print_duration_s: Mapped[int | None] = mapped_column(Integer)
    press_status: Mapped[str] = mapped_column(
        String(15), nullable=False, server_default=text("'queued'")
    )
    press_started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    press_completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    stitch_status: Mapped[str] = mapped_column(
        String(15), nullable=False, server_default=text("'queued'")
    )
    stitch_completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    quality_check_passed: Mapped[bool | None] = mapped_column(Boolean)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "print_status IN ('queued','printing','complete','failed')",
            name="ck_jobs_print_status",
        ),
        CheckConstraint(
            "press_status IN ('queued','pressing','complete','failed')",
            name="ck_jobs_press_status",
        ),
        CheckConstraint(
            "stitch_status IN ('queued','stitching','complete','skipped')",
            name="ck_jobs_stitch_status",
        ),
        Index("idx_jobs_order", "order_id"),
        Index("idx_jobs_status", "print_status", "created_at"),
    )


class Inventory(Base):
    __tablename__ = "inventory"

    product_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str | None] = mapped_column(String(30))
    price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    print_area: Mapped[str | None] = mapped_column(String(50))
    min_complexity: Mapped[str | None] = mapped_column(
        String(10), server_default=text("'simple'")
    )
    max_complexity: Mapped[str | None] = mapped_column(
        String(10), server_default=text("'complex'")
    )
    production_time_min: Mapped[int | None] = mapped_column(SmallInteger)
    margin_percent: Mapped[int | None] = mapped_column(SmallInteger)
    units_total: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    units_sold: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    units_reserved: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    reorder_level: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("5")
    )
    design_fit_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    sizes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    colors: Mapped[list[Any] | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id")
    )
    created_at: Mapped[datetime] = _created_at()
    agent_name: Mapped[str] = mapped_column(String(30), nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(50))
    state: Mapped[str | None] = mapped_column(String(32))
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    is_fallback: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    tokens_input: Mapped[int | None] = mapped_column(Integer)
    tokens_output: Mapped[int | None] = mapped_column(Integer)
    cost_microdollars: Mapped[int | None] = mapped_column(Integer)
    execution_ms: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    error_code: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_agent_logs_session", "session_id", "created_at"),
        Index("idx_agent_logs_agent", "agent_name", "created_at"),
    )


class Analytics(Base):
    __tablename__ = "analytics"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_sessions: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    completed_sessions: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    abandoned_sessions: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    completed_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    failed_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    revenue_paise: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    avg_session_s: Mapped[int | None] = mapped_column(Integer)
    avg_satisfaction: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    top_product_id: Mapped[str | None] = mapped_column(String(50))
    top_design_theme: Mapped[str | None] = mapped_column(String(50))
    total_agent_calls: Mapped[int | None] = mapped_column(Integer)
    total_tokens_used: Mapped[int | None] = mapped_column(BigInteger)
    total_images_gen: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _created_at()
