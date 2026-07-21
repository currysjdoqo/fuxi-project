from sqlalchemy import inspect, Column, Integer, String, DateTime, JSON, ForeignKey, UniqueConstraint, text

from database import engine, Base
from models import User, Subject, Question, PracticeRecord, WrongQuestion, PlanItem, Friendship, Message, ShareRecord, WalletTransaction, KeepSeekUsage, PaymentOrder


def add_column_if_not_exists(table_name, column_def):
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    if column_def.name not in columns:
        column_def_name = column_def.name
        column_type = str(column_def.type)
        with engine.connect() as conn:
            if column_type.startswith('INTEGER'):
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_def_name} INTEGER DEFAULT 0"))
            elif column_type.startswith('VARCHAR') or column_type.startswith('TEXT'):
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_def_name} VARCHAR(255)"))
            elif column_type.startswith('DATETIME'):
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_def_name} DATETIME"))
            elif column_type.startswith('JSON'):
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_def_name} TEXT"))
            conn.commit()
        return True
    return False


def migrate_users_table():
    inspector = inspect(engine)
    if not inspector.has_table('users'):
        return

    added = []
    columns_to_add = [
        Column('user_code', String(10)),
        Column('invite_code', String(16)),
        Column('invited_by_id', Integer, ForeignKey("users.id")),
        Column('ai_provider', String),
        Column('custom_ai_api_key_encrypted', String),
        Column('balance_cents', Integer),
        Column('call_credits', Integer),
        Column('member_expires_at', DateTime),
        Column('member_calls_remaining', Integer),
        Column('free_calls_used', Integer),
        Column('free_calls_date', String),
    ]

    for col in columns_to_add:
        if add_column_if_not_exists('users', col):
            added.append(col.name)

    if added:
        with engine.connect() as conn:
            conn.execute(text("UPDATE users SET ai_provider = 'platform' WHERE ai_provider IS NULL"))
            conn.execute(text("UPDATE users SET balance_cents = 0 WHERE balance_cents IS NULL"))
            conn.execute(text("UPDATE users SET call_credits = 0 WHERE call_credits IS NULL"))
            conn.execute(text("UPDATE users SET member_calls_remaining = 0 WHERE member_calls_remaining IS NULL"))
            conn.execute(text("UPDATE users SET free_calls_used = 0 WHERE free_calls_used IS NULL"))
            conn.commit()
        print(f"已为 users 表添加字段: {', '.join(added)}")


def migrate_all_tables():
    try:
        print("开始数据库迁移检查...")
        migrate_users_table()
        print("数据库迁移检查完成")
    except Exception as e:
        print(f"数据库迁移检查跳过（可能是新数据库）: {e}")


if __name__ == "__main__":
    migrate_all_tables()