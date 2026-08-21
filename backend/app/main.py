"""
app/main.py
───────────
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import health, auth, documents, files, notes, rag, generation, quizzes
from app.db.base import Base
from app.db.session import engine

# Import all models explicitly so SQLAlchemy registers their metadata
# before Base.metadata.create_all() runs in the lifespan hook.
# This is the correct pattern to avoid circular imports: models import
# Base from db/base.py (which has no model imports), and main.py
# is the single place that loads all models together.
from app.models import user, file, quiz  # noqa: F401, E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting {settings.APP_NAME} [{settings.APP_ENV}]")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables ready")
    yield
    print("🛑 Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered study platform for uploading materials and generating study content.",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
origins = (
    ["*"]
    if settings.APP_ENV == "development"
    else ["https://your-production-domain.com"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(documents.router)  # Also expose directly at /documents/upload etc.
app.include_router(files.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")
app.include_router(notes.router)  # Direct /notes/generate access
app.include_router(generation.router, prefix="/api/v1")
app.include_router(generation.router)  # Direct /flashcards/generate, /mcq/generate access
app.include_router(rag.router, prefix="/api/v1")
app.include_router(rag.router)  # Direct /qa/ask access
app.include_router(quizzes.router, prefix="/api/v1")
app.include_router(quizzes.router)  # Direct /quizzes/{quiz_id} access


@app.get("/", tags=["Root"])
def root():
    return {"message": f"Welcome to {settings.APP_NAME} API 🎓"}
