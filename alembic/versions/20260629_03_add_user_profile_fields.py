"""add avatar and signature fields to users table

Revision ID: 20260629_03
Revises: 20260628_02
Create Date: 2026-06-29 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260629_03"
down_revision: Union[str, Sequence[str], None] = "20260628_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("avatar", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("signature", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.drop_column("signature")
        batch_op.drop_column("avatar")