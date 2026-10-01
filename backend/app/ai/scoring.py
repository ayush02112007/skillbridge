"""Shared scoring primitives for the gap, matching and recommendation engines.

Everything here is deliberately pure: no database, no network, no model. That
keeps the core explainable and unit-testable, and means the platform behaves
identically with or without an LLM configured.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.models.enums import ProficiencyLevel, SkillImportance

# How much a requirement counts, by importance.
IMPORTANCE_MULTIPLIER: dict[str, float] = {
    SkillImportance.REQUIRED.value: 1.0,
    SkillImportance.PREFERRED.value: 0.6,
    SkillImportance.OPTIONAL.value: 0.3,
}

# Evidence quality per source, used to weight confidence.
SOURCE_CONFIDENCE: dict[str, float] = {
    "ASSESSMENT": 0.95,
    "CERTIFICATION": 0.85,
    "WORK_EXPERIENCE": 0.8,
    "PROJECT": 0.65,
    "ENDORSEMENT": 0.6,
    "RESUME": 0.5,
    "SELF_REPORTED": 0.35,
}

LEVEL_ORDER = [
    ProficiencyLevel.NONE, ProficiencyLevel.BEGINNER, ProficiencyLevel.INTERMEDIATE,
    ProficiencyLevel.ADVANCED, ProficiencyLevel.EXPERT,
]


def level_value(level: ProficiencyLevel | str | None) -> int:
    """Ordinal 0-4 for a proficiency level."""
    if level is None:
        return 0
    if isinstance(level, str):
        try:
            level = ProficiencyLevel(level)
        except ValueError:
            return 0
    return level.score


def level_label(value: int) -> str:
    return LEVEL_ORDER[max(0, min(4, value))].value


@dataclass(slots=True)
class Requirement:
    """What a role or posting asks for in one skill."""

    skill_id: str
    skill_name: str
    required_level: ProficiencyLevel
    importance: SkillImportance = SkillImportance.REQUIRED
    weight: float = 1.0
    demand_score: float = 0.0
    category: str = ""
    #: Canonical taxonomy slug, e.g. "nodejs". Carried through so downstream
    #: logic never has to re-derive it from the display name.
    slug: str = ""

    @property
    def effective_weight(self) -> float:
        return self.weight * IMPORTANCE_MULTIPLIER.get(
            self.importance.value if hasattr(self.importance, "value") else str(self.importance),
            1.0,
        )


@dataclass(slots=True)
class HeldSkill:
    """What a student actually has, and how well evidenced it is."""

    skill_id: str
    skill_name: str
    level: ProficiencyLevel
    score: float = 0.0
    confidence: float = 0.35
    source: str = "SELF_REPORTED"
    category: str = ""
    slug: str = ""


def coverage(held: HeldSkill | None, requirement: Requirement) -> float:
    """How much of a requirement a held skill satisfies, in 0..1.

    Exceeding the requirement does not earn extra credit - a role needs what it
    needs - so the ratio is capped at 1.0.
    """
    required = level_value(requirement.required_level)
    if required <= 0:
        return 1.0
    current = level_value(held.level) if held else 0
    return min(1.0, current / required)


def evidence_weighted_coverage(held: HeldSkill | None, requirement: Requirement) -> float:
    """Coverage discounted by how well the claim is evidenced.

    A self-reported 'Advanced' is worth less than an assessed 'Advanced'. The
    discount is bounded so an unassessed skill still counts for most of its
    value - we inform, we do not punish.
    """
    base = coverage(held, requirement)
    if base <= 0 or held is None:
        return base
    confidence = max(0.0, min(1.0, held.confidence))
    return base * (0.7 + 0.3 * confidence)


def readiness_score(
    held_by_skill: dict[str, HeldSkill], requirements: Iterable[Requirement]
) -> float:
    """Weighted percentage of a role's requirements that are met (0-100)."""
    requirements = list(requirements)
    total_weight = sum(r.effective_weight for r in requirements)
    if total_weight <= 0:
        return 0.0
    earned = sum(
        evidence_weighted_coverage(held_by_skill.get(r.skill_id), r) * r.effective_weight
        for r in requirements
    )
    return round(min(100.0, max(0.0, earned / total_weight * 100)), 1)


def blend_scores(existing: float, incoming: float, existing_confidence: float,
                 incoming_confidence: float) -> tuple[float, float]:
    """Combine an existing skill score with new evidence.

    Confidence-weighted so a high-confidence assessment moves the needle more
    than another self-report, and repeated evidence raises confidence.
    """
    ew = max(0.05, existing_confidence)
    iw = max(0.05, incoming_confidence)
    score = (existing * ew + incoming * iw) / (ew + iw)
    # Two independent sources agreeing is worth more than either alone.
    confidence = min(0.99, 1 - (1 - ew) * (1 - iw))
    return round(score, 2), round(confidence, 3)
