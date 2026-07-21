from pathlib import Path
from os import getenv
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import Base, engine

load_dotenv()

from utils.db_migration import migrate_all_tables

Base.metadata.create_all(bind=engine)

migrate_all_tables()

from routers.auth import router as auth_router
from routers.export import router as export_router
from routers.ai import router as ai_router
from routers.billing import router as billing_router
from routers.import_router import router as import_router
from routers.plan import router as plan_router
from routers.practice import router as practice_router
from routers.review import router as review_router
from routers.settings import router as settings_router
from routers.subjects import router as subjects_router
from routers.trash import router as trash_router
from routers.wrong import router as wrong_router
from routers.friends import router as friends_router
from routers.messages import router as messages_router
from routers.realtime import router as realtime_router
from routers.share import router as share_router

app = FastAPI(
    title="习题库管理系统",
    description="FastAPI + SQLAlchemy + SQLite",
    version="1.0.0",
)

allowed_origins = [
    origin.strip()
    for origin in getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

if not allowed_origins:
    import logging
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]
    logging.warning(
        "ALLOWED_ORIGINS environment variable is empty or not set. "
        "Falling back to local development origins: %s",
        ", ".join(allowed_origins),
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
app.include_router(export_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(billing_router, prefix="/api")
app.include_router(friends_router, prefix="/api")
app.include_router(messages_router, prefix="/api")
app.include_router(share_router, prefix="/api")
app.include_router(realtime_router)

Path("uploads/avatars").mkdir(parents=True, exist_ok=True)
app.mount("/uploads/avatars", StaticFiles(directory="uploads/avatars"), name="avatars")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "exercise-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
