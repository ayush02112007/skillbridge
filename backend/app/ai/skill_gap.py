"""Skill-gap analysis: the comparison at the heart of the product.

Given what a student has and what a target role requires, produce a prioritised,
human-readable plan. The output is intentionally explainable - every number can
be traced to a requirement and the evidence behind the student's level.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from app.ai.scoring import (
    HeldSkill,
    Requirement,
    coverage,
    evidence_weighted_coverage,
    level_value,
    readiness_score,
)
from app.models.enums import ProficiencyLevel, SkillImportance

STATUS_MISSING = "MISSING"
STATUS_WEAK = "WEAK"
STATUS_STRONG = "STRONG"


@dataclass(slots=True)
class GapItem:
    skill_id: str
    skill_name: str
    skill_slug: str
    category: str
    current_level: str
    required_level: str
    status: str
    gap_size: int
    importance: str
    weight: float
    coverage: float
    priority: int = 99
    recommendation: str = ""


@dataclass(slots=True)
class GapResult:
    job_role_id: str
    job_role_title: str
    readiness_score: float
    gap_percentage: float
    matched_count: int
    total_required: int
    items: list[GapItem] = field(default_factory=list)
    summary: str = ""

    @property
    def missing(self) -> list[GapItem]:
        return [i for i in self.items if i.status == STATUS_MISSING]

    @property
    def weak(self) -> list[GapItem]:
        return [i for i in self.items if i.status == STATUS_WEAK]

    @property
    def strong(self) -> list[GapItem]:
        return [i for i in self.items if i.status == STATUS_STRONG]

    @property
    def priority_skills(self) -> list[GapItem]:
        return [i for i in self.items if i.status != STATUS_STRONG][:5]


_IMPORTANCE_RANK = {
    SkillImportance.REQUIRED.value: 0,
    SkillImportance.PREFERRED.value: 1,
    SkillImportance.OPTIONAL.value: 2,
}


def _status(held: HeldSkill | None, requirement: Requirement) -> tuple[str, int]:
    required = level_value(requirement.required_level)
    current = level_value(held.level) if held else 0
    gap = max(0, required - current)
    if current == 0:
        return STATUS_MISSING, gap
    if current >= required:
        return STATUS_STRONG, 0
    return STATUS_WEAK, gap


def _recommendation(item_status: str, skill_name: str, current: str, required: str) -> str:
    if item_status == STATUS_MISSING:
        return (
            f"Start {skill_name} from the fundamentals and build one small project "
            f"with it - roles at this level expect {required.lower()} proficiency."
        )
    if item_status == STATUS_WEAK:
        return (
            f"You are at {current.lower()} in {skill_name}; the role expects "
            f"{required.lower()}. Deepen it with a substantial project and verify "
            "with a skill assessment."
        )
    return f"{skill_name} already meets the bar - keep it warm and use it as evidence."


def analyse(
    held_skills: Iterable[HeldSkill],
    requirements: Iterable[Requirement],
    *,
    job_role_id: str = "",
    job_role_title: str = "",
) -> GapResult:
    """Compare a skill profile against a set of requirements."""
    held_by_skill = {h.skill_id: h for h in held_skills}
    requirements = list(requirements)

    items: list[GapItem] = []
    for requirement in requirements:
        held = held_by_skill.get(requirement.skill_id)
        status, gap = _status(held, requirement)
        current_label = held.level.value if held else ProficiencyLevel.NONE.value
        required_label = requirement.required_level.value
        importance = (
            requirement.importance.value
            if hasattr(requirement.importance, "value")
            else str(requirement.importance)
        )
        items.append(
            GapItem(
                skill_id=requirement.skill_id,
                skill_name=requirement.skill_name,
                skill_slug=requirement.slug,
                category=requirement.category,
                current_level=current_label,
                required_level=required_label,
                status=status,
                gap_size=gap,
                importance=importance,
                weight=round(requirement.effective_weight, 3),
                coverage=round(coverage(held, requirement), 3),
                recommendation=_recommendation(
                    status, requirement.skill_name, current_label, required_label
                ),
            )
        )

    # Priority: required before preferred, then biggest gap, then heaviest
    # weight, then market demand. Strong skills sink to the bottom.
    def sort_key(item: GapItem) -> tuple:
        requirement = next(r for r in requirements if r.skill_id == item.skill_id)
        return (
            item.status == STATUS_STRONG,
            _IMPORTANCE_RANK.get(item.importance, 3),
            -item.gap_size,
            -item.weight,
            -requirement.demand_score,
            item.skill_name,
        )

    items.sort(key=sort_key)
    for index, item in enumerate(items, start=1):
        item.priority = index if item.status != STATUS_STRONG else 99

    readiness = readiness_score(held_by_skill, requirements)
    required_items = [
        i for i in items if i.importance == SkillImportance.REQUIRED.value
    ]
    matched = sum(1 for i in required_items if i.status == STATUS_STRONG)

    result = GapResult(
        job_role_id=job_role_id,
        job_role_title=job_role_title,
        readiness_score=readiness,
        gap_percentage=round(100 - readiness, 1),
        matched_count=matched,
        total_required=len(required_items),
        items=items,
    )
    result.summary = summarise(result)
    return result


def summarise(result: GapResult) -> str:
    """One paragraph a student can act on, with no jargon."""
    title = result.job_role_title or "this role"
    missing, weak = result.missing, result.weak
    if result.readiness_score >= 85:
        head = (
            f"You are well prepared for {title} - you meet "
            f"{result.matched_count} of {result.total_required} core requirements."
        )
    elif result.readiness_score >= 60:
        head = (
            f"You are on track for {title}, meeting {result.matched_count} of "
            f"{result.total_required} core requirements."
        )
    elif result.readiness_score >= 35:
        head = (
            f"You have a foundation for {title}, but several core skills are "
            "still short of what employers ask for."
        )
    else:
        head = (
            f"{title} is a stretch target right now. The good news is the path "
            "is concrete and short."
        )

    parts = [head]
    if missing:
        names = ", ".join(i.skill_name for i in missing[:3])
        parts.append(
            f"The biggest blockers are skills you have not started yet: {names}"
            + ("." if len(missing) <= 3 else f", and {len(missing) - 3} more.")
        )
    if weak:
        names = ", ".join(i.skill_name for i in weak[:3])
        parts.append(f"You are partway there on {names}; deepening these lifts your score fastest.")
    if result.strong:
        names = ", ".join(i.skill_name for i in result.strong[:3])
        parts.append(f"Lead with your strengths in {names} when you apply.")
    return " ".join(parts)


def compare_to_requirements(
    held_skills: Iterable[HeldSkill], requirements: Iterable[Requirement]
) -> tuple[list[str], list[str], float]:
    """Lightweight version used by the matcher: (matched, missing, coverage 0-1)."""
    held_by_skill = {h.skill_id: h for h in held_skills}
    requirements = list(requirements)
    matched: list[str] = []
    missing: list[str] = []
    total_weight = sum(r.effective_weight for r in requirements)
    earned = 0.0
    for requirement in requirements:
        held = held_by_skill.get(requirement.skill_id)
        value = evidence_weighted_coverage(held, requirement)
        earned += value * requirement.effective_weight
        if held and level_value(held.level) >= level_value(requirement.required_level):
            matched.append(requirement.skill_name)
        elif not held or value < 0.75:
            missing.append(requirement.skill_name)
        else:
            matched.append(requirement.skill_name)
    ratio = (earned / total_weight) if total_weight > 0 else 0.0
    return matched, missing, round(min(1.0, ratio), 4)
