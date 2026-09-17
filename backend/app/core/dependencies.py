"""FastAPI dependency-injection helpers.

Every dependency reads shared resources off `request.app.state` (populated
once at startup by the `lifespan` context manager in `app/main.py`) rather
than importing module-level singletons — this keeps route handlers trivially
testable with `app.dependency_overrides`.
"""

from __future__ import annotations

from fastapi import Request

from app.core.config import Settings
from app.repositories.claims_repository import ClaimsRepository
from app.repositories.mrf_repository import MrfRepository


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_pool(request: Request):
    return request.app.state.pool


def get_graph(request: Request):
    return request.app.state.graph


def get_claims_repository(request: Request) -> ClaimsRepository:
    return ClaimsRepository(request.app.state.pool)


def get_mrf_repository(request: Request) -> MrfRepository:
    return MrfRepository(request.app.state.pool)
