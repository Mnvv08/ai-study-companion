"""
app/core/config.py
──────────────────
Central configuration using pydantic-settings.

WHY pydantic-settings?
  - Reads from environment variables (or .env file) automatically.
  - Each setting is type-validated — if SECRET_KEY is missing, the app
    crashes at startup with a clear error, not silently mid-request.
  - One import (`from app.core.config import settings`) gives any module
    access to all config. No scattered os.getenv() calls.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    All application settings loaded from environment variables.
    Field(...) means the variable is REQUIRED — app won't start without it.
    Field(default=...) means it's optional with a fallback.
    """

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = Field(default="AI Study Companion")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql://studyuser:changeme@postgres:5432/study_companion",
        description="Full PostgreSQL connection URL (e.g., postgresql://user:pass@host:5432/dbname)"
    )

    # ── JWT ──────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-replace-in-env-32bytes",
        description="Secret key used to sign JWT tokens. Must be kept private in production."
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    # ── Groq (Text Generation + Embeddings) ────────────────────────
    # Groq's API is OpenAI-compatible, so we reuse the openai Python
    # SDK but point it at Groq's base URL for both chat and embeddings.
    GROQ_API_KEY: str = Field(
        default="gsk_placeholder",
        description="Groq API key for chat completions and embeddings."
    )
    GROQ_BASE_URL: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Groq API base URL (OpenAI-compatible endpoint)."
    )
    GROQ_CHAT_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq-hosted model for text generation (notes, flashcards, MCQs, Q&A)."
    )
    GROQ_EMBEDDING_MODEL: str = Field(
        default="nomic-embed-text-v1_5",
        description="Groq-hosted model for vector embeddings."
    )

    # ── ChromaDB ─────────────────────────────────────────────────
    CHROMA_HOST: str = Field(default="chromadb")
    CHROMA_PORT: int = Field(default=8000)

    # ── File Uploads ─────────────────────────────────────────────
    UPLOAD_DIR: str = Field(default="./uploads")
    MAX_UPLOAD_SIZE_MB: int = Field(default=20)
    ALLOWED_EXTENSIONS: str = Field(default="pdf,pptx")

    @property
    def allowed_extensions_list(self) -> list[str]:
        """Parse comma-separated string into a list: 'pdf,pptx' → ['pdf', 'pptx']"""
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB to bytes for comparison against uploaded file size."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # ── Pydantic-settings config ──────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",           # Load from .env file in the backend/ directory
        env_file_encoding="utf-8",
        case_sensitive=True,       # SECRET_KEY ≠ secret_key
        extra="ignore",            # Ignore extra vars in .env (won't crash)
    )


# ── Singleton instance ────────────────────────────────────────────
# All modules import this single object. This runs once at startup.
# If required fields are missing, pydantic raises ValidationError here.
settings = Settings()
