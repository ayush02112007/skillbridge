"""Learning-path generation.

Turns a skill gap into an ordered plan: what to learn, in what order, why, and
which available programmes cover it. Purely deterministic - the ordering comes
from the gap engine's priorities and from real prerequisite relationships, not
from a model.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from app.ai.skill_gap import GapItem, GapResult

# Rough effort to move one proficiency level, in study hours.
HOURS_PER_LEVEL: dict[str, int] = {
    "BEGINNER": 20,
    "INTERMEDIATE": 40,
    "ADVANCED": 70,
    "EXPERT": 110,
}

# Skills that are much easier once another is in place. Used only to order the
# plan sensibly; a missing prerequisite never blocks a step.
PREREQUISITES: dict[str, set[str]] = {
    "fastapi": {"python"},
    "django": {"python"},
    "flask": {"python"},
    "pandas": {"python"},
    "numpy": {"python"},
    "scikit-learn": {"python", "numpy"},
    "pytorch": {"python", "numpy"},
    "tensorflow": {"python", "numpy"},
    "machine-learning": {"python", "statistics"},
    "deep-learning": {"machine-learning"},
    "nlp": {"machine-learning"},
    "computer-vision": {"machine-learning"},
    "mlops": {"machine-learning", "docker"},
    "llm-engineering": {"python"},
    "spring-boot": {"java"},
    "react": {"javascript"},
    "nextjs": {"react"},
    "redux": {"react"},
    "express": {"nodejs"},
    "nestjs": {"nodejs", "typescript"},
    "typescript": {"javascript"},
    "kubernetes": {"docker"},
    "terraform": {"aws"},
    "query-optimization": {"sql"},
    "database-design": {"sql"},
    "etl": {"sql", "python"},
    "spark": {"python"},
    "penetration-testing": {"network-security"},
    "siem": {"network-security"},
    "application-security": {"owasp"},
}


def _slug(item: GapItem) -> str:
    """Prefer the canonical taxonomy slug; fall back to the display name."""
    return item.skill_slug or re.sub(
        r"[^a-z0-9]+", "-", item.skill_name.lower()
    ).strip("-")


@dataclass(slots=True)
class PathStep:
    order: int
    skill_id: str
    skill_name: str
    current_level: str
    target_level: str
    status: str
    why: str
    estimated_hours: int
    programs: list[dict[str, Any]] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "current_level": self.current_level,
            "target_level": self.target_level,
            "status": self.status,
            "why": self.why,
            "estimated_hours": self.estimated_hours,
            "programs": self.programs,
            "prerequisites": self.prerequisites,
        }


@dataclass(slots=True)
class LearningPlan:
    title: str
    summary: str
    estimated_weeks: int
    total_hours: int
    steps: list[PathStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "estimated_weeks": self.estimated_weeks,
            "total_hours": self.total_hours,
            "steps": [s.to_dict() for s in self.steps],
        }


def _hours_for(item: GapItem) -> int:
    """Effort to close one gap: the sum of the levels still to climb."""
    order = ["NONE", "BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"]
    try:
        start = order.index(item.current_level)
        end = order.index(item.required_level)
    except ValueError:
        return HOURS_PER_LEVEL["INTERMEDIATE"]
    return sum(HOURS_PER_LEVEL[order[level]] for level in range(start + 1, end + 1)) or 10


def _why(item: GapItem, role_title: str) -> str:
    if item.status == "MISSING":
        return (
            f"{item.skill_name} is a {item.importance.lower()} skill for "
            f"{role_title} and you have no evidence for it yet. It is the "
            "single biggest thing standing between your profile and this role."
            if item.priority == 1
            else f"{item.skill_name} is listed as {item.importance.lower()} for "
            f"{role_title} at {item.required_level.lower()} level, and is not "
            "yet on your profile."
        )
    return (
        f"You are at {item.current_level.lower()} in {item.skill_name} but "
        f"{role_title} expects {item.required_level.lower()}. Closing a single "
        "level here is usually faster than starting a new skill."
    )


def order_steps(items: Iterable[GapItem]) -> list[GapItem]:
    """Sort gap items into a teachable order, respecting prerequisites.

    The gap engine's priority is the main signal; prerequisites only pull a
    dependency in front of the skill that needs it.
    """
    items = [i for i in items if i.status != "STRONG"]
    by_slug = {_slug(i): i for i in items}
    ordered: list[GapItem] = []
    placed: set[str] = set()

    def place(item: GapItem, guard: set[str] | None = None) -> None:
        slug = _slug(item)
        if slug in placed:
            return
        guard = guard or set()
        if slug in guard:  # defensive: never loop on a cyclic definition
            return
        for prerequisite in sorted(PREREQUISITES.get(slug, set())):
            dependency = by_slug.get(prerequisite)
            if dependency is not None:
                place(dependency, guard | {slug})
        placed.add(slug)
        ordered.append(item)

    for item in sorted(items, key=lambda i: i.priority):
        place(item)
    return ordered


def build_plan(
    gap: GapResult,
    programs_by_skill: dict[str, list[dict[str, Any]]] | None = None,
    *,
    hours_per_week: int = 8,
    max_steps: int = 8,
) -> LearningPlan:
    programs_by_skill = programs_by_skill or {}
    steps: list[PathStep] = []
    total_hours = 0

    for index, item in enumerate(order_steps(gap.items)[:max_steps], start=1):
        hours = _hours_for(item)
        total_hours += hours
        slug = _slug(item)
        steps.append(
            PathStep(
                order=index,
                skill_id=item.skill_id,
                skill_name=item.skill_name,
                current_level=item.current_level,
                target_level=item.required_level,
                status=item.status,
                why=_why(item, gap.job_role_title or "this role"),
                estimated_hours=hours,
                programs=programs_by_skill.get(item.skill_id, [])[:3],
                prerequisites=sorted(
                    p.replace("-", " ").title() for p in PREREQUISITES.get(slug, set())
                ),
            )
        )

    weeks = max(1, round(total_hours / max(1, hours_per_week)))
    if not steps:
        summary = (
            f"You already meet every requirement recorded for "
            f"{gap.job_role_title}. Keep your evidence current and start applying."
        )
    else:
        first = steps[0]
        summary = (
            f"{len(steps)} step(s) to close your gap for {gap.job_role_title}, "
            f"about {total_hours} hours of focused work "
            f"(~{weeks} week(s) at {hours_per_week} hours a week). "
            f"Start with {first.skill_name}: {first.why.split('.')[0]}."
        )

    return LearningPlan(
        title=f"Path to {gap.job_role_title}",
        summary=summary,
        estimated_weeks=weeks,
        total_hours=total_hours,
        steps=steps,
    )
