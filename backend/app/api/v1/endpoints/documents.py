"""Secure document upload, access control and download."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import ActiveUser, CurrentStudent, DbSession
from app.core.exceptions import (
    NotFoundError,
    PayloadTooLargeError,
    PermissionDeniedError,
    ValidationError,
)
from app.models.document import Document, DocumentAccessGrant
from app.models.enums import AuditAction, DocumentType, Visibility
from app.models.portfolio import ResumeAnalysis
from app.models.skill import JobRole
from app.models.user import User
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    MessageResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.schemas.document import (
    DocumentGrantIn,
    DocumentOut,
    DocumentUpdate,
    ResumeAnalysisOut,
    ResumeAnalysisRequest,
)
from app.services import audit
from app.services import document as document_service
from app.services import storage as storage_service

router = APIRouter(prefix="/documents", tags=["Documents"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
    413: {"model": ErrorResponse, "description": "File too large"},
    415: {"model": ErrorResponse, "description": "Unsupported file type"},
}


async def _with_url(document: Document) -> DocumentOut:
    data = DocumentOut.model_validate(document)
    data.download_url = await storage_service.get_storage().signed_url(
        document.storage_key,
        filename=document.original_filename,
        expires=settings.SIGNED_URL_EXPIRE_SECONDS,
    )
    return data


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[DocumentOut],
    responses=ERRORS,
    summary="Upload a document",
    description=(
        "Uploads a resume, certificate, mark sheet or other supporting document.\n\n"
        "**Validation applied:** allow-listed MIME types (PDF, DOCX, PNG, JPG), "
        "a size limit, a dangerous-extension block list, and a magic-byte check "
        "so a renamed executable cannot masquerade as a PDF. Files are stored "
        "under an opaque generated key - no client-supplied path ever reaches "
        "the filesystem - and are private by default."
    ),
)
async def upload_document(
    request: Request,
    db: DbSession,
    user: ActiveUser,
    file: Annotated[UploadFile, File(description="The file to upload")],
    document_type: Annotated[DocumentType, Form()] = DocumentType.OTHER,
    title: Annotated[str, Form(max_length=220)] = "",
    visibility: Annotated[Visibility, Form()] = Visibility.PRIVATE,
) -> dict:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise PayloadTooLargeError(
            f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit"
        )

    document = await document_service.create_document(
        db, owner=user, document_type=document_type,
        title=title or file.filename or "Document",
        filename=file.filename or "document", content_type=file.content_type or "",
        data=data, visibility=visibility,
    )
    await audit.record(
        db, AuditAction.DOCUMENT_UPLOAD, actor=user, resource_type="document",
        resource_id=document.id,
        description=f"Uploaded {document_type.value}: {document.title}",
        request=request, meta={"size_bytes": document.size_bytes},
    )
    await db.commit()
    return ok(await _with_url(document))


@router.get(
    "",
    response_model=Page[DocumentOut],
    responses=ERRORS,
    summary="My documents",
)
async def list_documents(
    db: DbSession,
    user: ActiveUser,
    page: Annotated[PaginationParams, Depends(pagination)],
    document_type: DocumentType | None = None,
) -> Page[DocumentOut]:
    stmt = select(Document).where(
        Document.owner_id == user.id, Document.deleted_at.is_(None)
    )
    if document_type:
        stmt = stmt.where(Document.document_type == document_type)
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Document.created_at.desc()).offset(page.offset).limit(page.limit)
        )
    ).scalars().all()
    items = [await _with_url(row) for row in rows]
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/download",
    responses={**ERRORS, 200: {"content": {"application/octet-stream": {}}}},
    summary="Download via signed token",
    description=(
        "Redeems the short-lived signed token embedded in `download_url`. The "
        "token is HMAC-signed and expires, so a leaked URL stops working - and "
        "it never reveals the underlying storage path."
    ),
)
async def download_by_token(token: str, db: DbSession) -> StreamingResponse:
    key = storage_service.verify_download_token(token)
    if key is None:
        raise PermissionDeniedError(
            "This download link is invalid or has expired", code="DOWNLOAD_TOKEN_INVALID"
        )
    document = (
        await db.execute(select(Document).where(Document.storage_key == key))
    ).scalar_one_or_none()
    if document is None or document.deleted_at is not None:
        raise NotFoundError("Document not found", code="DOCUMENT_NOT_FOUND")

    data = await storage_service.get_storage().get(key)
    document.download_count += 1
    document.last_accessed_at = datetime.now(UTC)
    await db.commit()
    return StreamingResponse(
        iter([data]),
        media_type=document.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.original_filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{document_id}",
    response_model=Envelope[DocumentOut],
    responses=ERRORS,
    summary="Document metadata",
    description="Returns a fresh signed URL. Access is denied - as a 404, so "
                "existence is not disclosed - to anyone without a right to the file.",
)
async def get_document(
    document_id: uuid.UUID, request: Request, db: DbSession, user: ActiveUser
) -> dict:
    document = await document_service.get_for_user(db, document_id, user)
    if document.owner_id != user.id:
        await audit.record(
            db, AuditAction.DOCUMENT_ACCESS, actor=user, resource_type="document",
            resource_id=document.id,
            description=f"Accessed another user's document ({document.document_type.value})",
            request=request,
        )
        await db.commit()
    return ok(await _with_url(document))


@router.patch(
    "/{document_id}",
    response_model=Envelope[DocumentOut],
    responses=ERRORS,
    summary="Update document metadata",
)
async def update_document(
    document_id: uuid.UUID, payload: DocumentUpdate, db: DbSession, user: ActiveUser
) -> dict:
    document = (
        await db.execute(
            select(Document).where(
                Document.id == document_id, Document.owner_id == user.id,
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundError("Document not found", code="DOCUMENT_NOT_FOUND")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("is_primary_resume"):
        await db.execute(
            Document.__table__.update()
            .where(
                Document.owner_id == user.id,
                Document.document_type == DocumentType.RESUME,
            )
            .values(is_primary_resume=False)
        )
    for field, value in changes.items():
        setattr(document, field, value)
    await db.commit()
    return ok(await _with_url(document))


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Delete a document",
    description="Soft-deletes the record and removes the stored object.",
)
async def delete_document(
    document_id: uuid.UUID, request: Request, db: DbSession, user: ActiveUser
) -> MessageResponse:
    document = (
        await db.execute(
            select(Document).where(
                Document.id == document_id, Document.owner_id == user.id,
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundError("Document not found", code="DOCUMENT_NOT_FOUND")
    document.soft_delete()
    await storage_service.get_storage().delete(document.storage_key)
    await audit.record(
        db, AuditAction.DOCUMENT_DELETE, actor=user, resource_type="document",
        resource_id=document.id, description=f"Deleted {document.title}", request=request,
    )
    await db.commit()
    return MessageResponse(message="Document deleted")


@router.post(
    "/{document_id}/grants",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Share a document",
    description="Grants one named user time-limited read access. Grants are "
                "revocable and expire by default after a week.",
)
async def grant_access(
    document_id: uuid.UUID, payload: DocumentGrantIn, db: DbSession, user: ActiveUser
) -> MessageResponse:
    document = (
        await db.execute(
            select(Document).where(
                Document.id == document_id, Document.owner_id == user.id,
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundError("Document not found", code="DOCUMENT_NOT_FOUND")
    if await db.get(User, payload.granted_to_user_id) is None:
        raise NotFoundError("User not found", code="USER_NOT_FOUND")

    expires = (
        datetime.now(UTC) + timedelta(hours=payload.expires_in_hours)
        if payload.expires_in_hours
        else None
    )
    db.add(
        DocumentAccessGrant(
            document_id=document.id,
            granted_to_user_id=payload.granted_to_user_id,
            granted_by_user_id=user.id,
            reason=payload.reason,
            expires_at=expires,
        )
    )
    await db.commit()
    return MessageResponse(message="Access granted")


@router.delete(
    "/{document_id}/grants/{user_id}",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Revoke shared access",
)
async def revoke_access(
    document_id: uuid.UUID, user_id: uuid.UUID, db: DbSession, user: ActiveUser
) -> MessageResponse:
    grants = (
        await db.execute(
            select(DocumentAccessGrant)
            .join(Document, Document.id == DocumentAccessGrant.document_id)
            .where(
                DocumentAccessGrant.document_id == document_id,
                DocumentAccessGrant.granted_to_user_id == user_id,
                DocumentAccessGrant.revoked_at.is_(None),
                Document.owner_id == user.id,
            )
        )
    ).scalars().all()
    if not grants:
        raise NotFoundError("No active grant found", code="GRANT_NOT_FOUND")
    for grant in grants:
        grant.revoked_at = datetime.now(UTC)
    await db.commit()
    return MessageResponse(message="Access revoked")


@router.post(
    "/{document_id}/analyse",
    response_model=Envelope[ResumeAnalysisOut],
    responses=ERRORS,
    summary="Analyse a resume",
    description=(
        "Extracts skills, education, experience, projects and certifications "
        "from an uploaded resume and compares them against a target role.\n\n"
        "Extraction is exact-match against the skill taxonomy, so the analysis "
        "never claims experience the document does not contain. Set "
        "`import_skills` to add what was found to your profile - recorded as "
        "resume evidence, which carries lower confidence than an assessment."
    ),
)
async def analyse_resume(
    document_id: uuid.UUID,
    payload: ResumeAnalysisRequest,
    db: DbSession,
    student: CurrentStudent,
) -> dict:
    document = (
        await db.execute(
            select(Document).where(
                Document.id == document_id, Document.owner_id == student.user_id,
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundError("Document not found", code="DOCUMENT_NOT_FOUND")
    if document.document_type != DocumentType.RESUME:
        raise ValidationError(
            "Only documents uploaded as a RESUME can be analysed",
            code="NOT_A_RESUME",
        )

    role_id = payload.job_role_id or student.target_job_role_id
    job_role = await db.get(JobRole, role_id) if role_id else None

    analysis = await document_service.analyse_resume(
        db, document=document, student=student, job_role=job_role,
        import_skills=payload.import_skills,
    )
    await db.commit()
    data = ResumeAnalysisOut.model_validate(analysis)
    data.job_role_title = job_role.title if job_role else None
    return ok(data)


@router.get(
    "/{document_id}/analyses",
    response_model=Envelope[list[ResumeAnalysisOut]],
    responses=ERRORS,
    summary="Previous analyses for a resume",
)
async def list_analyses(
    document_id: uuid.UUID, db: DbSession, student: CurrentStudent
) -> dict:
    rows = (
        await db.execute(
            select(ResumeAnalysis)
            .where(
                ResumeAnalysis.document_id == document_id,
                ResumeAnalysis.student_id == student.id,
            )
            .order_by(ResumeAnalysis.created_at.desc())
        )
    ).scalars().all()
    return ok([ResumeAnalysisOut.model_validate(r) for r in rows])
