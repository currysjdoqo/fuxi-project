from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from database import Base, engine
from routers.auth import router as auth_router
from routers.import_router import router as import_router
from routers.practice import router as practice_router
from routers.review import router as review_router
from routers.settings import router as settings_router
from routers.subjects import router as subjects_router
from routers.trash import router as trash_router
from routers.wrong import router as wrong_router
from routers.plan import router as plan_router

Base.metadata.create_all(bind=engine)


ARUI_HASH = "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"


def ensure_database_schema():
    inspector = inspect(engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR NOT NULL UNIQUE,
                    password_hash VARCHAR NOT NULL,
                    token VARCHAR UNIQUE,
                    created_at DATETIME
                )
                """
            )
        )
        # migrate subjects(name UNIQUE) -> subjects(name non-unique)
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS _subjects_new (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    name VARCHAR NOT NULL,
                    created_at DATETIME
                )
                """
            )
        )
        old_subjects = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='subjects'")
        ).fetchone()
        if old_subjects:
            connection.execute(
                text(
                    """
                    INSERT OR IGNORE INTO _subjects_new (id, user_id, name, created_at)
                    SELECT id, user_id, name, created_at FROM subjects
                    """
                )
            )
            connection.execute(text("DROP TABLE subjects"))
            connection.execute(text("ALTER TABLE _subjects_new RENAME TO subjects"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_subjects_id ON subjects (id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_subjects_user_id ON subjects (user_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_subjects_name ON subjects (name)"))
        else:
            connection.execute(text("DROP TABLE IF EXISTS _subjects_new"))

    if "subjects" in inspector.get_table_names():
        subject_columns = {column["name"] for column in inspector.get_columns("subjects")}
        with engine.begin() as connection:
            if "user_id" not in subject_columns:
                connection.execute(text("ALTER TABLE subjects ADD COLUMN user_id INTEGER"))

    if "questions" in inspector.get_table_names():
        question_columns = {column["name"] for column in inspector.get_columns("questions")}
        with engine.begin() as connection:
            if "user_id" not in question_columns:
                connection.execute(text("ALTER TABLE questions ADD COLUMN user_id INTEGER"))
            if "subject_id" not in question_columns:
                connection.execute(text("ALTER TABLE questions ADD COLUMN subject_id INTEGER"))
            if "deleted_at" not in question_columns:
                connection.execute(text("ALTER TABLE questions ADD COLUMN deleted_at DATETIME"))
            if "is_important" not in question_columns:
                connection.execute(text("ALTER TABLE questions ADD COLUMN is_important INTEGER DEFAULT 0"))

    if "practice_records" in inspector.get_table_names():
        practice_columns = {column["name"] for column in inspector.get_columns("practice_records")}
        with engine.begin() as connection:
            if "user_id" not in practice_columns:
                connection.execute(text("ALTER TABLE practice_records ADD COLUMN user_id INTEGER"))

    if "wrong_questions" in inspector.get_table_names():
        wrong_columns = {column["name"] for column in inspector.get_columns("wrong_questions")}
        with engine.begin() as connection:
            if "user_id" not in wrong_columns:
                connection.execute(text("ALTER TABLE wrong_questions ADD COLUMN user_id INTEGER"))
            if "correct_count" not in wrong_columns:
                connection.execute(text("ALTER TABLE wrong_questions ADD COLUMN correct_count INTEGER DEFAULT 0"))
            connection.execute(text("UPDATE wrong_questions SET correct_count = 0 WHERE correct_count IS NULL"))

    # 创建 plan_items 表
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS plan_items (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    date VARCHAR NOT NULL,
                    content VARCHAR NOT NULL,
                    completed INTEGER DEFAULT 0,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_plan_items_id ON plan_items (id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_plan_items_user_id ON plan_items (user_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_plan_items_date ON plan_items (date)"))

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO users (username, password_hash, token, created_at)
                VALUES ('arui', :password_hash, NULL, CURRENT_TIMESTAMP)
                """
            ),
            {"password_hash": ARUI_HASH},
        )
        connection.execute(
            text("UPDATE users SET password_hash=:password_hash WHERE username='arui'"),
            {"password_hash": ARUI_HASH},
        )
        connection.execute(
            text(
                """
                UPDATE subjects
                SET user_id = (SELECT id FROM users WHERE username='arui')
                WHERE user_id IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE questions
                SET user_id = (SELECT id FROM users WHERE username='arui')
                WHERE user_id IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE practice_records
                SET user_id = (SELECT id FROM users WHERE username='arui')
                WHERE user_id IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE wrong_questions
                SET user_id = (SELECT id FROM users WHERE username='arui')
                WHERE user_id IS NULL
                """
            )
        )


ensure_database_schema()

app = FastAPI(
    title="练习题管理系统",
    description="FastAPI + SQLAlchemy + SQLite",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(import_router, prefix="/api")
app.include_router(practice_router, prefix="/api")
app.include_router(wrong_router, prefix="/api")
app.include_router(review_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(subjects_router, prefix="/api")
app.include_router(trash_router, prefix="/api")
app.include_router(plan_router, prefix="/api")

Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "exercise-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

