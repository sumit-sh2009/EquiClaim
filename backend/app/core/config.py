"""Application configuration.

Loaded once at process start via `pydantic-settings`. All values are
overridable through environment variables (see `.env.example` at the repo
root) so the same image runs unmodified across dev/staging/prod.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide settings, sourced from environment / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="EQUICLAIM_",
        extra="ignore",
    )

    # --- Postgres ---
    database_url: str = Field(
        default="postgresql://equiclaim:equiclaim@localhost:5432/equiclaim",
        description=(
            "libpq connection string used by both the LangGraph "
            "AsyncPostgresSaver and the application repository layer."
        ),
    )
    db_pool_min_size: int = Field(default=2, ge=0)
    db_pool_max_size: int = Field(default=20, ge=1)

    # --- LangGraph ---
    graph_recursion_limit: int = Field(
        default=50,
        description="Hard backstop beneath the 3-iteration evaluator-optimizer cap.",
    )
    evaluator_max_iterations: int = Field(default=3, ge=1)

    # --- App ---
    environment: str = Field(default="development")
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    upload_dir: str = Field(default="./data/uploads")

    # --- Auth (Phase 8 stub — see app/core/security.py) ---
    api_shared_secret: str = Field(
        default="dev-shared-secret-change-me",
        description="Placeholder bearer token for local/dev tenant auth (Phase 8 hardens this).",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide `Settings` singleton (cached)."""
    return Settings()
