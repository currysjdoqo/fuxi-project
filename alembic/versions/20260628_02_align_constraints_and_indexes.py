"""align constraints and indexes with models

Revision ID: 20260628_02
Revises: 20260628_01
Create Date: 2026-06-28 17:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260628_02"
down_revision: Union[str, Sequence[str], None] = "20260628_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_questions_user_id", "questions", ["user_id"], unique=False)
    op.create_index("ix_questions_subject_id", "questions", ["subject_id"], unique=False)
    op.create_index("ix_practice_records_user_id", "practice_records", ["user_id"], unique=False)
    op.create_index("ix_practice_records_question_id", "practice_records", ["question_id"], unique=False)

    with op.batch_alter_table("subjects", recreate="always") as batch_op:
        batch_op.alter_column("id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key("fk_subjects_user_id_users", "users", ["user_id"], ["id"])

    with op.batch_alter_table("questions", recreate="always") as batch_op:
        batch_op.create_foreign_key("fk_questions_user_id_users", "users", ["user_id"], ["id"])
        batch_op.create_foreign_key("fk_questions_subject_id_subjects", "subjects", ["subject_id"], ["id"])

    with op.batch_alter_table("practice_records", recreate="always") as batch_op:
        batch_op.create_foreign_key("fk_practice_records_user_id_users", "users", ["user_id"], ["id"])

    with op.batch_alter_table("wrong_questions", recreate="always") as batch_op:
        batch_op.alter_column("id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key("fk_wrong_questions_user_id_users", "users", ["user_id"], ["id"])
        batch_op.create_unique_constraint("uq_wrong_questions_user_question", ["user_id", "question_id"])


def downgrade() -> None:
    with op.batch_alter_table("wrong_questions", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_wrong_questions_user_question", type_="unique")
        batch_op.drop_constraint("fk_wrong_questions_user_id_users", type_="foreignkey")
        batch_op.alter_column("id", existing_type=sa.Integer(), nullable=True)
        batch_op.create_unique_constraint(None, ["user_id", "question_id"])

    with op.batch_alter_table("practice_records", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_practice_records_user_id_users", type_="foreignkey")

    with op.batch_alter_table("questions", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_questions_subject_id_subjects", type_="foreignkey")
        batch_op.drop_constraint("fk_questions_user_id_users", type_="foreignkey")

    with op.batch_alter_table("subjects", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_subjects_user_id_users", type_="foreignkey")
        batch_op.alter_column("id", existing_type=sa.Integer(), nullable=True)

    op.drop_index("ix_practice_records_question_id", table_name="practice_records")
    op.drop_index("ix_practice_records_user_id", table_name="practice_records")
    op.drop_index("ix_questions_subject_id", table_name="questions")
    op.drop_index("ix_questions_user_id", table_name="questions")
