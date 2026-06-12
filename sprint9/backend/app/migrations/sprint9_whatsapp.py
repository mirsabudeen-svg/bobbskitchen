"""
alembic/versions/sprint9_whatsapp.py

Sprint 9 — WhatsApp notification infrastructure.
Adds:
  - whatsapp_logs table
  - orders.whatsapp_sent  (bool, default False — quick status flag)
  - orders.whatsapp_log_id (FK to last send attempt)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade():
    # --- whatsapp_logs table ---
    op.create_table(
        "whatsapp_logs",
        sa.Column("id",             UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id",       UUID(as_uuid=True),
                  sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("short_ref",      sa.String(10),  nullable=False),
        sa.Column("customer_phone", sa.String(30),  nullable=False),
        sa.Column("customer_name",  sa.String(200), nullable=False),
        sa.Column("language",       sa.String(5),   nullable=False),
        sa.Column("image_url",      sa.Text(),      nullable=False),
        sa.Column("success",        sa.Boolean(),   nullable=False),
        sa.Column("message_sid",    sa.String(50),  nullable=True),
        sa.Column("error",          sa.Text(),      nullable=True),
        sa.Column("attempted_at",   sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_whatsapp_logs_order_id", "whatsapp_logs", ["order_id"])

    # --- orders additions ---
    op.add_column("orders",
        sa.Column("whatsapp_sent", sa.Boolean(), server_default="false", nullable=False)
    )
    op.add_column("orders",
        sa.Column("whatsapp_log_id", UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_orders_whatsapp_log",
        "orders", "whatsapp_logs",
        ["whatsapp_log_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_orders_whatsapp_log", "orders", type_="foreignkey")
    op.drop_column("orders", "whatsapp_log_id")
    op.drop_column("orders", "whatsapp_sent")
    op.drop_index("ix_whatsapp_logs_order_id", table_name="whatsapp_logs")
    op.drop_table("whatsapp_logs")
