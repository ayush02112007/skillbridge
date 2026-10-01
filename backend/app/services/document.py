"""Document management: upload, access control, extraction and resume analysis."""
from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.service import get_ai_service
from app.ai.text import parse_document
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.document import Document, DocumentAccessGrant
from app.models.enums import (
    DocumentType,
    ProficiencyLevel,
    RoleName,
    ScanStatus,
    SkillSource,
    Visibility,
)
from app.models.portfolio import ResumeAnalysis
from app.models.profile import StudentProfile
from app.models.skill import JobRole
from app.models.user import User
from app.services import skill as skill_service
from app.services import storage as storage_service

log = get_logger("documents")


def _now() -> datetime:
    return datetime.now(UTC)


async def create_document(
    db: AsyncSession,
    *,
    owner: User,
    document_type: DocumentType,
    title: str,
    filename: str,
    content_type: str,
    data: bytes,
    visibility: Visibility = Visibility.PRIVATE,
    meta: dict[str, Any] | None = None,
) -> Document:
    stored = await storage_service.store_upload(
        owner_id=owner.id, kind=document_type.value, filename=filename,
        content_type=content_type, data=data,
    )
    scan_status, scan_detail = await storage_service.scan_for_malware(data, filename)
    if scan_status == "INFECTED":
        await storage_service.get_storage().delete(stored.storage_key)
        from app.core.exceptions import UnsupportedMediaTypeError

        raise UnsupportedMediaTypeError(
            "This file was rejected by the malware scanner", code="FILE_REJECTED"
        )

    document = Document(
        owner_id=owner.id,
        document_type=document_type,
        title=(title or filename)[:220],
        original_filename=storage_service.sanitise_filename(filename),
        storage_key=stored.storage_key,
        storage_provider=stored.provider,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
        visibility=visibility,
        scan_status=ScanStatus(scan_status),
        scan_detail=scan_detail,
        meta=meta or {},
    )
    db.add(document)
    await db.flush()

    if document_type == DocumentType.RESUME:
        text = extract_text(data, stored.content_type)
        document.extracted_text = text
        document.extraction_status = "DONE" if text else "UNSUPPORTED"
        # The newest resume becomes the primary one used when applying.
        await db.execute(
            Document.__table__.update()
            .where(
                Document.owner_id == owner.id,
                Document.document_type == DocumentType.RESUME,
                Document.id != document.id,
            )
            .values(is_primary_resume=False)
        )
        document.is_primary_resume = True

    await db.flush()
    log.info(
        "documents.uploaded",
        document_id=str(document.id), type=document_type.value,
        size=stored.size_bytes, scan=scan_status,
    )
    return document


def extract_text(data: bytes, content_type: str) -> str:
    """Best-effort text extraction. Never raises - an unreadable file is not an error."""
    try:
        if content_type == "application/pdf":
            try:
                from pypdf import PdfReader  # type: ignore[import-not-found]
            except ImportError:
                return ""
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((page.extract_text() or "") for page in reader.pages)[:60000]
        if content_type.endswith("wordprocessingml.document"):
            try:
                import docx  # type: ignore[import-not-found]
            except ImportError:
                return ""
            document = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in document.paragraphs)[:60000]
        if content_type.startswith("text/"):
            return data.decode("utf-8", errors="ignore")[:60000]
    except Exception as exc:  # pragma: no cover - malformed input
        log.warning("documents.extraction_failed", error=str(exc)[:160])
    return ""


# ------------------------------------------------------- access control ----
async def can_access(db: AsyncSession, document: Document, user: User) -> bool:
    """Who may read a document.

    Private by default. Access is granted to the owner, to platform admins, to
    anyone holding an explicit unexpired grant, and to recruiters at a company
    the owner has actually applied to (scoped to the resume attached to that
    application).
    """
    if document.owner_id == user.id:
        return True
    if RoleName.SUPER_ADMIN.value in user.role_names:
        return True
    if document.visibility == Visibility.PUBLIC:
        return True

    grant = (
        await db.execute(
            select(DocumentAccessGrant).where(
                DocumentAccessGrant.document_id == document.id,
                DocumentAccessGrant.granted_to_user_id == user.id,
                DocumentAccessGrant.revoked_at.is_(None),
                or_(
                    DocumentAccessGrant.expires_at.is_(None),
                    DocumentAccessGrant.expires_at > _now(),
                ),
            )
        )
    ).scalar_one_or_none()
    if grant is not None:
        return True

    if user.company_id and set(user.role_names) & {
        RoleName.INDUSTRY_RECRUITER.value, RoleName.INDUSTRY_ADMIN.value
    }:
        from app.models.application import Application
        from app.models.opportunity import Opportunity

        attached = (
            await db.execute(
                select(func.count())
                .select_from(Application)
                .join(Opportunity, Opportunity.id == Application.opportunity_id)
                .where(
                    Application.resume_document_id == document.id,
                    Opportunity.company_id == user.company_id,
                )
            )
        ).scalar_one()
        if attached:
            return True

    if (
        document.visibility == Visibility.INSTITUTION_ONLY
        and RoleName.INSTITUTION_ADMIN.value in user.role_names
    ):
        owner_profile = (
            await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == document.owner_id)
            )
        ).scalar_one_or_none()
        if owner_profile and owner_profile.institution_id == user.institution_id:
            return True
    return False


