"""Skill assessment engine: attempts, scoring and skill-profile updates.

Scoring is transparent and reproducible:

* every question carries a ``weight`` and a ``difficulty``; its maximum score is
  ``weight * difficulty.weight``;
* multi-select questions award proportional credit and subtract for incorrect
  selections, so guessing everything scores zero rather than full marks;
* scores are aggregated per skill, and a skill's **confidence** grows with the
  number of questions that measured it - one question is a hint, six is evidence.
"""
from __future__ import annotations

import random
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.assessment import (
    Assessment,
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
    AttemptSkillScore,
)
from app.models.enums import (
    AttemptStatus,
    ProficiencyLevel,
    QuestionType,
    SkillSource,
)
from app.models.profile import StudentProfile
from app.services import skill as skill_service

log = get_logger("assessments")

# Confidence a single skill score earns, by how many questions measured it.
MIN_CONFIDENCE = 0.55
MAX_CONFIDENCE = 0.95
CONFIDENCE_PER_QUESTION = 0.09


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def confidence_for(question_count: int) -> float:
    return round(
        min(MAX_CONFIDENCE, MIN_CONFIDENCE + CONFIDENCE_PER_QUESTION * (question_count - 1)),
        3,
    )


async def get_assessment_or_404(
    db: AsyncSession, assessment_id: uuid.UUID, *, with_questions: bool = False
) -> Assessment:
    stmt = select(Assessment).where(Assessment.id == assessment_id)
    if with_questions:
        stmt = stmt.options(
            selectinload(Assessment.questions).selectinload(AssessmentQuestion.options),
            selectinload(Assessment.questions).selectinload(AssessmentQuestion.skill),
        # populate_existing: the Assessment may already be in the identity map
        # from a shallower query, and without this the eager load is skipped.
        ).execution_options(populate_existing=True)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Assessment not found", code="ASSESSMENT_NOT_FOUND")
    return row


