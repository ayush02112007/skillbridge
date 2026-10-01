"""Application tracking (student) and applicant review (recruiter)."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import (
    ActiveUser,
    CurrentStudent,
    DbSession,
    RecruiterCompanyId,
    RecruiterUser,
)
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.application import Application, Interview
from app.models.enums import (
    ApplicationStatus,
    AuditAction,
    OpportunityType,
    RoleName,
)
from app.models.opportunity import Opportunity
from app.models.profile import StudentProfile
from app.schemas.application import (
    ApplicantBrief,
    ApplicationFunnelOut,
    ApplicationListItem,
    ApplicationOut,
    ApplyRequest,
    BulkStatusChangeRequest,
    BulkStatusResult,
    InterviewCreate,
    InterviewFeedback,
    InterviewOut,
    OpportunityBrief,
    RecruiterNoteRequest,
    StatusChangeRequest,
    StatusHistoryOut,
    TimelineStep,
    WithdrawRequest,
)
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.schemas.opportunity import CompanyBrief
from app.services import (
    application as application_service,
)
from app.services import (
    audit,
)
from app.services import (
    opportunity as opportunity_service,
)

router = APIRouter(prefix="/applications", tags=["Applications"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Not allowed in the current state"},
}


def _opportunity_brief(opportunity: Opportunity | None) -> OpportunityBrief | None:
    if opportunity is None:
        return None
    return OpportunityBrief(
        id=opportunity.id,
        title=opportunity.title,
        opportunity_type=opportunity.opportunity_type,
        location_city=opportunity.location_city,
        work_mode=opportunity.work_mode.value,
        application_deadline=opportunity.application_deadline,
        company=(
            CompanyBrief.model_validate(opportunity.company)
            if opportunity.company
            else None
        ),
    )


def _applicant_brief(student: StudentProfile | None) -> ApplicantBrief | None:
    if student is None:
        return None
    user = student.user
    return ApplicantBrief(
        student_id=student.id,
        user_id=student.user_id,
        full_name=user.full_name if user else "",
        email=user.email if user else None,
        avatar_url=user.avatar_url if user else None,
        headline=student.headline,
        city=student.city,
        degree=student.degree.value if student.degree else None,
        graduation_year=student.graduation_year,
        cgpa=student.cgpa,
        portfolio_slug=student.portfolio_slug,
        skill_readiness_score=student.skill_readiness_score,
    )


def _to_out(application: Application, *, for_recruiter: bool) -> ApplicationOut:
    data = ApplicationOut(
        id=application.id,
        status=application.status,
        match_score=application.match_score,
        match_breakdown=dict(application.match_breakdown or {}),
        matching_skills=list(application.matching_skills or []),
        missing_skills=list(application.missing_skills or []),
        cover_letter=application.cover_letter,
        resume_document_id=application.resume_document_id,
        submitted_at=application.submitted_at,
        last_status_change_at=application.last_status_change_at,
        decided_at=application.decided_at,
        rejection_reason=application.rejection_reason,
        recruiter_rating=application.recruiter_rating,
        opportunity=_opportunity_brief(application.opportunity),
        applicant=_applicant_brief(application.student),
        timeline=[
            TimelineStep(**step) for step in application_service.build_timeline(application)
        ],
        history=[StatusHistoryOut.model_validate(h) for h in application.history],
        interviews=[InterviewOut.model_validate(i) for i in application.interviews],
    )
    # Internal recruiter notes are never disclosed to the applicant.
    data.recruiter_notes = application.recruiter_notes if for_recruiter else None
    return data


async def _assert_recruiter_owns(
    db, application: Application, user, company_id: uuid.UUID
) -> None:
    opportunity = application.opportunity or await db.get(
        Opportunity, application.opportunity_id
    )
    if opportunity is None:
        raise NotFoundError("Opportunity not found", code="OPPORTUNITY_NOT_FOUND")
    opportunity_service.assert_can_manage(opportunity, user, company_id)


# -------------------------------------------------------------- student ----
@router.post(
    "/opportunities/{opportunity_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[ApplicationOut],
    responses=ERRORS,
    summary="Apply to an opportunity",
    description=(
        "Submits an application and snapshots the match explanation (score, "
        "matching skills, missing skills) as it stood at submission time, so "
        "both sides can see the basis for the application later.\n\n"
        "The employer's stated hard eligibility criteria are enforced here; the "
        "match score itself never blocks an application."
    ),
)
async def apply(
    opportunity_id: uuid.UUID,
    payload: ApplyRequest,
    request: Request,
    student: CurrentStudent,
    db: DbSession,
) -> dict:
    opportunity = await opportunity_service.get_opportunity_or_404(db, opportunity_id)
    application = await application_service.apply_to_opportunity(
        db,
        opportunity=opportunity,
        student=student,
        cover_letter=payload.cover_letter,
        resume_document_id=payload.resume_document_id,
        answers=payload.answers,
    )
    await audit.record(
        db, AuditAction.APPLICATION_SUBMIT, actor=student.user,
        resource_type="application", resource_id=application.id,
        description=f"Applied to {opportunity.title}", request=request,
        meta={"match_score": application.match_score},
    )
    await db.commit()
    reloaded = await application_service.get_application_or_404(db, application.id)
    return ok(_to_out(reloaded, for_recruiter=False))


@router.get(
    "/mine",
    response_model=Page[ApplicationListItem],
    responses=ERRORS,
    summary="My applications",
    description="Every application the student has submitted, with its current "
                "pipeline stage and the next scheduled interview.",
)
async def my_applications(
    student: CurrentStudent,
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    status_filter: Annotated[ApplicationStatus | None, Query(alias="status")] = None,
    opportunity_type: OpportunityType | None = None,
) -> Page[ApplicationListItem]:
    stmt = (
        select(Application)
        .where(Application.student_id == student.id)
        .options(
            selectinload(Application.opportunity).selectinload(Opportunity.company),
            selectinload(Application.interviews),
        )
    )
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)
    if opportunity_type:
        stmt = stmt.join(Opportunity, Opportunity.id == Application.opportunity_id).where(
            Opportunity.opportunity_type == opportunity_type
        )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Application.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()

    items = []
    for row in rows:
        upcoming = sorted(
            (i for i in row.interviews if i.status == "SCHEDULED"),
            key=lambda i: i.scheduled_at,
        )
        items.append(
            ApplicationListItem(
                id=row.id, status=row.status, match_score=row.match_score,
                matching_skills=list(row.matching_skills or []),
                missing_skills=list(row.missing_skills or []),
                submitted_at=row.submitted_at,
                last_status_change_at=row.last_status_change_at,
                opportunity=_opportunity_brief(row.opportunity),
                next_interview_at=upcoming[0].scheduled_at if upcoming else None,
            )
        )
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/mine/funnel",
    response_model=Envelope[ApplicationFunnelOut],
    responses=ERRORS,
    summary="My application funnel",
    description="Counts per stage plus the conversion rate between stages.",
)
async def my_funnel(student: CurrentStudent, db: DbSession) -> dict:
    rows = (
        await db.execute(
            select(Application.status, func.count())
            .where(Application.student_id == student.id)
            .group_by(Application.status)
        )
    ).all()
    by_status = {s.value: c for s, c in rows}
    total = sum(by_status.values())
    shortlisted = by_status.get("SHORTLISTED", 0) + by_status.get("INTERVIEW", 0) \
        + by_status.get("OFFERED", 0) + by_status.get("SELECTED", 0)
    interviewed = by_status.get("INTERVIEW", 0) + by_status.get("OFFERED", 0) \
        + by_status.get("SELECTED", 0)
    offered = by_status.get("OFFERED", 0) + by_status.get("SELECTED", 0)

    def pct(part: int, whole: int) -> float:
        return round(part / whole * 100, 1) if whole else 0.0

    return ok(
        ApplicationFunnelOut(
            total=total,
            by_status=by_status,
            conversion={
                "applied_to_shortlist": pct(shortlisted, total),
                "shortlist_to_interview": pct(interviewed, shortlisted),
                "interview_to_offer": pct(offered, interviewed),
                "offer_to_selected": pct(by_status.get("SELECTED", 0), offered),
            },
        )
    )


@router.post(
    "/{application_id}/withdraw",
    response_model=Envelope[ApplicationOut],
    responses=ERRORS,
    summary="Withdraw an application",
    description="Withdrawal is final: a withdrawn application cannot be reopened "
                "and the student cannot reapply to the same posting.",
)
async def withdraw(
    application_id: uuid.UUID,
    payload: WithdrawRequest,
    request: Request,
    student: CurrentStudent,
    db: DbSession,
) -> dict:
    application = await application_service.get_application_or_404(db, application_id)
    await application_service.withdraw(db, application, student, payload.reason)
    await audit.record(
        db, AuditAction.APPLICATION_STATUS_CHANGE, actor=student.user,
        resource_type="application", resource_id=application.id,
        description="Withdrawn by applicant", request=request,
    )
    await db.commit()
    reloaded = await application_service.get_application_or_404(db, application_id)
    return ok(_to_out(reloaded, for_recruiter=False))


# ------------------------------------------------------------ recruiter ----
@router.get(
    "/received",
    response_model=Page[ApplicationListItem],
    responses=ERRORS,
    summary="Applicants for my company",
    description=(
        "Every application to the recruiter's company, filterable by posting, "
        "status and minimum match score.\n\n"
        "Ranking by match is decision *support*: the score and its contributing "
        "factors are shown so a human can judge, and no candidate is ever "
        "filtered out automatically."
    ),
)
async def received_applications(
    db: DbSession,
    user: RecruiterUser,
    company_id: RecruiterCompanyId,
    page: Annotated[PaginationParams, Depends(pagination)],
    opportunity_id: uuid.UUID | None = None,
    status_filter: Annotated[ApplicationStatus | None, Query(alias="status")] = None,
    min_match_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    q: Annotated[str | None, Query(description="Search applicant name")] = None,
    sort_by: Annotated[str, Query(pattern="^(match|recent|name)$")] = "match",
) -> Page[ApplicationListItem]:
    stmt = (
        select(Application)
        .join(Opportunity, Opportunity.id == Application.opportunity_id)
        .where(Opportunity.company_id == company_id)
        .options(
            selectinload(Application.opportunity).selectinload(Opportunity.company),
            selectinload(Application.student).selectinload(StudentProfile.user),
            selectinload(Application.interviews),
        )
    )
    if opportunity_id:
        stmt = stmt.where(Application.opportunity_id == opportunity_id)
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)
    if min_match_score is not None:
        stmt = stmt.where(Application.match_score >= min_match_score)
    if q:
        from app.models.user import User

        stmt = (
            stmt.join(StudentProfile, StudentProfile.id == Application.student_id)
            .join(User, User.id == StudentProfile.user_id)
            .where(func.lower(User.full_name).like(f"%{q.lower().strip()}%"))
        )

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    order = {
        "match": Application.match_score.desc(),
        "recent": Application.created_at.desc(),
    }.get(sort_by, Application.match_score.desc())
    rows = (
        await db.execute(stmt.order_by(order).offset(page.offset).limit(page.limit))
    ).scalars().all()

    items = []
    for row in rows:
        upcoming = sorted(
            (i for i in row.interviews if i.status == "SCHEDULED"),
            key=lambda i: i.scheduled_at,
        )
        items.append(
            ApplicationListItem(
                id=row.id, status=row.status, match_score=row.match_score,
                matching_skills=list(row.matching_skills or []),
                missing_skills=list(row.missing_skills or []),
                submitted_at=row.submitted_at,
                last_status_change_at=row.last_status_change_at,
                opportunity=_opportunity_brief(row.opportunity),
                applicant=_applicant_brief(row.student),
                next_interview_at=upcoming[0].scheduled_at if upcoming else None,
                recruiter_rating=row.recruiter_rating,
            )
        )
    return Page.build(items, total, page.page, page.page_size)


@router.patch(
    "/{application_id}",
    response_model=Envelope[ApplicationOut],
    responses=ERRORS,
    summary="Change application status",
    description=(
        "Moves an application through the hiring pipeline. Transitions are "
        "validated against an explicit state machine, so history can never "
        "become incoherent (for example a rejected candidate cannot be "
        "silently 'un-rejected').\n\n"
        "Selecting a candidate creates a **verified experience record** on their "
        "profile - the final step of the platform's core loop."
    ),
)
async def change_status(
    application_id: uuid.UUID,
    payload: StatusChangeRequest,
    request: Request,
    db: DbSession,
    user: RecruiterUser,
    company_id: RecruiterCompanyId,
) -> dict:
    application = await application_service.get_application_or_404(db, application_id)
    await _assert_recruiter_owns(db, application, user, company_id)
    await application_service.change_status(
        db, application, payload.status, actor=user, note=payload.note,
        reason=payload.reason,
    )
    await audit.record(
        db, AuditAction.APPLICATION_STATUS_CHANGE, actor=user,
        resource_type="application", resource_id=application.id,
        description=f"Status -> {payload.status.value}", request=request,
    )
    await db.commit()
    reloaded = await application_service.get_application_or_404(db, application_id)
    return ok(_to_out(reloaded, for_recruiter=True))


@router.post(
    "/bulk-status",
    response_model=Envelope[BulkStatusResult],
    responses=ERRORS,
    summary="Change status for several applications",
    description="Applies the same transition to a list of applications. Each is "
                "validated independently; failures are reported per application "
                "rather than failing the whole batch.",
)
async def bulk_status(
    payload: BulkStatusChangeRequest,
    request: Request,
    db: DbSession,
    user: RecruiterUser,
    company_id: RecruiterCompanyId,
) -> dict:
    updated, failed = 0, []
    for application_id in payload.application_ids:
        try:
            application = await application_service.get_application_or_404(
                db, application_id
            )
            await _assert_recruiter_owns(db, application, user, company_id)
            await application_service.change_status(
                db, application, payload.status, actor=user, note=payload.note
            )
            updated += 1
        except Exception as exc:  # collected, not swallowed
            code = getattr(exc, "code", "ERROR")
            failed.append({"application_id": str(application_id), "error": code})
    await audit.record(
        db, AuditAction.APPLICATION_STATUS_CHANGE, actor=user,
        resource_type="application",
        description=f"Bulk status -> {payload.status.value} ({updated} updated)",
        request=request,
    )
    await db.commit()
    return ok(BulkStatusResult(updated=updated, failed=failed))


@router.patch(
    "/{application_id}/notes",
    response_model=Envelope[ApplicationOut],
    responses=ERRORS,
    summary="Add recruiter notes and rating",
    description="Internal notes and a 1-5 rating. Never visible to the applicant.",
)
async def update_notes(
    application_id: uuid.UUID,
    payload: RecruiterNoteRequest,
    db: DbSession,
    user: RecruiterUser,
    company_id: RecruiterCompanyId,
) -> dict:
    application = await application_service.get_application_or_404(db, application_id)
    await _assert_recruiter_owns(db, application, user, company_id)
    changes = payload.model_dump(exclude_unset=True)
    if "recruiter_notes" in changes:
        application.recruiter_notes = changes["recruiter_notes"] or ""
    if "recruiter_rating" in changes:
        application.recruiter_rating = changes["recruiter_rating"]
    await db.commit()
    reloaded = await application_service.get_application_or_404(db, application_id)
    return ok(_to_out(reloaded, for_recruiter=True))


@router.post(
    "/{application_id}/interviews",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[InterviewOut],
    responses=ERRORS,
    summary="Schedule an interview",
    description="Schedules a round, advances the application to INTERVIEW and "
                "notifies the candidate by in-app notification and email.",
)
async def schedule_interview(
    application_id: uuid.UUID,
    payload: InterviewCreate,
    request: Request,
    db: DbSession,
    user: RecruiterUser,
    company_id: RecruiterCompanyId,
) -> dict:
    application = await application_service.get_application_or_404(db, application_id)
    await _assert_recruiter_owns(db, application, user, company_id)
    interview = await application_service.schedule_interview(
        db, application, actor=user, scheduled_at=payload.scheduled_at,
        round_name=payload.round_name, duration_minutes=payload.duration_minutes,
        mode=payload.mode, location_or_link=payload.location_or_link,
        interviewer_name=payload.interviewer_name, instructions=payload.instructions,
    )
    await audit.record(
        db, AuditAction.APPLICATION_STATUS_CHANGE, actor=user,
        resource_type="interview", resource_id=interview.id,
        description=f"Scheduled {payload.round_name}", request=request,
    )
    await db.commit()
    return ok(InterviewOut.model_validate(interview))


@router.patch(
    "/interviews/{interview_id}",
    response_model=Envelope[InterviewOut],
    responses=ERRORS,
    summary="Record interview outcome",
)
async def interview_feedback(
    interview_id: uuid.UUID,
    payload: InterviewFeedback,
    db: DbSession,
    user: RecruiterUser,
    company_id: RecruiterCompanyId,
) -> dict:
    interview = await db.get(Interview, interview_id)
    if interview is None:
        raise NotFoundError("Interview not found", code="INTERVIEW_NOT_FOUND")
    application = await application_service.get_application_or_404(
        db, interview.application_id
    )
    await _assert_recruiter_owns(db, application, user, company_id)
    interview.status = payload.status
    interview.feedback = payload.feedback
    interview.rating = payload.rating
    await db.commit()
    return ok(InterviewOut.model_validate(interview))


# -------------------------------------------------------------- shared -----
@router.get(
    "/{application_id}",
    response_model=Envelope[ApplicationOut],
    responses=ERRORS,
    summary="Application detail",
    description="Visible to the applicant, to recruiters at the hiring company, "
                "to the applicant's institution admin, and to platform admins.",
)
async def get_application(
    application_id: uuid.UUID, db: DbSession, user: ActiveUser
) -> dict:
    application = await application_service.get_application_or_404(db, application_id)
    roles = set(user.role_names)

    is_owner = bool(
        application.student and application.student.user_id == user.id
    )
    is_company = bool(
        application.opportunity
        and user.company_id
        and application.opportunity.company_id == user.company_id
        and roles & {RoleName.INDUSTRY_RECRUITER.value, RoleName.INDUSTRY_ADMIN.value}
    )
    is_institution = bool(
        RoleName.INSTITUTION_ADMIN.value in roles
        and application.student
        and application.student.institution_id == user.institution_id
    )
    is_admin = RoleName.SUPER_ADMIN.value in roles

    if not (is_owner or is_company or is_institution or is_admin):
        raise PermissionDeniedError(
            "You do not have access to this application", code="APPLICATION_ACCESS_DENIED"
        )
    return ok(_to_out(application, for_recruiter=is_company or is_admin))
