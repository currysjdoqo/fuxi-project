"""add payment orders

Revision ID: 20260721_05
Revises: 20260720_04
Create Date: 2026-07-21 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260721_05"
down_revision: Union[str, Sequence[str], None] = "20260720_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_orders",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("product_type", sa.String(length=32), nullable=False),
        sa.Column("plan", sa.String(length=32), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("provider_order_no", sa.String(length=128), nullable=True),
        sa.Column("payment_url", sa.String(), nullable=True),
        sa.Column("callback_payload", sa.JSON(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_payment_orders_order_no", "payment_orders", ["order_no"], unique=True)
    op.create_index("ix_payment_orders_user_id", "payment_orders", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payment_orders_user_id", table_name="payment_orders")
    op.drop_index("ix_payment_orders_order_no", table_name="payment_orders")
    op.drop_table("payment_orders")
