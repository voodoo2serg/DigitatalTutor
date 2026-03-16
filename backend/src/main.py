"""
StudoBot API - FastAPI Application
Система управления заданиями для преподавателя
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from src.config import settings
from src.database import init_db, close_db
from src.routes import students, submissions, files, reviews, notifications, webhooks

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Starting StudoBot API...")

    # Инициализация базы данных
    await init_db()
    logger.info("Database initialized")

    # Инициализация MinIO
    # await init_minio()
    # logger.info("MinIO initialized")

    yield

    # Закрытие соединений
    await close_db()
    logger.info("StudoBot API stopped")


app = FastAPI(
    title="StudoBot API",
    description="Система управления заданиями для преподавателя",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роуты
app.include_router(students.router, prefix="/api/students", tags=["Students"])
app.include_router(submissions.router, prefix="/api/submissions", tags=["Submissions"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["Reviews"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "StudoBot API",
        "version": "0.1.0",
        "docs": "/docs",
    }


# Глобальный обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
