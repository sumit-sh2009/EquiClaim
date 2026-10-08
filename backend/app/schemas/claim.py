"""Claim-level enums and the raw source-document contract."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ClaimStatus = Literal[
    "INTAKE",
    "BENCHMARKING",
    "COMPLIANCE_REVIEW",
    "EVALUATING",
    "AWAITING_HUMAN_REVIEW",
    "RESUMING",
    "CERTIFIED",
    "REJECTED",
    "FAILED",
]

DocumentType = Literal["BILL", "EOB", "ITEMIZED_STATEMENT"]

HumanDecision = Literal["PENDING", "APPROVED", "REJECTED", "EDITED"]


class SourceDocument(BaseModel):
    """A single uploaded artifact (scanned or digital) attached to a claim."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    document_id: str
    claim_id: str
    document_type: DocumentType
    file_ref: str = Field(description="Storage path/URI of the uploaded file.")
    original_filename: str
    content_type: str
    uploaded_at: datetime
    page_count: int | None = Field(default=None, ge=1)
