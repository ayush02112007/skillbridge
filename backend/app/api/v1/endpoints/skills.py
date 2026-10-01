"""Skill taxonomy and job-role endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import AdminUser, DbSession
from app.core.exceptions import ConflictError, NotFoundError
from app.models.skill import JobRole, RoleSkill, Skill, SkillCategory
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.schemas.skill import (
    JobRoleCreate,
    JobRoleOut,
    JobRoleUpdate,
    SkillBrief,
    SkillCategoryCreate,
    SkillCategoryOut,
    SkillCreate,
    SkillOut,
    SkillUpdate,
    TaxonomyNode,
)
from app.services import skill as skill_service
from app.services.auth import unique_slug

router = APIRouter(prefix="/skills", tags=["Skills"])
roles_router = APIRouter(prefix="/job-roles", tags=["Skills"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Not found"}}


@router.get(
    "",
    response_model=Page[SkillOut],
    summary="Browse skills",
    description="Paginated, filterable list of the skill taxonomy. Public - the "
                "taxonomy is reference data used by the landing page and filters.",
)
async def list_skills(
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    q: Annotated[str | None, Query(description="Search name, slug or alias")] = None,
    category_id: uuid.UUID | None = None,
    category_slug: str | None = None,
    is_soft_skill: bool | None = None,
    trending_only: bool = False,
    sort_by: Annotated[str, Query(pattern="^(name|demand_score)$")] = "name",
) -> Page[SkillOut]:
    stmt = (
        select(Skill)
        .where(Skill.is_active.is_(True))
        .options(selectinload(Skill.category))
    )
    if q:
        needle = f"%{q.lower().strip()}%"
        stmt = stmt.where(
            or_(
                func.lower(Skill.name).like(needle),
                Skill.slug.like(needle),
                func.lower(func.cast(Skill.aliases, __import__("sqlalchemy").String)).like(needle),
            )
        )
    if category_id:
        stmt = stmt.where(Skill.category_id == category_id)
    if category_slug:
        stmt = stmt.join(SkillCategory).where(SkillCategory.slug == category_slug)
    if is_soft_skill is not None:
        stmt = stmt.where(Skill.is_soft_skill.is_(is_soft_skill))
    if trending_only:
        stmt = stmt.where(Skill.is_trending.is_(True))

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    order = Skill.demand_score.desc() if sort_by == "demand_score" else Skill.name.asc()
    rows = (
        await db.execute(stmt.order_by(order).offset(page.offset).limit(page.limit))
    ).scalars().all()
    return Page.build(
        [SkillOut.model_validate(r) for r in rows], total, page.page, page.page_size
    )


@router.get(
    "/taxonomy",
    response_model=Envelope[list[TaxonomyNode]],
    summary="Skill taxonomy tree",
    description="Categories with their skills, ready to render as a tree or a "
                "grouped multi-select.",
)
async def taxonomy(db: DbSession) -> dict:
    nodes = await skill_service.get_taxonomy(db)
    return ok(
        [
            TaxonomyNode(
                id=node["id"], name=node["name"], slug=node["slug"], icon=node["icon"],
                color=node["color"], is_soft_skill=node["is_soft_skill"],
                skill_count=node["skill_count"],
                skills=[SkillBrief.model_validate(s) for s in node["skills"]],
            )
            for node in nodes
        ]
    )


@router.get(
    "/categories",
    response_model=Envelope[list[SkillCategoryOut]],
    summary="List skill categories",
)
async def list_categories(db: DbSession) -> dict:
    rows = (
        await db.execute(
            select(SkillCategory)
            .where(SkillCategory.is_active.is_(True))
            .order_by(SkillCategory.display_order, SkillCategory.name)
        )
    ).scalars().all()
    return ok([SkillCategoryOut.model_validate(r) for r in rows])


@router.get(
    "/trending",
    response_model=Envelope[list[SkillOut]],
    summary="Most in-demand skills",
    description="Ranked by the live demand signal, which is recomputed from "
                "published opportunity requirements.",
)
async def trending(db: DbSession, limit: Annotated[int, Query(ge=1, le=50)] = 12) -> dict:
    rows = (
        await db.execute(
            select(Skill)
            .where(Skill.is_active.is_(True))
            .options(selectinload(Skill.category))
            .order_by(Skill.demand_score.desc())
            .limit(limit)
        )
    ).scalars().all()
    return ok([SkillOut.model_validate(r) for r in rows])


@router.get(
    "/{skill_id}",
    response_model=Envelope[SkillOut],
    responses=NOT_FOUND,
    summary="Get one skill",
)
async def get_skill(skill_id: uuid.UUID, db: DbSession) -> dict:
    row = (
        await db.execute(
            select(Skill).where(Skill.id == skill_id).options(selectinload(Skill.category))
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Skill not found", code="SKILL_NOT_FOUND")
    return ok(SkillOut.model_validate(row))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[SkillOut],
    summary="Create a skill",
    description="Platform administrators extend the taxonomy at runtime; no "
                "deployment is needed to add a skill.",
)
async def create_skill(payload: SkillCreate, db: DbSession, _admin: AdminUser) -> dict:
    category = await db.get(SkillCategory, payload.category_id)
    if category is None:
        raise NotFoundError("Skill category not found", code="SKILL_CATEGORY_NOT_FOUND")
    existing = (
        await db.execute(select(Skill).where(func.lower(Skill.name) == payload.name.lower()))
    ).scalar_one_or_none()
    if existing:
        raise ConflictError("A skill with this name already exists", code="SKILL_EXISTS")
    row = Skill(
        name=payload.name.strip(),
        slug=await unique_slug(db, Skill, payload.name),
        category_id=payload.category_id,
        description=payload.description,
        aliases=payload.aliases,
        is_soft_skill=payload.is_soft_skill or category.is_soft_skill,
        is_trending=payload.is_trending,
        learning_resources=payload.learning_resources,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row, ["category"])
    return ok(SkillOut.model_validate(row))


@router.patch(
    "/{skill_id}",
    response_model=Envelope[SkillOut],
    responses=NOT_FOUND,
    summary="Update a skill",
)
async def update_skill(
    skill_id: uuid.UUID, payload: SkillUpdate, db: DbSession, _admin: AdminUser
) -> dict:
    row = await db.get(Skill, skill_id)
    if row is None:
        raise NotFoundError("Skill not found", code="SKILL_NOT_FOUND")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row, ["category"])
    return ok(SkillOut.model_validate(row))


@router.post(
    "/categories",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[SkillCategoryOut],
    summary="Create a skill category",
)
async def create_category(
    payload: SkillCategoryCreate, db: DbSession, _admin: AdminUser
) -> dict:
    row = SkillCategory(
        name=payload.name.strip(),
        slug=await unique_slug(db, SkillCategory, payload.name),
        description=payload.description,
        parent_id=payload.parent_id,
        icon=payload.icon,
        color=payload.color,
        display_order=payload.display_order,
        is_soft_skill=payload.is_soft_skill,
    )
    db.add(row)
    await db.commit()
    return ok(SkillCategoryOut.model_validate(row))


# ----------------------------------------------------------- job roles -----
@roles_router.get(
    "",
    response_model=Page[JobRoleOut],
    summary="Browse job roles",
    description="The career targets a student can aim at. Each carries the "
                "industry-expected skill profile used by the gap engine.",
)
async def list_job_roles(
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    q: str | None = None,
    family: str | None = None,
    seniority: str | None = None,
) -> Page[JobRoleOut]:
    stmt = (
        select(JobRole)
        .where(JobRole.is_active.is_(True))
        .options(
            selectinload(JobRole.required_skills).selectinload(RoleSkill.skill)
        )
    )
    if q:
        stmt = stmt.where(func.lower(JobRole.title).like(f"%{q.lower().strip()}%"))
    if family:
        stmt = stmt.where(JobRole.family == family)
    if seniority:
        stmt = stmt.where(JobRole.seniority == seniority)
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(JobRole.demand_index.desc(), JobRole.title)
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()
    return Page.build(
        [JobRoleOut.model_validate(r) for r in rows], total, page.page, page.page_size
    )


@roles_router.get(
    "/families",
    response_model=Envelope[list[str]],
    summary="List role families",
)
async def role_families(db: DbSession) -> dict:
    rows = (
        await db.execute(
            select(JobRole.family).where(JobRole.is_active.is_(True)).distinct()
        )
    ).scalars().all()
    return ok(sorted(rows))


@roles_router.get(
    "/{job_role_id}",
    response_model=Envelope[JobRoleOut],
    responses=NOT_FOUND,
    summary="Get a job role with its required skills",
)
async def get_job_role(job_role_id: uuid.UUID, db: DbSession) -> dict:
    row = (
        await db.execute(
            select(JobRole)
            .where(JobRole.id == job_role_id)
            .options(selectinload(JobRole.required_skills).selectinload(RoleSkill.skill))
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Job role not found", code="JOB_ROLE_NOT_FOUND")
    return ok(JobRoleOut.model_validate(row))


@roles_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[JobRoleOut],
    summary="Create a job role",
)
async def create_job_role(
    payload: JobRoleCreate, db: DbSession, _admin: AdminUser
) -> dict:
    row = JobRole(
        title=payload.title.strip(),
        slug=await unique_slug(db, JobRole, payload.title),
        family=payload.family,
        description=payload.description,
        responsibilities=payload.responsibilities,
        typical_qualifications=payload.typical_qualifications,
        seniority=payload.seniority,
        avg_salary_min=payload.avg_salary_min,
        avg_salary_max=payload.avg_salary_max,
    )
    db.add(row)
    await db.flush()
    for entry in payload.skills:
        db.add(
            RoleSkill(
                job_role_id=row.id, skill_id=entry.skill_id,
                required_level=entry.required_level, importance=entry.importance,
                weight=entry.weight,
            )
        )
    await db.commit()
    await db.refresh(row)
    reloaded = (
        await db.execute(
            select(JobRole)
            .where(JobRole.id == row.id)
            .options(selectinload(JobRole.required_skills).selectinload(RoleSkill.skill))
        )
    ).scalar_one()
    return ok(JobRoleOut.model_validate(reloaded))


@roles_router.patch(
    "/{job_role_id}",
    response_model=Envelope[JobRoleOut],
    responses=NOT_FOUND,
    summary="Update a job role",
    description="Replacing `skills` replaces the whole requirement set, so the "
                "gap engine always reflects one coherent definition.",
)
async def update_job_role(
    job_role_id: uuid.UUID, payload: JobRoleUpdate, db: DbSession, _admin: AdminUser
) -> dict:
    row = (
        await db.execute(
            select(JobRole)
            .where(JobRole.id == job_role_id)
            .options(selectinload(JobRole.required_skills))
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Job role not found", code="JOB_ROLE_NOT_FOUND")

    changes = payload.model_dump(exclude_unset=True)
    skills = changes.pop("skills", None)
    for field, value in changes.items():
        setattr(row, field, value)
    if skills is not None:
        from sqlalchemy import delete

        await db.execute(delete(RoleSkill).where(RoleSkill.job_role_id == row.id))
        for entry in skills:
            db.add(
                RoleSkill(
                    job_role_id=row.id,
                    skill_id=entry["skill_id"],
                    required_level=entry["required_level"],
                    importance=entry["importance"],
                    weight=entry["weight"],
                )
            )
    await db.commit()
    reloaded = (
        await db.execute(
            select(JobRole)
            .where(JobRole.id == row.id)
            .options(selectinload(JobRole.required_skills).selectinload(RoleSkill.skill))
        )
    ).scalar_one()
    return ok(JobRoleOut.model_validate(reloaded))

