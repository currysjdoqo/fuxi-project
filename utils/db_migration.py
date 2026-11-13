from sqlalchemy import inspect, Column, Integer, String, DateTime, JSON, ForeignKey, UniqueConstraint, text

from database import engine, Base
from models import User, Subject, Question, PracticeRecord, WrongQuestion, PlanItem, Friendship, Message, ShareRecord, WalletTransaction, KeepSeekUsage, PaymentOrder


# 结构版本号：升到该版本后，后续启动直接跳过反射检查
SCHEMA_VERSION = 4

# 高频查询用到的复合索引（(表, 索引名, 列)）
COMPOSITE_INDEXES = [
    ("questions", "ix_questions_user_deleted", "user_id, deleted_at"),
    ("questions", "ix_questions_user_subject_deleted", "user_id, subject_id, deleted_at"),
    ("questions", "ix_questions_chapter_user_deleted", "chapter_id, user_id, deleted_at"),
    ("questions", "ix_questions_user_subject_hash", "user_id, subject_id, content_hash"),
    ("practice_records", "ix_practice_records_user_question_time", "user_id, question_id, practiced_at"),
    ("practice_records", "ix_practice_records_user_time", "user_id, practiced_at"),
    ("messages", "ix_messages_receiver_read_created", "receiver_id, is_read, created_at"),
]


def _get_schema_version():
    with engine.connect() as conn:
        return conn.execute(text("PRAGMA user_version")).scalar() or 0


def _set_schema_version(version):
    with engine.connect() as conn:
        conn.execute(text(f"PRAGMA user_version = {int(version)}"))
        conn.commit()


def ensure_composite_indexes():
    """只建缺失的复合索引；已存在则跳过（幂等）。"""
    created = []
    with engine.connect() as conn:
        existing = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))}
        for table, name, columns in COMPOSITE_INDEXES:
            if name in existing:
                continue
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})"))
            created.append(name)
        conn.commit()
    return created


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


def migrate_questions_table():
    inspector = inspect(engine)
    if not inspector.has_table('questions'):
        return

    columns = [col['name'] for col in inspector.get_columns('questions')]
    if 'chapter_id' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE questions ADD COLUMN chapter_id INTEGER"))
            conn.commit()
        print("已为 questions 表添加字段: chapter_id")

    if 'knowledge_tags' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE questions ADD COLUMN knowledge_tags JSON"))
            conn.commit()
        print("已为 questions 表添加字段: knowledge_tags")


def migrate_questions_content_hash():
    """补齐 questions.content_hash 并回填历史数据（幂等、分批）。"""
    inspector = inspect(engine)
    if not inspector.has_table('questions'):
        return

    columns = [col['name'] for col in inspector.get_columns('questions')]
    if 'content_hash' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE questions ADD COLUMN content_hash VARCHAR(64)"))
            conn.commit()
        print("已为 questions 表添加字段: content_hash")

    from utils.content_hash import content_hash

    filled = 0
    while True:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, content FROM questions WHERE content_hash IS NULL LIMIT 500")
            ).fetchall()
        if not rows:
            break
        with engine.begin() as conn:
            for row_id, content in rows:
                conn.execute(
                    text("UPDATE questions SET content_hash = :hash WHERE id = :id"),
                    {"hash": content_hash(content or ""), "id": row_id},
                )
        filled += len(rows)
    if filled:
        print(f"已回填 {filled} 条题目的 content_hash")


def migrate_chapters_table():
    inspector = inspect(engine)
    if not inspector.has_table('chapters'):
        return

    columns = [col['name'] for col in inspector.get_columns('chapters')]
    new_columns = {
        'summary_md': 'TEXT',
        'outline_json': 'JSON',
        'tags_generated_at': 'DATETIME',
        'summary_generated_at': 'DATETIME',
        'outline_generated_at': 'DATETIME',
    }
    for col_name, col_type in new_columns.items():
        if col_name not in columns:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE chapters ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            print(f"已为 chapters 表添加字段: {col_name}")


def migrate_subjects_table():
    inspector = inspect(engine)
    if not inspector.has_table('subjects'):
        return

    columns = [col['name'] for col in inspector.get_columns('subjects')]
    if 'folder_id' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE subjects ADD COLUMN folder_id INTEGER"))
            conn.commit()
        print("已为 subjects 表添加字段: folder_id")


def migrate_all_tables():
    try:
        version = _get_schema_version()
        if version >= SCHEMA_VERSION:
            return
        print("开始数据库迁移检查...")
        migrate_users_table()
        migrate_subjects_table()
        migrate_questions_table()
        migrate_questions_content_hash()
        migrate_chapters_table()
        created = ensure_composite_indexes()
        if created:
            print(f"已创建索引: {', '.join(created)}")
        _set_schema_version(SCHEMA_VERSION)
        print("数据库迁移检查完成")
    except Exception as e:
        print(f"数据库迁移检查跳过（可能是新数据库）: {e}")


if __name__ == "__main__":
    migrate_all_tables()