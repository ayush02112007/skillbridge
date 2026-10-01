"""Company profiles and the industry portal overview."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import (
    CompanyAdminUser,
    DbSession,
    RecruiterCompanyId,
    RecruiterUser,
)
from app.core.exceptions import NotFoundError
from app.models.application import Application
from app.models.enums import OpportunityStatus
from app.models.opportunity import Opportunity
from app.models.organization import Company
from app.models.profile import RecruiterProfile
from app.models.user import User
from app.schemas.common import (
    APIModel,
    Envelope,
    ErrorResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.schemas.opportunity import CompanyBrief
from app.services import analytics as analytics_service

router = APIRouter(prefix="/companies", tags=["Companies"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
}


class CompanyOut(APIModel):
    id: uuid.UUID
    name: str
    slug: str
    industry_sector: str = ""
    website: str | None = None
    logo_url: str | None = None
    description: str = ""
    about: str = ""
    headquarters_city: str | None = None
    headquarters_country: str = "India"
    locations: list[object] = []
    employee_count: int | None = None
    founded_year: int | None = None
    contact_email: str | None = None
    linkedin_url: str | None = None
    tech_stack: list[object] = []
    benefits: list[object] = []
    verification_status: str
    is_hiring: bool = True
    is_demo: bool = False
    open_positions: int = 0


class CompanyUpdate(APIModel):
    name: str | None = None
    industry_sector: str | None = None
    website: str | None = None
    logo_url: str | None = None
    description: str | None = None
    about: str | None = None
    headquarters_city: str | None = None
    headquarters_country: str | None = None
    locations: list[str] | None = None
    employee_count: int | None = None
    founded_year: int | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    linkedin_url: str | None = None
    tech_stack: list[str] | None = None
    benefits: list[str] | None = None
    is_hiring: bool | None = None


class TeamMemberOut(APIModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    designation: str | None = None
    roles: list[str] = []
    is_primary_contact: bool = False


class IndustryDashboardOut(APIModel):
    company: CompanyBrief
    summary: dict[str, object]
    hiring_funnel: list[dict[str, object]]
    recent_applicants: list[dict[str, object]]
    active_postings: list[dict[str, object]]
    skill_shortfall: list[dict[str, object]]


@router.get(
    "",
    response_model=Page[CompanyOut],
    summary="Browse companies",
)
async def list_companies(
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    q: str | None = None,
    industry_sector: str | None = None,
    hiring_only: bool = False,
) -> Page[CompanyOut]:
    stmt = select(Company).where(Company.deleted_at.is_(None))
    if q:
        needle = f"%{q.lower().strip()}%"
        stmt = stmt.where(
            or_(
                func.lower(Company.name).like(needle),
                func.lower(Company.description).like(needle),
            )
        )
    if industry_sector:
        stmt = stmt.where(Company.industry_sector == industry_sector)
    if hiring_only:
        stmt = stmt.where(Company.is_hiring.is_(True))

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Company.name).offset(page.offset).limit(page.limit)
        )
    ).scalars().all()

    counts = dict(
        (
            await db.execute(
                select(Opportunity.company_id, func.count())
                .where(
                    Opportunity.company_id.in_([r.id for r in rows] or [uuid.uuid4()]),
                    Opportunity.status == OpportunityStatus.PUBLISHED,
                    Opportunity.deleted_at.is_(None),
                )
                .group_by(Opportunity.company_id)
            )
        ).all()
    )
    items = []
    for row in rows:
        data = CompanyOut.model_validate(row)
        data.open_positions = counts.get(row.id, 0)
        items.append(data)
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/sectors",
    response_model=Envelope[list[str]],
    summary="List industry sectors",
)
async def sectors(db: DbSession) -> dict:
    rows = (
        await db.execute(
            select(Company.industry_sector)
            .where(Company.deleted_at.is_(None))
            .distinct()
        )
    ).scalars().all()
    return ok(sorted(s for s in rows if s))


@router.get(
    "/me",
    response_model=Envelope[CompanyOut],
    responses=ERRORS,
    summary="My company profile",
)
async def my_company(
    db: DbSession, user: RecruiterUser, company_id: RecruiterCompanyId
) -> dict:
    company = await db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found", code="COMPANY_NOT_FOUND")
    open_positions = (
        await db.execute(
            select(func.count())
            .select_from(Opportunity)
            .where(
                Opportunity.company_id == company.id,
                Opportunity.status == OpportunityStatus.PUBLISHED,
                Opportunity.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    data = CompanyOut.model_validate(company)
    data.open_positions = open_positions
    return ok(data)


@router.patch(
    "/me",
    response_model=Envelope[CompanyOut],
    responses=ERRORS,
    summary="Update my company profile",
    description="Restricted to company admins. A complete profile raises the "
                "interest factor in candidate matching.",
)
async def update_my_company(
    payload: CompanyUpdate,
    db: DbSession,
    user: CompanyAdminUser,
    company_id: RecruiterCompanyId,
) -> dict:
    company = await db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found", code="COMPANY_NOT_FOUND")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    await db.commit()
    return ok(CompanyOut.model_validate(company))


@router.get(
    "/me/team",
    response_model=Envelope[list[TeamMemberOut]],
    responses=ERRORS,
    summary="My company's recruiters",
)
async def company_team(
    db: DbSession, user: RecruiterUser, company_id: RecruiterCompanyId
) -> dict:
    members = (
        await db.execute(
            select(User)
            .where(User.company_id == company_id, User.deleted_at.is_(None))
            .options(selectinload(User.roles))
        )
    ).scalars().all()
    profiles = {
        p.user_id: p
        for p in (
            await db.execute(
                select(RecruiterProfile).where(RecruiterProfile.company_id == company_id)
            )
        ).scalars()
    }
    return ok(
        [
            TeamMemberOut(
                user_id=m.id, full_name=m.full_name, email=m.email,
                designation=(
                    profiles[m.id].designation if m.id in profiles else None
                ),
                roles=m.role_names,
                is_primary_contact=(
                    profiles[m.id].is_primary_contact if m.id in profiles else False
                ),
            )
            for m in members
        ]
    )


@router.get(
    "/me/dashboard",
    response_model=Envelope[IndustryDashboardOut],
    responses=ERRORS,
    summary="Industry dashboard",
    description="Everything the recruiter landing page shows: hiring funnel, "
                "recent applicants, active postings and the skills applicants "
                "most often lack.",
)
async def industry_dashboard(
    db: DbSession, user: RecruiterUser, company_id: RecruiterCompanyId
) -> dict:
    company = await db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found", code="COMPANY_NOT_FOUND")

    analytics = await analytics_service.industry_analytics(db, company_id)

    from app.models.profile import StudentProfile

    recent = (
        await db.execute(
            select(Application)
            .join(Opportunity, Opportunity.id == Application.opportunity_id)
            .where(Opportunity.company_id == company_id)
            .options(
                selectinload(Application.student).selectinload(StudentProfile.user),
                selectinload(Application.opportunity),
            )
            .order_by(Application.created_at.desc())
            .limit(8)
        )
    ).scalars().all()

    postings = (
        await db.execute(
            select(Opportunity)
            .where(
                Opportunity.company_id == company_id,
                Opportunity.status == OpportunityStatus.PUBLISHED,
                Opportunity.deleted_at.is_(None),
            )
            .order_by(Opportunity.published_at.desc().nullslast())
            .limit(8)
        )
    ).scalars().all()

    return ok(
        IndustryDashboardOut(
            company=CompanyBrief.model_validate(company),
            summary=analytics["summary"],
            hiring_funnel=analytics["hiring_funnel"],
            skill_shortfall=analytics["skill_shortfall"],
            recent_applicants=[
                {
                    "application_id": str(a.id),
                    "student_name": (
                        a.student.user.full_name if a.student and a.student.user else ""
                    ),
                    "opportunity_title": a.opportunity.title if a.opportunity else "",
                    "match_score": a.match_score,
                    "status": a.status.value,
                    "submitted_at": a.submitted_at,
                }
                for a in recent
            ],
            active_postings=[
                {
                    "id": str(o.id),
                    "title": o.title,
                    "type": o.opportunity_type.value,
                    "applications": o.applications_count,
                    "views": o.views_count,
                    "deadline": o.application_deadline,
                }
                for o in postings
            ],
        )
    )


@router.get(
    "/{slug}",
    response_model=Envelope[CompanyOut],
    responses=ERRORS,
    summary="Company profile",
)
async def get_company(slug: str, db: DbSession) -> dict:
    company = (
        await db.execute(
            select(Company).where(Company.slug == slug, Company.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if company is None:
        raise NotFoundError("Company not found", code="COMPANY_NOT_FOUND")
    open_positions = (
        await db.execute(
            select(func.count())
            .select_from(Opportunity)
            .where(
                Opportunity.company_id == company.id,
                Opportunity.status == OpportunityStatus.PUBLISHED,
                Opportunity.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    data = CompanyOut.model_validate(company)
    data.open_positions = open_positions
    return ok(data)
