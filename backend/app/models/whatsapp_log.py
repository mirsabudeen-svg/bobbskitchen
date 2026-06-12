"""
backend/app/models/whatsapp_log.py

Stores every WhatsApp send attempt for audit, retry logic, and
end-of-day reconciliation (how many customers received their artwork).

Migration: add to your next Alembic revision (see sprint9 migration below).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db import Base


class WhatsAppLog(Base):
    __tablename__ = "whatsapp_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    short_ref: Mapped[str] = mapped_column(String(10), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(5), nullable=False)  # "en" | "ml"
    image_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Twilio response
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    message_sid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship back to the order (optional — for joins)
    order = relationship("Order", back_populates="whatsapp_logs")

    def __repr__(self) -> str:
        status = "OK" if self.success else f"FAIL({self.error})"
        return f"<WhatsAppLog {self.short_ref} → {self.customer_phone} [{status}]>"
