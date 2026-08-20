"""
app/main.py
───────────
FastAPI application entry point.

This file:
  1. Creates the FastAPI app instance.
  2. Adds CORS middleware (so the React frontend can call the backend).
  3. Registers all API routers (one per feature module).
  4. Creates DB tables on startup (dev only — in production, use Alembic migrations).

WHY CORS?
  Your frontend runs on http://localhost:5173.
  Your backend runs on http://localhost:8000.
  Browsers block cross-origin requests by default for security.
  CORS middleware tells the browser: "Yes, requests from 5173 are allowed."
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import health
from app.db.base import Base
from app.db.session import engine


# ── Lifespan: startup / shutdown logic ───────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs at startup (before yield) and shutdown (after yield).

    At startup: Create all DB tables if they don't exist.
    This is fine for development. For production, use Alembic migrations
    instead — they handle incremental schema changes safely.
    """
    print(f"🚀 Starting {settings.APP_NAME} [{settings.APP_ENV}]")
    Base.metadata.create_all(bind=engine)   # Create tables for all models
    print("✅ Database tables ready")
    yield
    print("🛑 Shutting down...")


# ── App instance ─────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered study platform for uploading materials and generating study content.",
    version="0.1.0",
    docs_url="/docs",        # Swagger UI — visit http://localhost:8000/docs
    redoc_url="/redoc",      # Alternative docs
    lifespan=lifespan,
)


# ── CORS Middleware ───────────────────────────────────────────────
# In development, we allow all origins. In production, restrict to your domain.
origins = (
    ["*"]
    if settings.APP_ENV == "development"
    else ["https://your-production-domain.com"]  # Update in Phase 8
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],     # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],     # Authorization, Content-Type, etc.
)


# ── Register Routers ──────────────────────────────────────────────
# Each feature module has its own router. We include them here with a prefix.
# In later phases, add:  app.include_router(auth.router, prefix="/api/v1")

app.include_router(health.router, prefix="/api/v1")

# ── Root endpoint ─────────────────────────────────────────────────
@app.get("/", tags=["Root"])
def root():
    """Simple root endpoint — confirms the API is alive."""
    return {"message": f"Welcome to {settings.APP_NAME} API 🎓"}
