"""add chapters and question chapter_id

Revision ID: 20260909_06
Revises: 20260721_05
Create Date: 2026-09-09 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260909_06"
down_revision: Union[str, Sequence[str], None] = "20260721_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_chapters_user_id", "chapters", ["user_id"], unique=False)
    op.create_index("ix_chapters_subject_id", "chapters", ["subject_id"], unique=False)
    op.create_index("ix_chapters_name", "chapters", ["name"], unique=False)

    with op.batch_alter_table("questions") as batch_op:
        batch_op.add_column(sa.Column("chapter_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_questions_chapter_id", ["chapter_id"])
        batch_op.create_foreign_key(
            "fk_questions_chapter_id",
            "chapters",
            ["chapter_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_constraint("fk_questions_chapter_id", type_="foreignkey")
        batch_op.drop_index("ix_questions_chapter_id")
        batch_op.drop_column("chapter_id")

    op.drop_index("ix_chapters_name", table_name="chapters")
    op.drop_index("ix_chapters_subject_id", table_name="chapters")
    op.drop_index("ix_chapters_user_id", table_name="chapters")
    op.drop_table("chapters")
