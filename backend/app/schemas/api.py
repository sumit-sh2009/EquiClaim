"""Transport-layer request/response DTOs for `app/routers/claims.py`.

Kept separate from the domain models in `app/schemas/` (which model the
LangGraph state / audit artifacts themselves) so API versioning changes
never ripple into the audited domain contracts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.claim import ClaimStatus


class ClaimCreateResponse(BaseModel):
    claim_id: str
    thread_id: str
    status: ClaimStatus


class ClaimStatusResponse(BaseModel):
    claim_id: str
    status: ClaimStatus
    eval_status: str | None = None
    eval_iteration: int | None = None
    next_nodes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    eval_feedback: list[str] = Field(default_factory=list)
    updated_at: datetime


class ClaimListItem(BaseModel):
    claim_id: str
    status: ClaimStatus
    hospital_ccn: str | None
    created_at: datetime
    updated_at: datetime


class ClaimListResponse(BaseModel):
    claims: list[ClaimListItem]


class ResumeRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    reviewer: str | None = None
    notes: str | None = None
