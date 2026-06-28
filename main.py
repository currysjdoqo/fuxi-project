from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers.auth import router as auth_router
from routers.export import router as export_router
from routers.ai import router as ai_router
from routers.import_router import router as import_router
from routers.plan import router as plan_router
from routers.practice import router as practice_router
from routers.review import router as review_router
from routers.settings import router as settings_router
from routers.subjects import router as subjects_router
from routers.trash import router as trash_router
from routers.wrong import router as wrong_router

app = FastAPI(
    title="习题库管理系统",
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
app.include_router(export_router, prefix="/api")
app.include_router(ai_router, prefix="/api")

Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "exercise-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
