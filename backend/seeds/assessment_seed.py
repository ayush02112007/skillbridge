"""Idempotent loader for the assessment catalogue."""
from __future__ import annotations

import hashlib
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.assessment import Assessment, AssessmentOption, AssessmentQuestion
from app.models.enums import AssessmentType, Difficulty, QuestionType
from app.models.skill import JobRole, Skill
from seeds import assessment_bank as bank

log = get_logger("seed.assessments")


def _shuffled(prompt: str, options: list[tuple[str, bool]]) -> list[tuple[str, bool]]:
    """Deterministically vary answer position.

    The bank is authored with the correct option first for readability, which
    would otherwise make "always pick the first option" a winning strategy. The
    order is derived from a hash of the prompt, so it is stable across seed runs
    and across environments, but uncorrelated with correctness.
    """
    seed = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)
    shuffled = list(options)
    random.Random(seed).shuffle(shuffled)
    return shuffled


def _question_type(options: list[tuple[str, bool]]) -> QuestionType:
    correct = sum(1 for _, is_correct in options if is_correct)
    if len(options) == 2 and {o[0].lower() for o in options} == {"true", "false"}:
        return QuestionType.TRUE_FALSE
    return QuestionType.MULTI_CHOICE if correct > 1 else QuestionType.SINGLE_CHOICE


async def seed_assessments(db: AsyncSession) -> dict[str, int]:
    stats = {"assessments": 0, "questions": 0, "options": 0}
    skills = {s.slug: s for s in (await db.execute(select(Skill))).scalars()}
    roles = {r.slug: r for r in (await db.execute(select(JobRole))).scalars()}
    existing = {a.slug: a for a in (await db.execute(select(Assessment))).scalars()}

    specs = list(bank.ASSESSMENTS)
    specs.append(
        {
            "slug": "professional-skills-self-assessment",
            "title": "Professional Skills Self-Assessment",
            "description": (
                "A short, honest self-rating of the professional skills employers "
                "ask about most. Self-assessed levels carry lower confidence than "
                "tested ones - they are a starting point, not proof."
            ),
            "type": "SELF_ASSESSMENT", "domain": "Professional", "role": None,
            "primary_skill": "communication", "duration": 10, "passing": 0,
            "questions": None,
        }
    )

    for spec in specs:
        assessment = existing.get(spec["slug"])
        if assessment is None:
            assessment = Assessment(
                slug=spec["slug"],
                title=spec["title"],
                description=spec["description"],
                assessment_type=AssessmentType(spec["type"]),
                domain=spec["domain"],
                job_role_id=roles[spec["role"]].id if spec.get("role") in roles else None,
                primary_skill_id=(
                    skills[spec["primary_skill"]].id
                    if spec.get("primary_skill") in skills
                    else None
                ),
                duration_minutes=spec["duration"],
                passing_score=float(spec["passing"]),
                max_attempts=3,
                cooldown_hours=0 if spec["type"] == "SELF_ASSESSMENT" else 12,
                is_published=True,
            )
            db.add(assessment)
            await db.flush()
            stats["assessments"] += 1
        else:
            assessment.title = spec["title"]
            assessment.description = spec["description"]
            assessment.duration_minutes = spec["duration"]
            assessment.passing_score = float(spec["passing"])

        has_questions = (
            await db.execute(
                select(AssessmentQuestion.id)
                .where(AssessmentQuestion.assessment_id == assessment.id)
                .limit(1)
            )
        ).first()
        if has_questions:
            continue

        if spec["questions"] is None:
            # Likert self-assessment built from the soft-skill statements.
            for order, (skill_slug, prompt) in enumerate(bank.SOFT_SKILLS):
                skill = skills.get(skill_slug)
                if skill is None:
                    continue
                question = AssessmentQuestion(
                    assessment_id=assessment.id,
                    skill_id=skill.id,
                    question_type=QuestionType.LIKERT,
                    prompt=prompt,
                    difficulty=Difficulty.MEDIUM,
                    weight=1.0,
                    explanation=(
                        "Self-assessed levels are recorded with lower confidence "
                        "than tested skills, and are clearly labelled as such on "
                        "your profile."
                    ),
                    display_order=order,
                )
                db.add(question)
                await db.flush()
                stats["questions"] += 1
                for option_order, (label, value) in enumerate(bank.LIKERT_OPTIONS):
                    db.add(
                        AssessmentOption(
                            question_id=question.id, label=label, is_correct=False,
                            proficiency_value=value, display_order=option_order,
                        )
                    )
                    stats["options"] += 1
            continue

        for order, (skill_slug, difficulty, prompt, options, explanation) in enumerate(
            spec["questions"]
        ):
            skill = skills.get(skill_slug)
            if skill is None:
                log.warning("seed.unknown_skill", skill=skill_slug)
                continue
            question = AssessmentQuestion(
                assessment_id=assessment.id,
                skill_id=skill.id,
                question_type=_question_type(options),
                prompt=prompt,
                difficulty=Difficulty(difficulty),
                weight=1.0,
                explanation=explanation,
                display_order=order,
            )
            db.add(question)
            await db.flush()
            stats["questions"] += 1
            for option_order, (label, is_correct) in enumerate(_shuffled(prompt, options)):
                db.add(
                    AssessmentOption(
                        question_id=question.id, label=label, is_correct=is_correct,
                        display_order=option_order,
                    )
                )
                stats["options"] += 1

    await db.flush()
    log.info("seed.assessments_complete", **stats)
    return stats
