"""Application configuration.

Loaded once at process start via `pydantic-settings`. All values are
overridable through environment variables (see `.env.example` at the repo
root) so the same image runs unmodified across dev/staging/prod.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SHARED_SECRET = "dev-shared-secret-change-me"
_DEV_API_KEY_PEPPER = "dev-api-key-pepper-change-me"


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
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    upload_dir: str = Field(default="./data/uploads")
    upload_max_bytes: int = Field(default=2_000_000, ge=1)

    # --- Auth (see app/core/security.py) ---
    api_shared_secret: str = Field(
        default=_DEV_SHARED_SECRET,
        description=(
            "Shared bearer token for development and test. Refused outside those "
            "environments; production resolves a peppered HMAC-SHA256 per-tenant API key."
        ),
    )
    api_key_pepper: str = Field(
        default=_DEV_API_KEY_PEPPER,
        description=(
            "Server-side pepper for tenant API key hashes. Refused at its default "
            "outside development and test. Changing it invalidates stored key hashes."
        ),
    )


def refuse_default_secrets(settings: Settings) -> None:
    """Refuse the shipped secret and pepper outside development and test."""
    if settings.environment in {"development", "test"}:
        return
    missing: list[str] = []
    if settings.api_shared_secret == _DEV_SHARED_SECRET:
        missing.append("EQUICLAIM_API_SHARED_SECRET")
    if settings.api_key_pepper == _DEV_API_KEY_PEPPER:
        missing.append("EQUICLAIM_API_KEY_PEPPER")
    if missing:
        names = " and ".join(missing)
        raise RuntimeError(f"refusing to start: set {names} outside development and test")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide `Settings` singleton (cached)."""
    return Settings()
