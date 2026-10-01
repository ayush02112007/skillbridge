"""Digital portfolio and resume builder."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentStudent, DbSession, OptionalUser
from app.core.exceptions import NotFoundError
from app.models.enums import Visibility
from app.models.portfolio import Portfolio, Resume
from app.models.profile import StudentProfile
from app.schemas.common import Envelope, ErrorResponse, MessageResponse, ok
from app.schemas.document import (
    PortfolioOut,
    PortfolioUpdate,
    PublicPortfolioOut,
    ResumeIn,
    ResumeOut,
)
from app.services import portfolio as portfolio_service
from app.services import student as student_service

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

ERRORS: dict[int | str, dict[str, Any]] = {
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
}


@router.get(
    "/me",
    response_model=Envelope[PortfolioOut],
    responses=ERRORS,
    summary="My portfolio settings",
)
async def my_portfolio(student: CurrentStudent, db: DbSession) -> dict:
    portfolio = await portfolio_service.get_or_create(db, student)
    completion = await student_service.compute_profile_completion(db, student)
    portfolio.completion_percentage = completion["percentage"]
    await db.commit()
    return ok(PortfolioOut.model_validate(portfolio))


@router.patch(
    "/me",
    response_model=Envelope[PortfolioOut],
    responses=ERRORS,
    summary="Update my portfolio",
    description=(
        "Controls what the public portfolio shows.\n\n"
        "`visibility` is the privacy switch: **PUBLIC** is reachable by anyone "
        "with the link, **INSTITUTION_ONLY** is limited to the student's own "
        "institution plus companies they have applied to, and **PRIVATE** is "
        "visible only to the student. Contact details stay hidden unless "
        "explicitly enabled."
    ),
)
async def update_my_portfolio(
    payload: PortfolioUpdate, student: CurrentStudent, db: DbSession
) -> dict:
    portfolio = await portfolio_service.get_or_create(db, student)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("featured_project_ids"):
        changes["featured_project_ids"] = [
            str(v) for v in changes["featured_project_ids"]
        ]
    for field, value in changes.items():
        setattr(portfolio, field, value)
    if "visibility" in changes:
        student.portfolio_visibility = portfolio.visibility
        if portfolio.visibility != Visibility.PRIVATE and portfolio.published_at is None:
            portfolio.published_at = datetime.now(UTC)
    await db.commit()
    return ok(PortfolioOut.model_validate(portfolio))


@router.get(
    "/{slug}",
    response_model=Envelope[PublicPortfolioOut],
    responses=ERRORS,
    summary="View a portfolio",
    description=(
        "The public-facing portfolio at `/portfolio/{slug}`.\n\n"
        "Respects the owner's visibility setting: a private portfolio returns "
        "404 rather than disclosing that it exists, and contact details are "
        "omitted unless the owner opted in. Verified credentials are marked so "
        "a viewer can tell claims apart from confirmed facts."
    ),
)
async def public_portfolio(
    slug: str, db: DbSession, viewer: OptionalUser = None
) -> dict:
    portfolio = (
        await db.execute(select(Portfolio).where(Portfolio.slug == slug))
    ).scalar_one_or_none()
    if portfolio is None:
        raise NotFoundError("Portfolio not found", code="PORTFOLIO_NOT_FOUND")
    student = (
        await db.execute(
            select(StudentProfile)
            .where(StudentProfile.id == portfolio.student_id)
            .options(selectinload(StudentProfile.user))
        )
    ).scalar_one_or_none()
    if student is None or student.deleted_at is not None:
        raise NotFoundError("Portfolio not found", code="PORTFOLIO_NOT_FOUND")

    if not await portfolio_service.can_view(db, portfolio, student, viewer):
        raise NotFoundError("Portfolio not found", code="PORTFOLIO_NOT_FOUND")

    view = await portfolio_service.build_public_view(db, student, portfolio)
    if viewer is None or viewer.id != student.user_id:
        portfolio.view_count += 1
        await db.commit()
    return ok(PublicPortfolioOut.model_validate(view))


# ------------------------------------------------------- resume builder ----
resumes_router = APIRouter(prefix="/resumes", tags=["Portfolio"])


@resumes_router.get(
    "",
    response_model=Envelope[list[ResumeOut]],
    responses=ERRORS,
    summary="My resumes",
)
async def list_resumes(student: CurrentStudent, db: DbSession) -> dict:
    rows = (
        await db.execute(
            select(Resume)
            .where(Resume.student_id == student.id)
            .order_by(Resume.is_default.desc(), Resume.updated_at.desc())
        )
    ).scalars().all()
    return ok([ResumeOut.model_validate(r) for r in rows])


@resumes_router.get(
    "/prefill",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Pre-fill from my profile",
    description="Builds resume content from data already on the profile. Only "
                "existing data is used - nothing is generated to fill gaps.",
)
async def prefill_resume(student: CurrentStudent, db: DbSession) -> dict:
    return ok(await portfolio_service.resume_content_from_profile(db, student))


@resumes_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[ResumeOut],
    responses=ERRORS,
    summary="Create a resume",
)
async def create_resume(
    payload: ResumeIn, student: CurrentStudent, db: DbSession
) -> dict:
    if payload.is_default:
        for existing in (
            await db.execute(select(Resume).where(Resume.student_id == student.id))
        ).scalars():
            existing.is_default = False
    resume = Resume(
        student_id=student.id,
        title=payload.title,
        template=payload.template,
        content=payload.content.model_dump(),
        target_job_role_id=payload.target_job_role_id,
        is_default=payload.is_default,
    )
    db.add(resume)
    await db.commit()
    return ok(ResumeOut.model_validate(resume))


@resumes_router.put(
    "/{resume_id}",
    response_model=Envelope[ResumeOut],
    responses=ERRORS,
    summary="Update a resume",
)
async def update_resume(
    resume_id: uuid.UUID, payload: ResumeIn, student: CurrentStudent, db: DbSession
) -> dict:
    resume = (
        await db.execute(
            select(Resume).where(
                Resume.id == resume_id, Resume.student_id == student.id
            )
        )
    ).scalar_one_or_none()
    if resume is None:
        raise NotFoundError("Resume not found", code="RESUME_NOT_FOUND")
    if payload.is_default and not resume.is_default:
        for existing in (
            await db.execute(select(Resume).where(Resume.student_id == student.id))
        ).scalars():
            existing.is_default = False
    resume.title = payload.title
    resume.template = payload.template
    resume.content = payload.content.model_dump()
    resume.target_job_role_id = payload.target_job_role_id
    resume.is_default = payload.is_default
    await db.commit()
    return ok(ResumeOut.model_validate(resume))


@resumes_router.delete(
    "/{resume_id}",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Delete a resume",
)
async def delete_resume(
    resume_id: uuid.UUID, student: CurrentStudent, db: DbSession
) -> MessageResponse:
    from sqlalchemy import delete

    result = await db.execute(
        delete(Resume).where(Resume.id == resume_id, Resume.student_id == student.id)
    )
    if not result.rowcount:
        raise NotFoundError("Resume not found", code="RESUME_NOT_FOUND")
    await db.commit()
    return MessageResponse(message="Resume deleted")


@resumes_router.get(
    "/{resume_id}/export",
    responses={**ERRORS, 200: {"content": {"application/pdf": {}}}},
    summary="Export a resume as PDF",
    description="Renders the saved content with the chosen template. Only data "
                "the student entered is rendered.",
)
async def export_resume(
    resume_id: uuid.UUID,
    student: CurrentStudent,
    db: DbSession,
    template: Annotated[str | None, Query(description="Override the saved template")] = None,
) -> StreamingResponse:
    resume = (
        await db.execute(
            select(Resume).where(
                Resume.id == resume_id, Resume.student_id == student.id
            )
        )
    ).scalar_one_or_none()
    if resume is None:
        raise NotFoundError("Resume not found", code="RESUME_NOT_FOUND")

    pdf = portfolio_service.render_resume_pdf(
        resume.content or {}, template or resume.template
    )
    resume.last_exported_at = datetime.now(UTC)
    await db.commit()

    safe_title = "".join(
        c for c in (resume.title or "resume") if c.isalnum() or c in "-_ "
    ).strip().replace(" ", "-") or "resume"
    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.pdf"',
            "X-Content-Type-Options": "nosniff",
        },
    )

