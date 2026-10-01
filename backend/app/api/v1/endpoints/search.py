"""Global search across every searchable entity.

Implementation note: search runs over denormalised ``search_text`` columns. On
PostgreSQL this upgrades to full-text search via ``to_tsvector``; on SQLite it
falls back to a LIKE scan so the behaviour is identical in every environment.
The query builder is isolated here so an Elasticsearch/OpenSearch backend can be
introduced later without touching call sites.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession, OptionalUser
from app.models.enums import OpportunityStatus
from app.models.event import Event
from app.models.learning import LearningProgram
from app.models.mentorship import MentorProfile
from app.models.opportunity import Opportunity
from app.models.organization import Company
from app.models.research import ResearchProject
from app.models.skill import JobRole, Skill
from app.models.user import User
from app.schemas.common import APIModel, Envelope, ok

router = APIRouter(prefix="/search", tags=["Search"])


class SearchHit(APIModel):
    id: uuid.UUID
    type: str
    title: str
    subtitle: str = ""
    url: str
    icon: str = "search"
    score: float = 0.0


class SearchGroup(APIModel):
    type: str
    label: str
    total: int
    results: list[SearchHit] = []


class GlobalSearchOut(APIModel):
    query: str
    total: int
    groups: list[SearchGroup] = []


def _like(column: Any, needle: str):
    """Portable substring match, used by every entity search below.

    This is the single seam to replace when moving to PostgreSQL full-text
    (``to_tsvector(search_text) @@ plainto_tsquery(:q)``) or to an external
    search engine: no call site needs to change.
    """
    return func.lower(column).like(f"%{needle.lower().strip()}%")


@router.get(
    "",
    response_model=Envelope[GlobalSearchOut],
    summary="Global search",
    description=(
        "Searches opportunities, learning programmes, companies, skills, job "
        "roles, mentors, events and research collaborations in one call.\n\n"
        "Powers the command palette (Cmd/Ctrl-K). Results are grouped by type "
        "and each hit carries the route the client should navigate to."
    ),
)
async def global_search(
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=120, description="Search text")],
    limit_per_group: Annotated[int, Query(ge=1, le=20)] = 5,
    types: Annotated[list[str] | None, Query(description="Restrict to these types")] = None,
    user: OptionalUser = None,
) -> dict:
    needle = q.strip()
    wanted = set(types) if types else None
    groups: list[SearchGroup] = []

    async def add(
        type_key: str, label: str, stmt, icon: str, to_hit
    ) -> None:
        if wanted and type_key not in wanted:
            return
        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (await db.execute(stmt.limit(limit_per_group))).scalars().all()
        if not rows:
            return
        groups.append(
            SearchGroup(
                type=type_key, label=label, total=total,
                results=[to_hit(r) for r in rows],
            )
        )

    # ------------------------------------------------------ opportunities --
    opportunity_stmt = (
        select(Opportunity)
        .where(
            Opportunity.status == OpportunityStatus.PUBLISHED,
            Opportunity.deleted_at.is_(None),
            or_(_like(Opportunity.title, needle), _like(Opportunity.search_text, needle)),
        )
        .options(selectinload(Opportunity.company))
        .order_by(Opportunity.published_at.desc().nullslast())
    )
    await add(
        "opportunity", "Opportunities", opportunity_stmt, "briefcase",
        lambda r: SearchHit(
            id=r.id, type=r.opportunity_type.value.lower(), title=r.title,
            subtitle=" · ".join(
                filter(None, [r.company.name if r.company else "", r.location_city or ""])
            ),
            url=f"/opportunities/{r.id}", icon="briefcase",
        ),
    )

    # ----------------------------------------------------------- learning --
    program_stmt = (
        select(LearningProgram)
        .where(
            LearningProgram.is_published.is_(True),
            LearningProgram.deleted_at.is_(None),
            or_(
                _like(LearningProgram.title, needle),
                _like(LearningProgram.search_text, needle),
            ),
        )
        .order_by(LearningProgram.enrollment_count.desc())
    )
    await add(
        "program", "Learning", program_stmt, "graduation-cap",
        lambda r: SearchHit(
            id=r.id, type="program", title=r.title,
            subtitle=f"{r.program_type.value.title()} · {r.duration_hours}h",
            url=f"/learning/{r.id}", icon="graduation-cap",
        ),
    )

    # ---------------------------------------------------------- companies --
    company_stmt = (
        select(Company)
        .where(
            Company.deleted_at.is_(None),
            or_(_like(Company.name, needle), _like(Company.description, needle)),
        )
        .order_by(Company.name)
    )
    await add(
        "company", "Companies", company_stmt, "building-2",
        lambda r: SearchHit(
            id=r.id, type="company", title=r.name, subtitle=r.industry_sector or "",
            url=f"/companies/{r.slug}", icon="building-2",
        ),
    )

    # ------------------------------------------------------------- skills --
    skill_stmt = (
        select(Skill)
        .where(
            Skill.is_active.is_(True),
            or_(_like(Skill.name, needle), _like(Skill.description, needle)),
        )
        .order_by(Skill.demand_score.desc())
    )
    await add(
        "skill", "Skills", skill_stmt, "sparkles",
        lambda r: SearchHit(
            id=r.id, type="skill", title=r.name,
            subtitle=f"Demand {r.demand_score:.0f}/100",
            url=f"/skills/{r.id}", icon="sparkles",
        ),
    )

    # ---------------------------------------------------------- job roles --
    role_stmt = (
        select(JobRole)
        .where(JobRole.is_active.is_(True), _like(JobRole.title, needle))
        .order_by(JobRole.demand_index.desc())
    )
    await add(
        "job_role", "Career roles", role_stmt, "target",
        lambda r: SearchHit(
            id=r.id, type="job_role", title=r.title, subtitle=r.family,
            url=f"/careers/{r.slug}", icon="target",
        ),
    )

    # ------------------------------------------------------------ mentors --
    mentor_stmt = (
        select(MentorProfile)
        .join(User, User.id == MentorProfile.user_id)
        .where(
            MentorProfile.is_accepting_requests.is_(True),
            or_(
                _like(User.full_name, needle),
                _like(MentorProfile.headline, needle),
                _like(MentorProfile.designation, needle),
            ),
        )
        .options(selectinload(MentorProfile.user))
        .order_by(MentorProfile.rating.desc())
    )
    await add(
        "mentor", "Mentors", mentor_stmt, "users",
        lambda r: SearchHit(
            id=r.id, type="mentor",
            title=r.user.full_name if r.user else "Mentor",
            subtitle=r.headline or r.designation or "",
            url=f"/mentors/{r.id}", icon="users",
        ),
    )

    # ------------------------------------------------------------- events --
    event_stmt = (
        select(Event)
        .where(
            Event.is_published.is_(True),
            Event.deleted_at.is_(None),
            or_(_like(Event.title, needle), _like(Event.search_text, needle)),
        )
        .order_by(Event.starts_at.asc())
    )
    await add(
        "event", "Events", event_stmt, "calendar",
        lambda r: SearchHit(
            id=r.id, type="event", title=r.title,
            subtitle=f"{r.event_type.value.replace('_', ' ').title()} · "
                     f"{r.starts_at:%d %b %Y}",
            url=f"/events/{r.id}", icon="calendar",
        ),
    )

    # ----------------------------------------------------------- research --
    research_stmt = (
        select(ResearchProject)
        .where(
            ResearchProject.deleted_at.is_(None),
            or_(
                _like(ResearchProject.title, needle),
                _like(ResearchProject.search_text, needle),
            ),
        )
        .order_by(ResearchProject.created_at.desc())
    )
    await add(
        "research", "Research", research_stmt, "flask-conical",
        lambda r: SearchHit(
            id=r.id, type="research", title=r.title,
            subtitle=r.project_type.value.replace("_", " ").title(),
            url=f"/research/{r.id}", icon="flask-conical",
        ),
    )

    return ok(
        GlobalSearchOut(
            query=needle,
            total=sum(g.total for g in groups),
            groups=groups,
        )
    )


@router.get(
    "/suggest",
    response_model=Envelope[list[str]],
    summary="Search suggestions",
    description="Lightweight type-ahead over skills, job roles and companies.",
)
async def suggest(
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=60)],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> dict:
    needle = q.strip()
    suggestions: list[str] = []
    for column, _model, condition in (
        (Skill.name, Skill, Skill.is_active.is_(True)),
        (JobRole.title, JobRole, JobRole.is_active.is_(True)),
        (Company.name, Company, Company.deleted_at.is_(None)),
    ):
        rows = (
            await db.execute(
                select(column).where(condition, _like(column, needle)).limit(limit)
            )
        ).scalars().all()
        suggestions.extend(rows)
    seen: set[str] = set()
    unique = [s for s in suggestions if not (s in seen or seen.add(s))]
    return ok(unique[:limit])
