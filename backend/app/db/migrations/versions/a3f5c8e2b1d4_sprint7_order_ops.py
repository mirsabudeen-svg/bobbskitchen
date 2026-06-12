"""Sprint 7 Order Operations — status lifecycle, print spec, payment, short ref, idempotency

Revision ID: a3f5c8e2b1d4
Revises: f0d86e4e7bcc
Create Date: 2026-06-12

Changes:
- orders: drop old check constraints, add short_ref/daily_sequence/staff_notes/
  reprint_count/reprint_of_order_item_id/paid_at/amount_paid_paise/idempotency_key
  and updated check constraints
- order_items: add image_url/print_width_in/print_height_in/print_placement/name_tag_text
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3f5c8e2b1d4"
down_revision: Union[str, None] = "f0d86e4e7bcc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- drop old check constraints on orders ---
    op.drop_constraint("ck_orders_order_status", "orders", type_="check")
    op.drop_constraint("ck_orders_payment_status", "orders", type_="check")
    op.drop_constraint("ck_orders_payment_method", "orders", type_="check")

    # --- add new columns to orders ---
    op.add_column("orders", sa.Column("short_ref", sa.String(10), nullable=True))
    op.add_column("orders", sa.Column("daily_sequence", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("staff_notes", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("reprint_count", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("orders", sa.Column(
        "reprint_of_order_item_id",
        sa.UUID(),
        sa.ForeignKey("order_items.id"),
        nullable=True,
    ))
    op.add_column("orders", sa.Column("paid_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("amount_paid_paise", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("idempotency_key", sa.String(36), nullable=True))

    # --- unique indexes ---
    op.create_unique_constraint("uq_orders_short_ref", "orders", ["short_ref"])
    op.create_unique_constraint("uq_orders_idempotency", "orders", ["idempotency_key"])

    # --- new check constraints ---
    op.create_check_constraint(
        "ck_orders_order_status_v2",
        "orders",
        "order_status IN ('pending','printing','ready','failed','reprinting','collected')",
    )
    op.create_check_constraint(
        "ck_orders_payment_status_v2",
        "orders",
        "payment_status IN ('pending','paid')",
    )
    op.create_check_constraint(
        "ck_orders_payment_method_v2",
        "orders",
        "payment_method IS NULL OR payment_method IN ('upi','card','cash')",
    )

    # --- add columns to order_items ---
    op.add_column("order_items", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("order_items", sa.Column("print_width_in", sa.Numeric(5, 2), nullable=True))
    op.add_column("order_items", sa.Column("print_height_in", sa.Numeric(5, 2), nullable=True))
    op.add_column("order_items", sa.Column("print_placement", sa.String(50), nullable=True))
    op.add_column("order_items", sa.Column("name_tag_text", sa.String(15), nullable=True))


def downgrade() -> None:
    # restore old constraints
    op.drop_constraint("ck_orders_order_status_v2", "orders", type_="check")
    op.drop_constraint("ck_orders_payment_status_v2", "orders", type_="check")
    op.drop_constraint("ck_orders_payment_method_v2", "orders", type_="check")
    op.create_check_constraint(
        "ck_orders_order_status",
        "orders",
        "order_status IN ('pending','queued','printing','pressing','stitching','complete','cancelled')",
    )
    op.create_check_constraint(
        "ck_orders_payment_status",
        "orders",
        "payment_status IN ('pending','completed','failed','refunded')",
    )
    op.create_check_constraint(
        "ck_orders_payment_method",
        "orders",
        "payment_method IN ('upi','card','cash')",
    )
    op.drop_constraint("uq_orders_short_ref", "orders", type_="unique")
    op.drop_constraint("uq_orders_idempotency", "orders", type_="unique")
    op.drop_column("orders", "short_ref")
    op.drop_column("orders", "daily_sequence")
    op.drop_column("orders", "staff_notes")
    op.drop_column("orders", "reprint_count")
    op.drop_column("orders", "reprint_of_order_item_id")
    op.drop_column("orders", "paid_at")
    op.drop_column("orders", "amount_paid_paise")
    op.drop_column("orders", "idempotency_key")
    op.drop_column("order_items", "image_url")
    op.drop_column("order_items", "print_width_in")
    op.drop_column("order_items", "print_height_in")
    op.drop_column("order_items", "print_placement")
    op.drop_column("order_items", "name_tag_text")
