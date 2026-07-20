"""add billing and per-user ai key fields

Revision ID: 20260720_04
Revises: 20260629_03
Create Date: 2026-07-20 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260720_04"
down_revision: Union[str, Sequence[str], None] = "20260629_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("invite_code", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("invited_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("ai_provider", sa.String(), nullable=True, server_default="platform"))
        batch_op.add_column(sa.Column("custom_ai_api_key_encrypted", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("balance_cents", sa.Integer(), nullable=True, server_default="0"))
        batch_op.add_column(sa.Column("call_credits", sa.Integer(), nullable=True, server_default="0"))
        batch_op.add_column(sa.Column("member_expires_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("member_calls_remaining", sa.Integer(), nullable=True, server_default="0"))
        batch_op.add_column(sa.Column("free_calls_used", sa.Integer(), nullable=True, server_default="0"))
        batch_op.add_column(sa.Column("free_calls_date", sa.String(), nullable=True))
        batch_op.create_foreign_key("fk_users_invited_by_id_users", "users", ["invited_by_id"], ["id"])

    op.create_index("ix_users_invite_code", "users", ["invite_code"], unique=True)
    op.create_index("ix_users_invited_by_id", "users", ["invited_by_id"], unique=False)

    op.create_table(
        "wallet_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("tx_type", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_wallet_transactions_user_id", "wallet_transactions", ["user_id"], unique=False)
    op.create_index("ix_wallet_transactions_source_user_id", "wallet_transactions", ["source_user_id"], unique=False)

    op.create_table(
        "keepseek_usage",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("cost_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_keepseek_usage_user_id", "keepseek_usage", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_keepseek_usage_user_id", table_name="keepseek_usage")
    op.drop_table("keepseek_usage")

    op.drop_index("ix_wallet_transactions_source_user_id", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_user_id", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")

    op.drop_index("ix_users_invited_by_id", table_name="users")
    op.drop_index("ix_users_invite_code", table_name="users")
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_users_invited_by_id_users", type_="foreignkey")
        batch_op.drop_column("free_calls_date")
        batch_op.drop_column("free_calls_used")
        batch_op.drop_column("member_calls_remaining")
        batch_op.drop_column("member_expires_at")
        batch_op.drop_column("call_credits")
        batch_op.drop_column("balance_cents")
        batch_op.drop_column("custom_ai_api_key_encrypted")
        batch_op.drop_column("ai_provider")
        batch_op.drop_column("invited_by_id")
        batch_op.drop_column("invite_code")
