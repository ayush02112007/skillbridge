"""Idempotent loader for the reference catalogue (categories, skills, roles).

Run on every deployment: it creates what is missing and refreshes metadata on
what exists, without touching admin-authored additions.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.enums import ProficiencyLevel, SkillImportance
from app.models.skill import JobRole, RoleSkill, Skill, SkillCategory
from seeds import catalog

log = get_logger("seed.catalog")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


async def seed_catalog(db: AsyncSession) -> dict[str, int]:
    stats = {"categories": 0, "skills": 0, "job_roles": 0, "role_skills": 0}

    # ---------------------------------------------------------- categories --
    existing_categories = {
        c.slug: c for c in (await db.execute(select(SkillCategory))).scalars()
    }
    for order, (slug, name, icon, color, is_soft) in enumerate(catalog.CATEGORIES):
        category = existing_categories.get(slug)
        if category is None:
            category = SkillCategory(
                slug=slug, name=name, icon=icon, color=color,
                is_soft_skill=is_soft, display_order=order,
            )
            db.add(category)
            existing_categories[slug] = category
            stats["categories"] += 1
        else:
            category.name, category.icon = name, icon
            category.color, category.display_order = color, order
            category.is_soft_skill = is_soft
    await db.flush()

    # -------------------------------------------------------------- skills --
    existing_skills = {s.slug: s for s in (await db.execute(select(Skill))).scalars()}
    for slug, name, category_slug, aliases, demand, trending in catalog.SKILLS:
        category = existing_categories[category_slug]
        skill = existing_skills.get(slug)
        if skill is None:
            skill = Skill(
                slug=slug, name=name, category_id=category.id, aliases=aliases,
                demand_score=float(demand), is_trending=trending,
                is_soft_skill=category.is_soft_skill,
            )
            db.add(skill)
            existing_skills[slug] = skill
            stats["skills"] += 1
        else:
            skill.name, skill.category_id = name, category.id
            skill.aliases, skill.is_trending = aliases, trending
            skill.is_soft_skill = category.is_soft_skill
            # Demand is a live signal; only seed it when it has never been set.
            if not skill.demand_score:
                skill.demand_score = float(demand)
    await db.flush()

    # ----------------------------------------------------------- job roles --
    existing_roles = {r.slug: r for r in (await db.execute(select(JobRole))).scalars()}
    for role_slug, spec in catalog.JOB_ROLES.items():
        role = existing_roles.get(role_slug)
        salary_min, salary_max = spec["salary"]
        if role is None:
            role = JobRole(
                slug=role_slug, title=spec["title"], family=spec["family"],
                description=spec["description"],
                responsibilities=spec.get("responsibilities", []),
                seniority=spec["seniority"], avg_salary_min=salary_min,
                avg_salary_max=salary_max, demand_index=float(spec["demand"]),
            )
            db.add(role)
            existing_roles[role_slug] = role
            stats["job_roles"] += 1
        else:
            role.title, role.family = spec["title"], spec["family"]
            role.description = spec["description"]
            role.responsibilities = spec.get("responsibilities", [])
            role.seniority = spec["seniority"]
            role.avg_salary_min, role.avg_salary_max = salary_min, salary_max
            role.demand_index = float(spec["demand"])
        await db.flush()

        existing_links = {
            rs.skill_id: rs
            for rs in (
                await db.execute(select(RoleSkill).where(RoleSkill.job_role_id == role.id))
            ).scalars()
        }
        for skill_slug, level, importance, weight in spec["skills"]:
            skill = existing_skills.get(skill_slug)
            if skill is None:
                log.warning("seed.unknown_skill", role=role_slug, skill=skill_slug)
                continue
            link = existing_links.get(skill.id)
            if link is None:
                db.add(
                    RoleSkill(
                        job_role_id=role.id, skill_id=skill.id,
                        required_level=ProficiencyLevel(level),
                        importance=SkillImportance(importance), weight=float(weight),
                    )
                )
                stats["role_skills"] += 1
            else:
                link.required_level = ProficiencyLevel(level)
                link.importance = SkillImportance(importance)
                link.weight = float(weight)
    await db.flush()
    log.info("seed.catalog_complete", **stats)
    return stats