# ----------------------------------------------------------- start ---------
async def start_attempt(
    db: AsyncSession, assessment: Assessment, student: StudentProfile
) -> tuple[AssessmentAttempt, list[AssessmentQuestion]]:
    """Create an attempt and fix the question order for it."""
    if not assessment.is_published:
        raise BusinessRuleError(
            "This assessment is not available", code="ASSESSMENT_NOT_PUBLISHED"
        )

    previous = (
        await db.execute(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.assessment_id == assessment.id,
                AssessmentAttempt.student_id == student.id,
            )
            .order_by(AssessmentAttempt.attempt_number.desc())
        )
    ).scalars().all()

    live = next(
        (a for a in previous if a.status == AttemptStatus.IN_PROGRESS), None
    )
    if live is not None:
        expires = _aware(live.expires_at)
        if expires and expires < _now():
            live.status = AttemptStatus.EXPIRED
            await db.flush()
        else:
            questions = await _questions_for(db, assessment, live.question_order)
            return live, questions

    finished = [a for a in previous if a.status != AttemptStatus.IN_PROGRESS]
    if len(finished) >= assessment.max_attempts:
        raise BusinessRuleError(
            f"You have used all {assessment.max_attempts} attempts for this assessment",
            code="MAX_ATTEMPTS_REACHED",
        )
    if finished and assessment.cooldown_hours:
        last = max(
            (_aware(a.submitted_at) or _aware(a.created_at) for a in finished),
            default=None,
        )
        if last:
            ready_at = last + timedelta(hours=assessment.cooldown_hours)
            if ready_at > _now():
                hours = max(1, int((ready_at - _now()).total_seconds() // 3600) + 1)
                raise BusinessRuleError(
                    f"You can retake this assessment in about {hours} hour(s)",
                    code="ASSESSMENT_COOLDOWN",
                    details={"retry_after": ready_at.isoformat()},
                )

    questions = [q for q in assessment.questions if q.is_active]
    if not questions:
        raise BusinessRuleError(
            "This assessment has no questions yet", code="ASSESSMENT_EMPTY"
        )
    if assessment.shuffle_questions:
        questions = questions[:]
        random.shuffle(questions)

    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        student_id=student.id,
        attempt_number=len(previous) + 1,
        status=AttemptStatus.IN_PROGRESS,
        started_at=_now(),
        expires_at=_now() + timedelta(minutes=assessment.duration_minutes),
        question_order=[str(q.id) for q in questions],
        max_score=round(sum(q.weight * q.difficulty.weight for q in questions), 2),
    )
    db.add(attempt)
    await db.flush()
    log.info(
        "assessments.attempt_started",
        attempt_id=str(attempt.id), assessment=assessment.slug,
        student_id=str(student.id), questions=len(questions),
    )
    return attempt, questions


async def _questions_for(
    db: AsyncSession, assessment: Assessment, order: list[Any]
) -> list[AssessmentQuestion]:
    by_id = {str(q.id): q for q in assessment.questions}
    ordered = [by_id[str(qid)] for qid in (order or []) if str(qid) in by_id]
    return ordered or [q for q in assessment.questions if q.is_active]


# ------------------------------------------------------------ scoring ------
def score_question(
    question: AssessmentQuestion, selected_ids: Iterable[uuid.UUID]
) -> tuple[float, float, bool]:
    """Return ``(awarded, maximum, is_correct)`` for one answer."""
    maximum = round(question.weight * question.difficulty.weight, 4)
    selected = {uuid.UUID(str(s)) for s in selected_ids}
    options = {o.id: o for o in question.options}
    selected &= set(options)  # ignore ids that are not this question's options

    if question.question_type == QuestionType.LIKERT:
        # Self-assessment: the chosen option declares a proficiency 0..4.
        if not selected:
            return 0.0, maximum, False
        values = [
            options[o].proficiency_value or 0 for o in selected if o in options
        ]
        ratio = (max(values) / 4) if values else 0.0
        return round(maximum * ratio, 4), maximum, ratio >= 0.5

    correct = {o.id for o in question.options if o.is_correct}
    if not correct:
        return 0.0, maximum, False

    if question.question_type in (QuestionType.SINGLE_CHOICE, QuestionType.TRUE_FALSE):
        is_correct = len(selected) == 1 and selected == correct
        return (maximum if is_correct else 0.0), maximum, is_correct

    # MULTI_CHOICE: proportional credit, penalised for wrong picks.
    hits = len(selected & correct)
    misses = len(selected - correct)
    ratio = max(0.0, (hits - misses) / len(correct))
    return round(maximum * ratio, 4), maximum, ratio >= 0.999


async def submit_attempt(
    db: AsyncSession,
    attempt: AssessmentAttempt,
    answers: list[dict[str, Any]],
    student: StudentProfile,
) -> AssessmentAttempt:
    """Score a submission, store the breakdown and update the skill profile."""
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise BusinessRuleError(
            "This attempt has already been submitted", code="ATTEMPT_ALREADY_SUBMITTED"
        )

    assessment = await get_assessment_or_404(
        db, attempt.assessment_id, with_questions=True
    )
    questions = {q.id: q for q in assessment.questions}
    expires = _aware(attempt.expires_at)
    late = bool(expires and _now() > expires + timedelta(seconds=60))

    by_skill: dict[uuid.UUID, dict[str, float]] = {}
    total_awarded = total_max = 0.0

    for entry in answers:
        question_id = entry.get("question_id")
        try:
            question = questions[uuid.UUID(str(question_id))]
        except (KeyError, ValueError, TypeError) as exc:
            raise ValidationError(
                "An answer refers to a question that is not in this assessment",
                code="UNKNOWN_QUESTION",
                details={"question_id": str(question_id)},
            ) from exc
        selected = entry.get("selected_option_ids") or []
        awarded, maximum, is_correct = score_question(question, selected)
        if late:
            # A late submission still records answers, but scores zero.
            awarded = 0.0
            is_correct = False

        db.add(
            AssessmentAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option_ids=[str(s) for s in selected],
                free_text=entry.get("free_text"),
                is_correct=is_correct,
                awarded_score=awarded,
                max_score=maximum,
                time_spent_seconds=entry.get("time_spent_seconds"),
            )
        )
        total_awarded += awarded
        total_max += maximum

        bucket = by_skill.setdefault(
            question.skill_id,
            {"score": 0.0, "max": 0.0, "questions": 0, "correct": 0},
        )
        bucket["score"] += awarded
        bucket["max"] += maximum
        bucket["questions"] += 1
        bucket["correct"] += 1 if is_correct else 0

    # Unanswered questions still count against the maximum.
    answered_ids = {uuid.UUID(str(a["question_id"])) for a in answers if a.get("question_id")}
    ordered_ids = [uuid.UUID(str(q)) for q in (attempt.question_order or [])]
    for question_id in ordered_ids:
        if question_id in answered_ids or question_id not in questions:
            continue
        question = questions[question_id]
        maximum = round(question.weight * question.difficulty.weight, 4)
        total_max += maximum
        bucket = by_skill.setdefault(
            question.skill_id,
            {"score": 0.0, "max": 0.0, "questions": 0, "correct": 0},
        )
        bucket["max"] += maximum
        bucket["questions"] += 1

    percentage = round(total_awarded / total_max * 100, 2) if total_max else 0.0
    attempt.raw_score = round(total_awarded, 2)
    attempt.max_score = round(total_max, 2)
    attempt.percentage = percentage
    attempt.is_passed = percentage >= assessment.passing_score
    attempt.status = AttemptStatus.EVALUATED
    attempt.submitted_at = _now()
    started = _aware(attempt.started_at) or _now()
    attempt.duration_seconds = int((_now() - started).total_seconds())
    attempt.confidence = confidence_for(max(1, len(ordered_ids)))
    attempt.feedback = _feedback(percentage, assessment.passing_score, late)

    # ------------------------------------------------- per-skill results --
    for skill_id, bucket in by_skill.items():
        skill_percentage = (
            round(bucket["score"] / bucket["max"] * 100, 2) if bucket["max"] else 0.0
        )
        question_count = int(bucket["questions"])
        confidence = confidence_for(question_count)
        level = ProficiencyLevel.from_score(skill_percentage)
        db.add(
            AttemptSkillScore(
                attempt_id=attempt.id,
                skill_id=skill_id,
                score=round(bucket["score"], 2),
                max_score=round(bucket["max"], 2),
                percentage=skill_percentage,
                questions_count=question_count,
                correct_count=int(bucket["correct"]),
                confidence=confidence,
                level=level,
            )
        )
        if late:
            continue
        # Feed the measured level back into the student's skill profile.
        await skill_service.upsert_student_skill(
            db,
            student.id,
            skill_id,
            level=level,
            source=SkillSource.ASSESSMENT,
            score=skill_percentage,
            confidence=confidence,
            evidence={
                "assessment_id": str(assessment.id),
                "assessment_title": assessment.title,
                "attempt_id": str(attempt.id),
                "percentage": skill_percentage,
                "questions": question_count,
                "measured_at": _now().isoformat(),
            },
            mark_assessed=True,
        )

    await db.flush()
    await skill_service.refresh_student_readiness(db, student)
    log.info(
        "assessments.attempt_scored",
        attempt_id=str(attempt.id), percentage=percentage,
        passed=attempt.is_passed, skills=len(by_skill),
    )
    return attempt