async def get_for_user(
    db: AsyncSession, document_id: uuid.UUID, user: User
) -> Document:
    document = (
        await db.execute(
            select(Document).where(
                Document.id == document_id, Document.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if document is None:
        raise NotFoundError("Document not found", code="DOCUMENT_NOT_FOUND")
    if not await can_access(db, document, user):
        # Do not disclose existence to someone with no right to the file.
        raise NotFoundError("Document not found", code="DOCUMENT_NOT_FOUND")
    return document


# ------------------------------------------------------ resume analysis ----
async def analyse_resume(
    db: AsyncSession,
    *,
    document: Document,
    student: StudentProfile,
    job_role: JobRole | None,
    import_skills: bool = False,
) -> ResumeAnalysis:
    """Parse a resume, compare it to a target role and suggest improvements.

    Nothing is invented: skills come from exact taxonomy matches in the text,
    and experience/education are read from the document's own sections.
    """
    text = document.extracted_text or ""
    if not text:
        data = await storage_service.get_storage().get(document.storage_key)
        text = extract_text(data, document.content_type)
        document.extracted_text = text
        document.extraction_status = "DONE" if text else "UNSUPPORTED"

    vocabulary = await skill_service.get_skill_vocabulary(db)
    parsed = parse_document(text, vocabulary)

    extracted_skills = [
        {
            "skill_id": hit.skill_id,
            "skill_name": hit.skill_name,
            "matched_term": hit.matched_term,
            "occurrences": hit.occurrences,
            "is_aspirational": hit.is_aspirational,
        }
        for hit in parsed.skills
    ]

    matched: list[str] = []
    missing: list[str] = []
    if job_role is not None:
        requirements = await skill_service.load_role_requirements(db, job_role.id)
        found_ids = {hit.skill_id for hit in parsed.skills if not hit.is_aspirational}
        for requirement in requirements:
            (matched if requirement.skill_id in found_ids else missing).append(
                requirement.skill_name
            )

    ats_score = compute_ats_score(parsed)
    suggestions, analysed_by = await get_ai_service().resume_suggestions(
        parsed,
        target_role=job_role.title if job_role else None,
        missing_skills=missing,
        ats_score=ats_score,
    )

    analysis = ResumeAnalysis(
        student_id=student.id,
        document_id=document.id,
        job_role_id=job_role.id if job_role else None,
        extracted_skills=extracted_skills,
        extracted_education=parsed.education,
        extracted_experience=parsed.experience,
        extracted_projects=parsed.projects,
        extracted_certifications=parsed.certifications,
        matched_skills=matched,
        missing_skills=missing,
        suggestions=suggestions,
        ats_score=ats_score,
        analyzed_by=analysed_by,
    )
    db.add(analysis)

    if import_skills:
        # Resume evidence is weaker than an assessment, and is recorded as such.
        for hit in parsed.skills:
            if hit.is_aspirational:
                continue
            level = (
                ProficiencyLevel.INTERMEDIATE
                if hit.occurrences >= 3
                else ProficiencyLevel.BEGINNER
            )
            await skill_service.upsert_student_skill(
                db, student.id, uuid.UUID(hit.skill_id), level=level,
                source=SkillSource.RESUME,
                evidence={
                    "document_id": str(document.id),
                    "matched_term": hit.matched_term,
                    "occurrences": hit.occurrences,
                },
            )
        await skill_service.refresh_student_readiness(db, student)

    await db.flush()
    return analysis


def compute_ats_score(parsed: Any) -> int:
    """A transparent proxy for machine-readability, 0-100.

    Each component is a concrete, checkable property of the document rather
    than an opaque model output, so the suggestions can name exactly what to fix.
    """
    score = 0
    sections = parsed.sections or {}
    if sections.get("skills"):
        score += 20
    if sections.get("experience"):
        score += 20
    if sections.get("education"):
        score += 15
    if sections.get("projects"):
        score += 10
    if parsed.emails:
        score += 10
    if parsed.urls:
        score += 5
    if 250 <= parsed.word_count <= 900:
        score += 10
    elif parsed.word_count:
        score += 4
    if len(parsed.skills) >= 6:
        score += 10
    elif parsed.skills:
        score += 5
    return min(100, score)
