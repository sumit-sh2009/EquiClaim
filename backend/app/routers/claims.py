"""`/claims` APIRouter — Phase 6.

Route handlers stay deliberately thin: they never contain forensic/business
logic (that all lives in `app/graph/nodes/`), only orchestration of
(1) persisting uploads, (2) starting/resuming the compiled graph by
`thread_id`, and (3) translating graph/DB state into API DTOs.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from app.core.config import Settings
from app.core.dependencies import get_claims_repository, get_graph, get_settings_dep
from app.core.security import require_tenant
from app.graph.state import initial_state
from app.repositories.claims_repository import ClaimsRepository
from app.schemas.api import (
    ClaimCreateResponse,
    ClaimListItem,
    ClaimListResponse,
    ClaimStatusResponse,
    ResumeRequest,
)
from app.schemas.claim import DocumentType, SourceDocument
from app.services.claim_runner import get_status_snapshot, resume_claim_graph, run_claim_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["claims"])

_VALID_DOCUMENT_TYPES: set[DocumentType] = {"BILL", "EOB", "ITEMIZED_STATEMENT"}


@router.post("", response_model=ClaimCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_claim(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    document_types: list[str] = Form(...),
    hospital_ccn: str | None = Form(default=None),
    tenant_id: str = Depends(require_tenant),
    claims_repo: ClaimsRepository = Depends(get_claims_repository),
    graph=Depends(get_graph),
    settings: Settings = Depends(get_settings_dep),
) -> ClaimCreateResponse:
    """Upload bill/EOB documents and kick off an asynchronous forensic audit run."""
    if len(files) != len(document_types):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "files and document_types must have the same length"
        )
    for doc_type in document_types:
        if doc_type not in _VALID_DOCUMENT_TYPES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid document_type {doc_type!r}")

    claim_id = str(uuid.uuid4())
    thread_id = claim_id  # 1:1 mapping keeps the LangGraph thread trivially discoverable.

    await claims_repo.ensure_tenant(tenant_id=tenant_id)
    await claims_repo.create_claim(
        claim_id=claim_id, tenant_id=tenant_id, thread_id=thread_id, hospital_ccn=hospital_ccn
    )

    upload_dir = Path(settings.upload_dir) / claim_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    source_documents: list[SourceDocument] = []
    for upload, doc_type in zip(files, document_types, strict=True):
        document_id = str(uuid.uuid4())
        dest = upload_dir / f"{document_id}_{upload.filename}"
        contents = await upload.read()
        dest.write_bytes(contents)

        await claims_repo.add_document(
            document_id=document_id,
            claim_id=claim_id,
            file_ref=str(dest),
            original_filename=upload.filename or dest.name,
            content_type=upload.content_type or "text/plain",
            document_type=doc_type,
        )
        source_documents.append(
            SourceDocument(
                document_id=document_id,
                claim_id=claim_id,
                document_type=doc_type,  # type: ignore[arg-type]
                file_ref=str(dest),
                original_filename=upload.filename or dest.name,
                content_type=upload.content_type or "text/plain",
                uploaded_at=datetime.now(UTC),
            )
        )

    seed_state = initial_state(
        claim_id=claim_id, thread_id=thread_id, tenant_id=tenant_id, hospital_ccn=hospital_ccn
    )
    seed_state["source_documents"] = source_documents

    background_tasks.add_task(
        run_claim_graph,
        graph=graph,
        thread_id=thread_id,
        initial_state=seed_state,
        settings=settings,
    )

    return ClaimCreateResponse(claim_id=claim_id, thread_id=thread_id, status="INTAKE")


@router.get("", response_model=ClaimListResponse)
async def list_claims(
    tenant_id: str = Depends(require_tenant),
    claims_repo: ClaimsRepository = Depends(get_claims_repository),
) -> ClaimListResponse:
    rows = await claims_repo.list_claims(tenant_id=tenant_id)
    return ClaimListResponse(
        claims=[
            ClaimListItem(
                claim_id=row.claim_id,
                status=row.status,  # type: ignore[arg-type]
                hospital_ccn=row.hospital_ccn,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    )


async def _load_claim_or_404(
    claim_id: str, tenant_id: str, claims_repo: ClaimsRepository
):
    claim = await claims_repo.get_claim(claim_id=claim_id, tenant_id=tenant_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "claim not found")
    return claim


@router.get("/{claim_id}/status", response_model=ClaimStatusResponse)
async def get_claim_status(
    claim_id: str,
    tenant_id: str = Depends(require_tenant),
    claims_repo: ClaimsRepository = Depends(get_claims_repository),
    graph=Depends(get_graph),
) -> ClaimStatusResponse:
    claim = await _load_claim_or_404(claim_id, tenant_id, claims_repo)
    snapshot = await get_status_snapshot(graph=graph, thread_id=claim.thread_id)
    if snapshot is None:
        return ClaimStatusResponse(
            claim_id=claim_id, status=claim.status, updated_at=claim.updated_at  # type: ignore[arg-type]
        )
    if snapshot.status != claim.status:
        await claims_repo.update_status(claim_id=claim_id, status=snapshot.status)
    return ClaimStatusResponse(
        claim_id=claim_id,
        status=snapshot.status,
        eval_status=snapshot.eval_status,
        eval_iteration=snapshot.eval_iteration,
        next_nodes=snapshot.next_nodes,
        errors=snapshot.errors,
        eval_feedback=snapshot.eval_feedback,
        updated_at=datetime.now(UTC),
    )


@router.post("/{claim_id}/resume", response_model=ClaimStatusResponse)
async def resume_claim(
    claim_id: str,
    body: ResumeRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(require_tenant),
    claims_repo: ClaimsRepository = Depends(get_claims_repository),
    graph=Depends(get_graph),
    settings: Settings = Depends(get_settings_dep),
) -> ClaimStatusResponse:
    """Human-in-the-Loop decision endpoint — resumes past the `finalize_docket` interrupt."""
    claim = await _load_claim_or_404(claim_id, tenant_id, claims_repo)
    snapshot = await get_status_snapshot(graph=graph, thread_id=claim.thread_id)
    if snapshot is None or snapshot.status != "AWAITING_HUMAN_REVIEW":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"claim {claim_id} is not awaiting human review "
            f"(current status: {snapshot.status if snapshot else claim.status})",
        )

    background_tasks.add_task(
        resume_claim_graph,
        graph=graph,
        thread_id=claim.thread_id,
        decision=body.decision,
        reviewer=body.reviewer,
        notes=body.notes,
        settings=settings,
        claims_repo=claims_repo,
    )

    provisional_status = "CERTIFIED" if body.decision == "APPROVED" else "REJECTED"
    await claims_repo.update_status(claim_id=claim_id, status=provisional_status)  # type: ignore[arg-type]
    return ClaimStatusResponse(
        claim_id=claim_id,
        status=provisional_status,  # type: ignore[arg-type]
        eval_status=snapshot.eval_status,
        eval_iteration=snapshot.eval_iteration,
        next_nodes=[],
        errors=snapshot.errors,
        eval_feedback=snapshot.eval_feedback,
        updated_at=datetime.now(UTC),
    )


@router.get("/{claim_id}/docket")
async def get_docket(
    claim_id: str,
    tenant_id: str = Depends(require_tenant),
    claims_repo: ClaimsRepository = Depends(get_claims_repository),
):
    await _load_claim_or_404(claim_id, tenant_id, claims_repo)
    docket = await claims_repo.get_docket(claim_id=claim_id)
    if docket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "docket not yet available for this claim")
    return docket
