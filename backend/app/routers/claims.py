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
from app.core.dependencies import get_claims_repository, get_graph, get_mrf_repository, get_settings_dep
from app.core.security import require_tenant
from app.graph.nodes.finalize import _build_audit_docket
from app.graph.state import initial_state
from app.repositories.claims_repository import ClaimsRepository
from app.repositories.mrf_repository import MrfRepository
from app.schemas.api import (
    ClaimCreateResponse,
    ClaimListItem,
    ClaimListResponse,
    ClaimStatusResponse,
    ResumeRequest,
)
from app.schemas.claim import DocumentType, SourceDocument
from app.services.claim_runner import (
    get_status_snapshot,
    resume_claim_graph,
    run_claim_graph,
    sync_claim_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["claims"])

_VALID_DOCUMENT_TYPES: set[DocumentType] = {"BILL", "EOB", "ITEMIZED_STATEMENT"}
_ALLOWED_UPLOAD_SUFFIXES = {".json", ".txt"}


def _assert_supported_upload(upload: UploadFile) -> str:
    """Accept a bare ``.json`` or ``.txt`` name. Paths and absolute names are rejected.

    ``Path(dir) / upload.filename`` treats an absolute filename as the whole
    destination, and ``../`` walks out of the claim folder. Only the final
    path segment is eligible, and the bytes are stored under a generated id.
    """
    raw = upload.filename or ""
    if not raw or "\x00" in raw or raw in {".", ".."} or raw != Path(raw).name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "upload filename must be a .json or .txt file",
        )
    suffix = Path(raw).suffix.lower()
    if suffix not in _ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"{raw} must be a .json or .txt file",
        )
    return raw


async def _read_upload(upload: UploadFile, *, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        block = await upload.read(64 * 1024)
        if not block:
            break
        total += len(block)
        if total > limit:
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE,
                f"upload exceeds {limit} bytes",
            )
        chunks.append(block)
    return b"".join(chunks)


