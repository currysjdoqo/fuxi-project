"""legacy baseline schema

Revision ID: 20260628_01
Revises:
Create Date: 2026-06-28 16:50:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260628_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARUI_HASH = "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_token", "users", ["token"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_subjects_id", "subjects", ["id"], unique=False)
    op.create_index("ix_subjects_user_id", "subjects", ["user_id"], unique=False)
    op.create_index("ix_subjects_name", "subjects", ["name"], unique=False)

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("answer", sa.String(), nullable=True),
        sa.Column("explanation", sa.String(), nullable=True),
        sa.Column("is_important", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_questions_id", "questions", ["id"], unique=False)
    op.create_index("ix_questions_type", "questions", ["type"], unique=False)
    op.create_index("ix_questions_content", "questions", ["content"], unique=False)

    op.create_table(
        "practice_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("user_answer", sa.String(), nullable=False),
        sa.Column("is_correct", sa.Integer(), nullable=False),
        sa.Column("practiced_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_practice_records_id", "practice_records", ["id"], unique=False)

    op.create_table(
        "wrong_questions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("correct_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "question_id"),
    )
    op.create_index("ix_wrong_questions_id", "wrong_questions", ["id"], unique=False)
    op.create_index("ix_wrong_questions_user_id", "wrong_questions", ["user_id"], unique=False)
    op.create_index("ix_wrong_questions_question_id", "wrong_questions", ["question_id"], unique=False)

    op.create_table(
        "plan_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("completed", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_plan_items_id", "plan_items", ["id"], unique=False)
    op.create_index("ix_plan_items_user_id", "plan_items", ["user_id"], unique=False)
    op.create_index("ix_plan_items_date", "plan_items", ["date"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT OR IGNORE INTO users (username, password_hash, token, created_at)
            VALUES ('arui', :password_hash, NULL, CURRENT_TIMESTAMP)
            """
        ).bindparams(password_hash=ARUI_HASH)
    )


def downgrade() -> None:
    op.drop_index("ix_plan_items_date", table_name="plan_items")
    op.drop_index("ix_plan_items_user_id", table_name="plan_items")
    op.drop_index("ix_plan_items_id", table_name="plan_items")
    op.drop_table("plan_items")

    op.drop_index("ix_wrong_questions_question_id", table_name="wrong_questions")
    op.drop_index("ix_wrong_questions_user_id", table_name="wrong_questions")
    op.drop_index("ix_wrong_questions_id", table_name="wrong_questions")
    op.drop_table("wrong_questions")

    op.drop_index("ix_practice_records_question_id", table_name="practice_records")
    op.drop_index("ix_practice_records_user_id", table_name="practice_records")
    op.drop_index("ix_practice_records_id", table_name="practice_records")
    op.drop_table("practice_records")

    op.drop_index("ix_questions_content", table_name="questions")
    op.drop_index("ix_questions_type", table_name="questions")
    op.drop_index("ix_questions_subject_id", table_name="questions")
    op.drop_index("ix_questions_user_id", table_name="questions")
    op.drop_index("ix_questions_id", table_name="questions")
    op.drop_table("questions")

    op.drop_index("ix_subjects_name", table_name="subjects")
    op.drop_index("ix_subjects_user_id", table_name="subjects")
    op.drop_index("ix_subjects_id", table_name="subjects")
    op.drop_table("subjects")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_token", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
