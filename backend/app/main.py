"""
app/main.py
───────────
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.rate_limiter import limiter

from app.core.config import settings
from app.api.v1 import health, auth, documents, notes, rag, generation, quizzes, analytics, users, review
# Import all models explicitly so SQLAlchemy registers their metadata.
# Models import Base from db/base.py (which imports no models), so this
# stays free of circular imports. alembic/env.py imports the same three
# modules for the same reason.
from app.models import user, file, quiz, review as review_model  # noqa: F401, E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown hook.

    Schema creation deliberately does NOT happen here. It used to call
    Base.metadata.create_all(), which creates missing tables but silently
    ignores changes to tables that already exist — so the first time a
    column was added to an existing model, production would keep running
    against the old schema and fail at query time instead of at deploy time.

    Schema is now owned by Alembic. Run `alembic upgrade head` as a release
    step before the server starts.
    """
    print(f"🚀 Starting {settings.APP_NAME} [{settings.APP_ENV}]")
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

# Rate limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
# Origins come from the ALLOWED_ORIGINS env var so that adding a new
# frontend URL is a config change on the host, not a code edit + redeploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
# Every router is mounted once, under /api/v1. Registering them a second time
# without the prefix previously produced duplicate paths in the OpenAPI schema
# and two URLs for every endpoint.
for router in (health, auth, documents, notes, generation, rag, quizzes, analytics, users, review):
    app.include_router(router.router, prefix="/api/v1")


@app.get("/", tags=["Root"])
def root():
    return {"message": f"Welcome to {settings.APP_NAME} API 🎓"}
