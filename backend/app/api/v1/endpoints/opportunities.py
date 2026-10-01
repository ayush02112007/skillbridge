"""Shared opportunity endpoints: search, detail, saving and JD analysis.

Type-specific creation lives in ``internships.py``, ``jobs.py``, ``projects.py``
and ``academician.py``; everything below works across every opportunity type.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import (
    ActiveUser,
    DbSession,
    OptionalUser,
    RecruiterUser,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import (
    OpportunityStatus,
    OpportunityType,
    RoleName,
    WorkMode,
)
from app.models.opportunity import Opportunity, OpportunitySkill, SavedOpportunity
from app.models.profile import StudentProfile
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    MessageResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.schemas.opportunity import (
    CompanyBrief,
    DetectedSkill,
    JobDescriptionAnalysisIn,
    JobDescriptionAnalysisOut,
    MatchExplanation,
    OpportunityDetail,
    OpportunityListItem,
    OpportunitySkillOut,
)
from app.services import opportunity as opportunity_service

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
}

# Fields flattened onto list rows so cards render without a second request.
SUMMARY_FIELDS = (
    "stipend_min", "stipend_max", "duration_weeks", "salary_min", "salary_max",
    "employment_type", "experience_min_years",
)


def to_list_item(opportunity: Opportunity) -> OpportunityListItem:
    item = OpportunityListItem(
        id=opportunity.id,
        opportunity_type=opportunity.opportunity_type,
        title=opportunity.title,
        slug=opportunity.slug,
        company=(
            CompanyBrief.model_validate(opportunity.company)
            if opportunity.company
            else None
        ),
        status=opportunity.status,
        work_mode=opportunity.work_mode,
        location_city=opportunity.location_city,
        positions=opportunity.positions,
        application_deadline=opportunity.application_deadline,
        published_at=opportunity.published_at,
        applications_count=opportunity.applications_count,
        views_count=opportunity.views_count,
        job_role_title=opportunity.job_role.title if opportunity.job_role else None,
        skills=[OpportunitySkillOut.model_validate(s) for s in opportunity.skills],
        is_open=opportunity.is_open,
        is_demo=opportunity.is_demo,
    )
    for field in SUMMARY_FIELDS:
        if hasattr(opportunity, field):
            setattr(item, field, getattr(opportunity, field))
    return item


def to_detail(opportunity: Opportunity) -> OpportunityDetail:
    detail = OpportunityDetail(**to_list_item(opportunity).model_dump())
    detail.description = opportunity.description
    detail.responsibilities = list(opportunity.responsibilities or [])
    detail.eligibility_text = opportunity.eligibility_text
    detail.location_country = opportunity.location_country
    detail.min_cgpa = opportunity.min_cgpa
    detail.max_backlogs = opportunity.max_backlogs
    detail.eligible_degrees = list(opportunity.eligible_degrees or [])
    detail.eligible_graduation_years = list(opportunity.eligible_graduation_years or [])
    detail.eligible_departments = list(opportunity.eligible_departments or [])
    detail.starts_on = opportunity.starts_on
    detail.perks = list(opportunity.perks or [])
    detail.extracted_requirements = dict(opportunity.extracted_requirements or {})
    detail.created_at = opportunity.created_at
    subtype = opportunity_service.SUBTYPE_FIELDS.get(opportunity.opportunity_type, set())
    detail.details = {
        field: getattr(opportunity, field)
        for field in sorted(subtype)
        if hasattr(opportunity, field)
    }
    return detail


async def student_profile_for(db, user) -> StudentProfile | None:
    if user is None or RoleName.STUDENT.value not in user.role_names:
        return None
    return (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))
    ).scalar_one_or_none()


async def decorate_for_student(
    db, user, rows: Sequence[Opportunity], items: list[OpportunityListItem]
) -> list[OpportunityListItem]:
    """Attach per-student match scores and saved/applied flags to a result page."""
    if user is None:
        return items
    ids = [r.id for r in rows]
    saved = await opportunity_service.saved_opportunity_ids(db, user.id, ids)
    student = await student_profile_for(db, user)
    applied: set[uuid.UUID] = set()
    matches: dict[uuid.UUID, Any] = {}
    if student is not None:
        applied = await opportunity_service.applied_opportunity_ids(db, student.id, ids)
        matches = await opportunity_service.match_many(db, student, rows)
    for item in items:
        item.is_saved = item.id in saved
        item.has_applied = item.id in applied
        result = matches.get(item.id)
        if result is not None:
            item.match_score = result.match_score
            item.matching_skills = result.matching_skills[:6]
            item.missing_skills = result.missing_skills[:6]
    return items


@router.get(
    "",
    response_model=Page[OpportunityListItem],
    summary="Search opportunities",
    description=(
        "Searches across every opportunity type with a shared filter set.\n\n"
        "For a signed-in student, each row is annotated with their match score, "
        "the skills they already meet, the ones they are missing, and whether "
        "they have already applied or saved it."
    ),
)
async def search_opportunities(
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    user: OptionalUser = None,
    q: Annotated[str | None, Query(description="Free-text search")] = None,
    opportunity_type: OpportunityType | None = None,
    company_id: uuid.UUID | None = None,
    job_role_id: uuid.UUID | None = None,
    skill_id: Annotated[list[uuid.UUID] | None, Query()] = None,
    location: str | None = None,
    work_mode: WorkMode | None = None,
    min_stipend: int | None = None,
    min_salary: int | None = None,
    max_experience_years: float | None = None,
    open_only: bool = True,
    sort_by: Annotated[str, Query(pattern="^(recent|deadline|match|applications)$")] = "recent",
) -> Page[OpportunityListItem]:
    entity = opportunity_service.polymorphic_opportunity()
    stmt = select(entity).options(
        selectinload(entity.company),
        selectinload(entity.job_role),
        selectinload(entity.skills).selectinload(OpportunitySkill.skill),
    )
    stmt = opportunity_service.apply_filters(
        stmt, entity, q=q, opportunity_type=opportunity_type, company_id=company_id,
        job_role_id=job_role_id, skill_ids=skill_id, location=location,
        work_mode=work_mode, min_stipend=min_stipend, min_salary=min_salary,
        max_experience_years=max_experience_years, open_only=open_only,
    )

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    order = {
        "recent": entity.published_at.desc().nullslast(),
        "deadline": entity.application_deadline.asc().nullslast(),
        "applications": entity.applications_count.desc(),
    }.get(sort_by, entity.published_at.desc().nullslast())

    if sort_by == "match" and user is not None:
        # Match ordering needs every candidate row scored, so it is bounded to a
        # reasonable working set rather than the whole table.
        rows = (
            await db.execute(stmt.order_by(entity.published_at.desc().nullslast()).limit(200))
        ).scalars().all()
        items = [to_list_item(r) for r in rows]
        items = await decorate_for_student(db, user, rows, items)
        items.sort(key=lambda i: -(i.match_score or 0))
        window = items[page.offset : page.offset + page.limit]
        return Page.build(window, min(total, len(items)), page.page, page.page_size)

    rows = (
        await db.execute(stmt.order_by(order).offset(page.offset).limit(page.limit))
    ).scalars().all()
    items = [to_list_item(r) for r in rows]
    items = await decorate_for_student(db, user, rows, items)
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/saved",
    response_model=Page[OpportunityListItem],
    responses=ERRORS,
    summary="My saved opportunities",
)
async def list_saved(
    db: DbSession, user: ActiveUser, page: Annotated[PaginationParams, Depends(pagination)]
) -> Page[OpportunityListItem]:
    entity = opportunity_service.polymorphic_opportunity()
    stmt = (
        select(entity)
        .join(SavedOpportunity, SavedOpportunity.opportunity_id == entity.id)
        .where(SavedOpportunity.user_id == user.id, entity.deleted_at.is_(None))
        .options(
            selectinload(entity.company),
            selectinload(entity.job_role),
            selectinload(entity.skills).selectinload(OpportunitySkill.skill),
        )
        .order_by(SavedOpportunity.created_at.desc())
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.offset(page.offset).limit(page.limit))).scalars().all()
    items = await decorate_for_student(db, user, rows, [to_list_item(r) for r in rows])
    return Page.build(items, total, page.page, page.page_size)


@router.post(
    "/analyse-description",
    response_model=Envelope[JobDescriptionAnalysisOut],
    responses=ERRORS,
    summary="Analyse a job description",
    description=(
        "Extracts structured requirements from free text so a recruiter does not "
        "have to tag skills by hand.\n\n"
        "Skills are detected by exact matching against the platform taxonomy, so "
        "nothing is invented. The result is a **suggestion**: the recruiter "
        "reviews and edits it before the posting is published."
    ),
)
async def analyse_description(
    payload: JobDescriptionAnalysisIn, db: DbSession, _user: RecruiterUser
) -> dict:
    result = await opportunity_service.analyse_job_description(
        db, payload.description, payload.title
    )
    return ok(
        JobDescriptionAnalysisOut(
            skills=[DetectedSkill(**s) for s in result["skills"]],
            keywords=result["keywords"],
            responsibilities=result.get("responsibilities") or [],
            education=result.get("education"),
            experience_years=result.get("experience_years"),
            seniority=result.get("seniority"),
            suggested_job_role_id=result.get("suggested_job_role_id"),
            suggested_job_role_title=result.get("suggested_job_role_title"),
            extracted_by=result["extracted_by"],
        )
    )


@router.get(
    "/{opportunity_id}",
    response_model=Envelope[OpportunityDetail],
    responses=ERRORS,
    summary="Opportunity detail",
    description="Full posting. For a signed-in student the response also carries "
                "the complete match explanation.",
)
async def get_opportunity(
    opportunity_id: uuid.UUID, db: DbSession, user: OptionalUser = None
) -> dict:
    include_unpublished = bool(
        user
        and (
            RoleName.SUPER_ADMIN.value in user.role_names
            or RoleName.INDUSTRY_ADMIN.value in user.role_names
            or RoleName.INDUSTRY_RECRUITER.value in user.role_names
        )
    )
    opportunity = await opportunity_service.get_opportunity_or_404(
        db, opportunity_id, include_unpublished=include_unpublished
    )
    if include_unpublished and opportunity.status != OpportunityStatus.PUBLISHED:
        if (
            RoleName.SUPER_ADMIN.value not in user.role_names
            and opportunity.company_id != user.company_id
        ):
            raise NotFoundError("Opportunity not found", code="OPPORTUNITY_NOT_FOUND")

    detail = to_detail(opportunity)
    if user is not None:
        saved = await opportunity_service.saved_opportunity_ids(
            db, user.id, [opportunity.id]
        )
        detail.is_saved = opportunity.id in saved
        student = await student_profile_for(db, user)
        if student is not None:
            applied = await opportunity_service.applied_opportunity_ids(
                db, student.id, [opportunity.id]
            )
            detail.has_applied = opportunity.id in applied
            result = await opportunity_service.match_student_to_opportunity(
                db, student, opportunity
            )
            detail.match_score = result.match_score
            detail.matching_skills = result.matching_skills
            detail.missing_skills = result.missing_skills
            detail.match = MatchExplanation(**result.to_dict())

    opportunity.views_count = (opportunity.views_count or 0) + 1
    await db.commit()
    return ok(detail)


@router.post(
    "/{opportunity_id}/save",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Save an opportunity",
)
async def save_opportunity(
    opportunity_id: uuid.UUID, db: DbSession, user: ActiveUser, note: str = ""
) -> MessageResponse:
    await opportunity_service.get_opportunity_or_404(db, opportunity_id)
    existing = (
        await db.execute(
            select(SavedOpportunity).where(
                SavedOpportunity.user_id == user.id,
                SavedOpportunity.opportunity_id == opportunity_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("Already saved", code="ALREADY_SAVED")
    db.add(
        SavedOpportunity(
            user_id=user.id, opportunity_id=opportunity_id, note=note[:400]
        )
    )
    await db.commit()
    return MessageResponse(message="Saved")


@router.delete(
    "/{opportunity_id}/save",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Remove a saved opportunity",
)
async def unsave_opportunity(
    opportunity_id: uuid.UUID, db: DbSession, user: ActiveUser
) -> MessageResponse:
    from sqlalchemy import delete

    result = await db.execute(
        delete(SavedOpportunity).where(
            SavedOpportunity.user_id == user.id,
            SavedOpportunity.opportunity_id == opportunity_id,
        )
    )
    if not result.rowcount:
        raise NotFoundError("Not in your saved list", code="NOT_SAVED")
    await db.commit()
    return MessageResponse(message="Removed from saved")