@router.post("", response_model=ClaimCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_claim(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    document_types: list[str] = Form(...),
    hospital_ccn: str | None = Form(default=None),
    tenant_id: str = Depends(require_tenant),
    claims_repo: ClaimsRepository = Depends(get_claims_repository),
    mrf_repo: MrfRepository = Depends(get_mrf_repository),
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
    safe_names = [_assert_supported_upload(upload) for upload in files]

    if hospital_ccn is not None:
        hospital_ccn = hospital_ccn.strip() or None
    if hospital_ccn is not None and await mrf_repo.get_hospital(hospital_ccn=hospital_ccn) is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No price file is loaded for hospital {hospital_ccn}. "
            "Ingest a CMS machine-readable file before starting an audit.",
        )

    payloads = [
        await _read_upload(upload, limit=settings.upload_max_bytes) for upload in files
    ]

    claim_id = str(uuid.uuid4())
    thread_id = claim_id  # 1:1 mapping keeps the LangGraph thread trivially discoverable.

    await claims_repo.ensure_tenant(tenant_id=tenant_id)
    await claims_repo.create_claim(
        claim_id=claim_id, tenant_id=tenant_id, thread_id=thread_id, hospital_ccn=hospital_ccn
    )

    upload_dir = Path(settings.upload_dir) / claim_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    source_documents: list[SourceDocument] = []
    root = upload_dir.resolve()
    for upload, doc_type, safe_name, contents in zip(
        files, document_types, safe_names, payloads, strict=True
    ):
        document_id = str(uuid.uuid4())
        suffix = Path(safe_name).suffix.lower()
        dest = (upload_dir / f"{document_id}{suffix}").resolve()
        if not dest.is_relative_to(root):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "upload filename must be a .json or .txt file",
            )
        dest.write_bytes(contents)

        await claims_repo.add_document(
            document_id=document_id,
            claim_id=claim_id,
            file_ref=str(dest),
            original_filename=safe_name,
            content_type=upload.content_type or "text/plain",
            document_type=doc_type,
        )
        source_documents.append(
            SourceDocument(
                document_id=document_id,
                claim_id=claim_id,
                document_type=doc_type,  # type: ignore[arg-type]
                file_ref=str(dest),
                original_filename=safe_name,
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
        claims_repo=claims_repo,
        claim_id=claim_id,
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
    # RESUMING is the resume lock. FAILED is sticky after a crash or a failed
    # finalize — a stale checkpoint must not put the row back in progress.
    if claim.status == "RESUMING":
        return ClaimStatusResponse(
            claim_id=claim_id,
            status="RESUMING",
            eval_status=snapshot.eval_status if snapshot else None,
            eval_iteration=snapshot.eval_iteration if snapshot else None,
            next_nodes=snapshot.next_nodes if snapshot else [],
            errors=snapshot.errors if snapshot else [],
            eval_feedback=snapshot.eval_feedback if snapshot else [],
            updated_at=claim.updated_at,
        )
    if claim.status == "FAILED":
        return ClaimStatusResponse(
            claim_id=claim_id,
            status="FAILED",
            eval_status=snapshot.eval_status if snapshot else None,
            eval_iteration=snapshot.eval_iteration if snapshot else None,
            next_nodes=[],
            errors=snapshot.errors if snapshot else [],
            eval_feedback=snapshot.eval_feedback if snapshot else [],
            updated_at=claim.updated_at,
        )
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
    tenant_id: str = Depends(require_tenant),
    claims_repo: ClaimsRepository = Depends(get_claims_repository),
    graph=Depends(get_graph),
    settings: Settings = Depends(get_settings_dep),
) -> ClaimStatusResponse:
    """Human-in-the-Loop decision. The row lock is taken before finalize runs.

    ``CERTIFIED`` and ``REJECTED`` are written only after the docket is saved.
    A second call that loses the lock gets 409, including one that arrives
    while the first finalize is still running.
    """
    claim = await _load_claim_or_404(claim_id, tenant_id, claims_repo)
    snapshot = await get_status_snapshot(graph=graph, thread_id=claim.thread_id)
    if snapshot is None or snapshot.status != "AWAITING_HUMAN_REVIEW":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"claim {claim_id} is not awaiting human review "
            f"(current status: {snapshot.status if snapshot else claim.status})",
        )
    if not await claims_repo.begin_resume(claim_id=claim_id, tenant_id=tenant_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"claim {claim_id} is already being resumed or is no longer awaiting review",
        )

    saved = await resume_claim_graph(
        graph=graph,
        thread_id=claim.thread_id,
        decision=body.decision,
        reviewer=body.reviewer,
        notes=body.notes,
        settings=settings,
        claims_repo=claims_repo,
        claim_id=claim_id,
    )
    if not saved:
        return ClaimStatusResponse(
            claim_id=claim_id, status="FAILED", updated_at=datetime.now(UTC)
        )

    finished = await get_status_snapshot(graph=graph, thread_id=claim.thread_id)
    if finished is None:
        await claims_repo.update_status(claim_id=claim_id, status="FAILED")
        return ClaimStatusResponse(
            claim_id=claim_id, status="FAILED", updated_at=datetime.now(UTC)
        )
    await sync_claim_status(claims_repo=claims_repo, claim_id=claim_id, snapshot=finished)
    return ClaimStatusResponse(
        claim_id=claim_id,
        status=finished.status,
        eval_status=finished.eval_status,
        eval_iteration=finished.eval_iteration,
        next_nodes=finished.next_nodes,
        errors=finished.errors,
        eval_feedback=finished.eval_feedback,
        updated_at=datetime.now(UTC),
    )


@router.get("/{claim_id}/docket")
async def get_docket(
    claim_id: str,
    tenant_id: str = Depends(require_tenant),
    claims_repo: ClaimsRepository = Depends(get_claims_repository),
    graph=Depends(get_graph),
):
    claim = await _load_claim_or_404(claim_id, tenant_id, claims_repo)
    docket = await claims_repo.get_docket(claim_id=claim_id)
    if docket is not None:
        return docket

    # Preview only after the evaluator has certified and the graph is paused
    # for review. A mid-run checkpoint with line items is not a filing.
    snapshot = await get_status_snapshot(graph=graph, thread_id=claim.thread_id)
    if snapshot is not None and snapshot.status == "AWAITING_HUMAN_REVIEW":
        config = {"configurable": {"thread_id": claim.thread_id}}
        state = await graph.aget_state(config)
        if (
            state is not None
            and state.values
            and state.values.get("line_items")
            and state.values.get("eval_status") == "CERTIFIED"
        ):
            return _build_audit_docket(state.values, decision="PENDING")

    raise HTTPException(status.HTTP_404_NOT_FOUND, "docket not yet available for this claim")
