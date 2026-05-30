from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from database import Base, engine
from routers.import_router import router as import_router
from routers.practice import router as practice_router
from routers.wrong import router as wrong_router
from routers.review import router as review_router
from routers.settings import router as settings_router
from routers.subjects import router as subjects_router
from routers.trash import router as trash_router

Base.metadata.create_all(bind=engine)


def ensure_database_schema():
    inspector = inspect(engine)
    if "questions" in inspector.get_table_names():
        question_columns = {column["name"] for column in inspector.get_columns("questions")}
        with engine.begin() as connection:
            if "subject_id" not in question_columns:
                connection.execute(text("ALTER TABLE questions ADD COLUMN subject_id INTEGER"))
            if "deleted_at" not in question_columns:
                connection.execute(text("ALTER TABLE questions ADD COLUMN deleted_at DATETIME"))
            if "is_important" not in question_columns:
                connection.execute(text("ALTER TABLE questions ADD COLUMN is_important INTEGER DEFAULT 0"))

            connection.execute(
                text("INSERT OR IGNORE INTO subjects (name, created_at) VALUES ('未分类', CURRENT_TIMESTAMP)")
            )
            connection.execute(
                text(
                    """
                    UPDATE questions
                    SET subject_id = (SELECT id FROM subjects WHERE name = '未分类')
                    WHERE subject_id IS NULL
                    """
                )
            )
    if "wrong_questions" in inspector.get_table_names():
        wrong_columns = {column["name"] for column in inspector.get_columns("wrong_questions")}
        with engine.begin() as connection:
            if "correct_count" not in wrong_columns:
                connection.execute(text("ALTER TABLE wrong_questions ADD COLUMN correct_count INTEGER DEFAULT 0"))
            connection.execute(text("UPDATE wrong_questions SET correct_count = 0 WHERE correct_count IS NULL"))


ensure_database_schema()

# 创建 FastAPI 应用实例
app = FastAPI(
    title="练习题管理系统",
    description="FastAPI + SQLAlchemy + SQLite 后端基础服务",
    version="1.0.0"
)

# 配置 CORS（跨域资源共享）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境应限制具体域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由
app.include_router(import_router, prefix="/api")
app.include_router(practice_router, prefix="/api")
app.include_router(wrong_router, prefix="/api")
app.include_router(review_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(subjects_router, prefix="/api")
app.include_router(trash_router, prefix="/api")


@app.get("/health")
async def health_check():
    """
    健康检查接口
    用于检查服务是否正常运行
    """
    return {"status": "healthy", "service": "exercise-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
