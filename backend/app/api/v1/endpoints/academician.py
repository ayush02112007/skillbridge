"""Academician portal: profile, faculty opportunities and dashboard."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints._opportunity_routes import build_router
from app.core.deps import (
    CurrentAcademician,
    DbSession,
)
from app.core.exceptions import NotFoundError
from app.models.application import Application
from app.models.enums import (
    AuditAction,
    CollaborationStatus,
    MentorshipStatus,
    OpportunityStatus,
    OpportunityType,
)
from app.models.event import Event
from app.models.mentorship import MentorProfile, MentorshipRequest, MentorshipSession
from app.models.opportunity import FacultyOpportunity, Opportunity
from app.models.organization import Department, Institution
from app.models.research import ResearchApplication, ResearchProject
from app.models.user import User
from app.schemas.collaboration import (
    AcademicianDashboardOut,
    AcademicianProfileOut,
    AcademicianProfileUpdate,
)
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.schemas.opportunity import FacultyOpportunityCreate
from app.services import application as application_service
from app.services import audit

router = APIRouter(prefix="/academicians", tags=["Academicians"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
}

# Companies create faculty programmes through the shared opportunity builder.
faculty_opportunities_router = build_router(
    prefix="/faculty-opportunities",
    tag="Academicians",
    opportunity_type=OpportunityType.FACULTY_OPPORTUNITY,
    create_schema=FacultyOpportunityCreate,
    label="faculty opportunity",
    list_description=(
        "Industry programmes aimed at academicians: faculty internships, FDPs, "
        "industrial training, consultancy, research collaboration and guest "
        "lectures."
    ),
    create_description=(
        "Publishes a programme for academicians. Use `extra.kind` to set the "
        "programme type and `min_teaching_experience_years` for eligibility."
    ),
)


def _now() -> datetime:
    return datetime.now(UTC)


async def _profile_out(db, profile) -> AcademicianProfileOut:
    user = profile.user or await db.get(User, profile.user_id)
    institution = (
        await db.get(Institution, profile.institution_id)
        if profile.institution_id
        else None
    )
    data = AcademicianProfileOut.model_validate(profile)
    data.full_name = user.full_name if user else ""
    data.email = user.email if user else None
    data.avatar_url = user.avatar_url if user else None
    data.institution_name = institution.name if institution else None
    return data


def _completion(profile) -> int:
    """Simple, explicit completion score for a faculty profile."""
    checks = [
        bool(profile.designation),
        bool(profile.highest_qualification),
        bool(profile.specialization),
        bool(profile.bio and len(profile.bio) > 40),
        bool(profile.research_areas),
        bool(profile.expertise_areas),
        bool(profile.institution_id),
        profile.teaching_experience_years > 0,
    ]
    return round(sum(checks) / len(checks) * 100)


@router.get(
    "/me",
    response_model=Envelope[AcademicianProfileOut],
    responses=ERRORS,
    summary="My faculty profile",
)
async def get_my_profile(academician: CurrentAcademician, db: DbSession) -> dict:
    return ok(await _profile_out(db, academician))


@router.patch(
    "/me",
    response_model=Envelope[AcademicianProfileOut],
    responses=ERRORS,
    summary="Update my faculty profile",
)
async def update_my_profile(
    payload: AcademicianProfileUpdate,
    request: Request,
    academician: CurrentAcademician,
    db: DbSession,
) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("institution_id") and await db.get(
        Institution, changes["institution_id"]
    ) is None:
        raise NotFoundError("Institution not found", code="INSTITUTION_NOT_FOUND")
    if changes.get("department_id") and await db.get(
        Department, changes["department_id"]
    ) is None:
        raise NotFoundError("Department not found", code="DEPARTMENT_NOT_FOUND")
    for field, value in changes.items():
        setattr(academician, field, value)
    academician.profile_completion = _completion(academician)
    await audit.record(
        db, AuditAction.PROFILE_UPDATE, actor=academician.user,
        resource_type="academician_profile", resource_id=academician.id,
        description="Faculty profile updated", request=request,
    )
    await db.commit()
    return ok(await _profile_out(db, academician))


@router.post(
    "/faculty-opportunities/{opportunity_id}/apply",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Apply to a faculty programme",
    description="Eligibility (minimum teaching experience) is checked before "
                "the application is accepted.",
)
async def apply_to_faculty_opportunity(
    opportunity_id: uuid.UUID,
    db: DbSession,
    academician: CurrentAcademician,
    cover_letter: Annotated[str, Query(max_length=4000)] = "",
) -> dict:
    from app.services import opportunity as opportunity_service

    opportunity = await opportunity_service.get_opportunity_or_404(db, opportunity_id)
    application = await application_service.apply_to_faculty_opportunity(
        db, opportunity=opportunity, academician=academician, cover_letter=cover_letter
    )
    await db.commit()
    return ok(
        {
            "id": str(application.id),
            "status": application.status.value,
            "opportunity_id": str(opportunity.id),
            "opportunity_title": opportunity.title,
            "submitted_at": application.submitted_at,
        }
    )


@router.get(
    "/applications/mine",
    response_model=Envelope[list[dict]],
    responses=ERRORS,
    summary="My faculty programme applications",
)
async def my_faculty_applications(
    db: DbSession, academician: CurrentAcademician
) -> dict:
    rows = (
        await db.execute(
            select(Application)
            .where(Application.academician_id == academician.id)
            .options(selectinload(Application.opportunity).selectinload(Opportunity.company))
            .order_by(Application.created_at.desc())
        )
    ).scalars().all()
    return ok(
        [
            {
                "id": str(r.id),
                "status": r.status.value,
                "submitted_at": r.submitted_at,
                "opportunity_id": str(r.opportunity_id),
                "opportunity_title": r.opportunity.title if r.opportunity else "",
                "company_name": (
                    r.opportunity.company.name
                    if r.opportunity and r.opportunity.company
                    else ""
                ),
                "kind": getattr(r.opportunity, "kind", None)
                and r.opportunity.kind.value,
            }
            for r in rows
        ]
    )


@router.get(
    "/me/dashboard",
    response_model=Envelope[AcademicianDashboardOut],
    responses=ERRORS,
    summary="Academician dashboard",
    description="Opportunities, applications, mentorship load, research "
                "collaborations and upcoming sessions.",
)
async def academician_dashboard(
    academician: CurrentAcademician, db: DbSession
) -> dict:
    open_opportunities = (
        await db.execute(
            select(func.count())
            .select_from(Opportunity)
            .where(
                Opportunity.opportunity_type == OpportunityType.FACULTY_OPPORTUNITY,
                Opportunity.status == OpportunityStatus.PUBLISHED,
                Opportunity.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    application_rows = (
        await db.execute(
            select(Application.status, func.count())
            .where(Application.academician_id == academician.id)
            .group_by(Application.status)
        )
    ).all()

    mentor = (
        await db.execute(
            select(MentorProfile).where(MentorProfile.user_id == academician.user_id)
        )
    ).scalar_one_or_none()
    mentorship = {"pending": 0, "active": 0, "completed": 0, "sessions_completed": 0}
    upcoming_sessions: list[dict] = []
    if mentor is not None:
        rows = (
            await db.execute(
                select(MentorshipRequest.status, func.count())
                .where(MentorshipRequest.mentor_id == mentor.id)
                .group_by(MentorshipRequest.status)
            )
        ).all()
        counts = {s.value: c for s, c in rows}
        mentorship = {
            "pending": counts.get(MentorshipStatus.REQUESTED.value, 0),
            "active": counts.get(MentorshipStatus.ACCEPTED.value, 0)
            + counts.get(MentorshipStatus.SCHEDULED.value, 0),
            "completed": counts.get(MentorshipStatus.COMPLETED.value, 0),
            "sessions_completed": mentor.sessions_completed,
        }
        sessions = (
            await db.execute(
                select(MentorshipSession)
                .join(
                    MentorshipRequest,
                    MentorshipRequest.id == MentorshipSession.request_id,
                )
                .where(
                    MentorshipRequest.mentor_id == mentor.id,
                    MentorshipSession.status == "SCHEDULED",
                )
                .order_by(MentorshipSession.scheduled_at)
                .limit(5)
            )
        ).scalars().all()
        upcoming_sessions = [
            {
                "id": str(s.id),
                "scheduled_at": s.scheduled_at,
                "duration_minutes": s.duration_minutes,
                "agenda": s.agenda,
                "meeting_link": s.meeting_link,
            }
            for s in sessions
        ]

    research_rows = (
        await db.execute(
            select(ResearchApplication.status, func.count())
            .where(ResearchApplication.academician_id == academician.id)
            .group_by(ResearchApplication.status)
        )
    ).all()
    open_research = (
        await db.execute(
            select(func.count())
            .select_from(ResearchProject)
            .where(
                ResearchProject.status == CollaborationStatus.OPEN,
                ResearchProject.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    events_hosted = (
        await db.execute(
            select(func.count())
            .select_from(Event)
            .where(Event.created_by_id == academician.user_id, Event.deleted_at.is_(None))
        )
    ).scalar_one()

    # Faculty programmes matched on expertise overlap and experience eligibility.
    expertise = {str(a).lower() for a in (academician.expertise_areas or [])}
    expertise |= {str(a).lower() for a in (academician.research_areas or [])}
    candidates = (
        await db.execute(
            select(FacultyOpportunity)
            .where(
                FacultyOpportunity.status == OpportunityStatus.PUBLISHED,
                FacultyOpportunity.deleted_at.is_(None),
            )
            .options(selectinload(FacultyOpportunity.company))
            .order_by(FacultyOpportunity.published_at.desc().nullslast())
            .limit(40)
        )
    ).scalars().all()

    recommended = []
    for opportunity in candidates:
        if (
            opportunity.min_teaching_experience_years
            > academician.teaching_experience_years
        ):
            continue
        focus = {str(f).lower() for f in (opportunity.focus_areas or [])}
        overlap = expertise & focus
        reasons = []
        if overlap:
            reasons.append(f"Matches your expertise in {', '.join(sorted(overlap)[:2])}")
        reasons.append("You meet the teaching-experience requirement")
        recommended.append(
            {
                "id": str(opportunity.id),
                "title": opportunity.title,
                "kind": opportunity.kind.value,
                "company_name": opportunity.company.name if opportunity.company else "",
                "deadline": opportunity.application_deadline,
                "overlap_count": len(overlap),
                "reasons": reasons,
            }
        )
    recommended.sort(key=lambda r: -r["overlap_count"])

    return ok(
        AcademicianDashboardOut(
            profile_completion=_completion(academician),
            open_faculty_opportunities=open_opportunities,
            my_applications={s.value: c for s, c in application_rows},
            mentorship=mentorship,
            research={
                "open_projects": open_research,
                **{str(s): c for s, c in research_rows},
            },
            events_hosted=events_hosted,
            upcoming_sessions=upcoming_sessions,
            recommended_opportunities=recommended[:5],
        )
    )


@router.get(
    "",
    response_model=Page[AcademicianProfileOut],
    summary="Browse academicians",
    description="Faculty directory, used by industry to find collaborators and "
                "guest speakers.",
)
async def list_academicians(
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    q: str | None = None,
    institution_id: uuid.UUID | None = None,
    available_for_consultancy: bool | None = None,
) -> Page[AcademicianProfileOut]:
    from app.models.profile import AcademicianProfile

    stmt = (
        select(AcademicianProfile)
        .where(AcademicianProfile.deleted_at.is_(None))
        .options(selectinload(AcademicianProfile.user))
    )
    if institution_id:
        stmt = stmt.where(AcademicianProfile.institution_id == institution_id)
    if available_for_consultancy is not None:
        stmt = stmt.where(
            AcademicianProfile.is_available_for_consultancy.is_(available_for_consultancy)
        )
    if q:
        needle = f"%{q.lower().strip()}%"
        stmt = stmt.join(User, User.id == AcademicianProfile.user_id).where(
            or_(
                func.lower(User.full_name).like(needle),
                func.lower(AcademicianProfile.specialization).like(needle),
                func.lower(AcademicianProfile.designation).like(needle),
            )
        )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(AcademicianProfile.publications_count.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()
    items = [await _profile_out(db, r) for r in rows]
    return Page.build(items, total, page.page, page.page_size)