def _feedback(percentage: float, passing: float, late: bool) -> str:
    if late:
        return (
            "This attempt was submitted after the time limit, so it scores zero. "
            "Your skill profile was not changed - you can retake the assessment."
        )
    if percentage >= 90:
        return (
            "Excellent - this is expert-level performance. Use it as evidence in "
            "your applications and portfolio."
        )
    if percentage >= passing:
        return (
            "You passed. Your skill profile has been updated with the measured "
            "levels, which improves your role readiness and recommendations."
        )
    if percentage >= passing * 0.6:
        return (
            "Close. Review the explanations for the questions you missed, spend "
            "time on the weakest skill, then retake the assessment."
        )
    return (
        "This assessment is measuring skills you have not built yet. Work through "
        "the recommended learning path first - that is what it is for."
    )


# ------------------------------------------------------------- reporting ---
async def attempt_report(
    db: AsyncSession, attempt: AssessmentAttempt
) -> dict[str, Any]:
    """Full result view, including per-question explanations."""
    answers = (
        await db.execute(
            select(AssessmentAnswer)
            .where(AssessmentAnswer.attempt_id == attempt.id)
            .options(
                selectinload(AssessmentAnswer.question).selectinload(
                    AssessmentQuestion.options
                ),
                selectinload(AssessmentAnswer.question).selectinload(
                    AssessmentQuestion.skill
                ),
            )
        )
    ).scalars().all()
    skill_scores = (
        await db.execute(
            select(AttemptSkillScore)
            .where(AttemptSkillScore.attempt_id == attempt.id)
            .options(selectinload(AttemptSkillScore.skill))
            .order_by(AttemptSkillScore.percentage.desc())
        )
    ).scalars().all()

    return {
        "attempt_id": attempt.id,
        "assessment_id": attempt.assessment_id,
        "assessment_title": attempt.assessment.title if attempt.assessment else "",
        "status": attempt.status.value,
        "attempt_number": attempt.attempt_number,
        "raw_score": attempt.raw_score,
        "max_score": attempt.max_score,
        "percentage": attempt.percentage,
        "confidence": attempt.confidence,
        "is_passed": attempt.is_passed,
        "duration_seconds": attempt.duration_seconds,
        "submitted_at": attempt.submitted_at,
        "feedback": attempt.feedback,
        "skill_scores": [
            {
                "skill_id": s.skill_id,
                "skill_name": s.skill.name if s.skill else "",
                "score": s.score,
                "max_score": s.max_score,
                "percentage": s.percentage,
                "questions_count": s.questions_count,
                "correct_count": s.correct_count,
                "confidence": s.confidence,
                "level": s.level.value,
            }
            for s in skill_scores
        ],
        "answers": [
            {
                "question_id": a.question_id,
                "prompt": a.question.prompt if a.question else "",
                "skill_name": (
                    a.question.skill.name if a.question and a.question.skill else ""
                ),
                "difficulty": a.question.difficulty.value if a.question else "",
                "is_correct": a.is_correct,
                "awarded_score": a.awarded_score,
                "max_score": a.max_score,
                "selected_option_ids": a.selected_option_ids,
                "correct_option_ids": (
                    [str(o.id) for o in a.question.options if o.is_correct]
                    if a.question
                    else []
                ),
                "explanation": a.question.explanation if a.question else "",
            }
            for a in answers
        ],
    }
