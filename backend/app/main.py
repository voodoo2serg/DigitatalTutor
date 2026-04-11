from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api import users, works, files, communications, ai_analysis

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown

app = FastAPI(
    title="DigitalTutor API",
    description="Система управления учебными проектами",
    version="1.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(works.router, prefix="/api/v1/works", tags=["works"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(communications.router, prefix="/api/v1/communications", tags=["communications"])
app.include_router(ai_analysis.router, prefix="/api/v1/ai", tags=["ai"])

@app.get("/")
async def root():
    return {
        "service": "DigitalTutor API",
        "version": "1.1.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
