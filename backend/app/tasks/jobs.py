"""Background jobs: recommendations, reminders, analytics and housekeeping."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app, run_async

log = get_logger("tasks")


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------- emails ---
@celery_app.task(name="skillbridge.send_email", bind=True, max_retries=3)
def send_email_task(self, to: str, template: str, **context: Any) -> bool:
    """Deliver one email out of band so the request path never blocks on SMTP."""
    from app.services.email import send_email

    async def _run() -> bool:
        async with AsyncSessionLocal() as db:
            sent = await send_email(to, template, db=db, **context)
            await db.commit()
            return sent

    try:
        return run_async(_run())
    except Exception as exc:  # pragma: no cover - network dependent
        log.error("tasks.email_failed", to=to, template=template, error=str(exc)[:200])
        raise self.retry(exc=exc, countdown=60) from exc


# ------------------------------------------------------- recommendations ---
@celery_app.task(name="skillbridge.recompute_recommendations")
def recompute_recommendations(student_id: str | None = None) -> dict[str, int]:
    """Refresh stored recommendations for one student, or for everyone active."""
    from app.ai import recommender
    from app.models.enums import OpportunityType
    from app.models.profile import StudentProfile

    async def _run() -> dict[str, int]:
        processed = failed = 0
        async with AsyncSessionLocal() as db:
            stmt = select(StudentProfile).where(StudentProfile.deleted_at.is_(None))
            if student_id:
                stmt = stmt.where(StudentProfile.id == uuid.UUID(student_id))
            else:
                # Only students with a usable profile - recommending to an empty
                # profile produces noise, not value.
                stmt = stmt.where(
                    StudentProfile.is_open_to_work.is_(True),
                    StudentProfile.profile_completion >= 20,
                )
            students = (await db.execute(stmt.limit(2000))).scalars().all()

            for student in students:
                try:
                    for kind in (
                        OpportunityType.INTERNSHIP,
                        OpportunityType.JOB,
                        OpportunityType.LIVE_PROJECT,
                    ):
                        await recommender.recommend_opportunities(
                            db, student, opportunity_type=kind, limit=10
                        )
                    await recommender.recommend_career_roles(db, student)
                    await recommender.recommend_learning(db, student)
                    await recommender.recommend_mentors(db, student)
                    await db.commit()
                    processed += 1
                except Exception as exc:
                    await db.rollback()
                    failed += 1
                    log.error(
                        "tasks.recommendation_failed",
                        student_id=str(student.id), error=str(exc)[:200],
                    )
        log.info("tasks.recommendations_done", processed=processed, failed=failed)
        return {"processed": processed, "failed": failed}

    return run_async(_run())


@celery_app.task(name="skillbridge.refresh_skill_demand")
def refresh_skill_demand() -> dict[str, int]:
    """Recompute every skill's demand score from live postings."""
    from app.services import skill as skill_service

    async def _run() -> dict[str, int]:
        async with AsyncSessionLocal() as db:
            updated = await skill_service.refresh_skill_demand(db)
            await db.commit()
            return {"skills_updated": updated}

    return run_async(_run())


@celery_app.task(name="skillbridge.recompute_readiness")
def recompute_readiness(student_id: str) -> dict[str, Any]:
    """Recompute a student's readiness after their skill profile changed."""
    from app.models.profile import StudentProfile
    from app.services import skill as skill_service

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            student = await db.get(StudentProfile, uuid.UUID(student_id))
            if student is None:
                return {"error": "student_not_found"}
            score = await skill_service.refresh_student_readiness(db, student)
            await db.commit()
            return {"student_id": student_id, "readiness_score": score}

    return run_async(_run())


# ------------------------------------------------------------- reminders ---
@celery_app.task(name="skillbridge.send_deadline_reminders")
def send_deadline_reminders(days_ahead: int = 3) -> dict[str, int]:
    """Nudge students about saved opportunities closing soon."""
    from app.models.application import Application
    from app.models.enums import NotificationCategory, OpportunityStatus
    from app.models.opportunity import Opportunity, SavedOpportunity
    from app.services import notification

    async def _run() -> dict[str, int]:
        sent = 0
        horizon = _now() + timedelta(days=days_ahead)
        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(
                    select(SavedOpportunity, Opportunity)
                    .join(Opportunity, Opportunity.id == SavedOpportunity.opportunity_id)
                    .where(
                        Opportunity.status == OpportunityStatus.PUBLISHED,
                        Opportunity.deleted_at.is_(None),
                        Opportunity.application_deadline.isnot(None),
                        Opportunity.application_deadline <= horizon,
                        Opportunity.application_deadline >= _now(),
                    )
                )
            ).all()
            for saved, opportunity in rows:
                # Skip anyone who already applied.
                from app.models.profile import StudentProfile

                student = (
                    await db.execute(
                        select(StudentProfile).where(
                            StudentProfile.user_id == saved.user_id
                        )
                    )
                ).scalar_one_or_none()
                if student is not None:
                    applied = (
                        await db.execute(
                            select(func.count())
                            .select_from(Application)
                            .where(
                                Application.student_id == student.id,
                                Application.opportunity_id == opportunity.id,
                            )
                        )
                    ).scalar_one()
                    if applied:
                        continue
                await notification.notify(
                    db, saved.user_id,
                    category=NotificationCategory.OPPORTUNITY,
                    title=f"Closing soon: {opportunity.title}",
                    body=f"Applications close {opportunity.application_deadline:%d %b %Y}.",
                    action_url=f"/opportunities/{opportunity.id}",
                    action_label="Apply now",
                    icon="clock",
                    resource_type="opportunity",
                    resource_id=opportunity.id,
                )
                sent += 1
            await db.commit()
        log.info("tasks.deadline_reminders_sent", count=sent)
        return {"reminders_sent": sent}

    return run_async(_run())


@celery_app.task(name="skillbridge.send_event_reminders")
def send_event_reminders(hours_ahead: int = 24) -> dict[str, int]:
    from app.models.enums import NotificationCategory, RegistrationStatus
    from app.models.event import Event, EventRegistration
    from app.services import notification

    async def _run() -> dict[str, int]:
        sent = 0
        horizon = _now() + timedelta(hours=hours_ahead)
        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(
                    select(EventRegistration, Event)
                    .join(Event, Event.id == EventRegistration.event_id)
                    .where(
                        EventRegistration.status == RegistrationStatus.REGISTERED,
                        Event.starts_at <= horizon,
                        Event.starts_at >= _now(),
                        Event.deleted_at.is_(None),
                    )
                )
            ).all()
            for registration, event in rows:
                await notification.notify(
                    db, registration.user_id,
                    category=NotificationCategory.EVENT,
                    title=f"Tomorrow: {event.title}",
                    body=f"Starts {event.starts_at:%d %b %Y at %H:%M} UTC",
                    action_url=f"/events/{event.id}",
                    icon="calendar",
                    resource_type="event",
                    resource_id=event.id,
                    email_template="event_reminder",
                    email_context={
                        "event_title": event.title,
                        "starts_at": f"{event.starts_at:%d %b %Y at %H:%M} UTC",
                        "link": event.meeting_link,
                    },
                )
                sent += 1
            await db.commit()
        return {"reminders_sent": sent}

    return run_async(_run())


# ----------------------------------------------------------- housekeeping --
@celery_app.task(name="skillbridge.expire_stale_attempts")
def expire_stale_attempts() -> dict[str, int]:
    """Close assessment attempts whose time limit has passed."""
    from app.models.assessment import AssessmentAttempt
    from app.models.enums import AttemptStatus

    async def _run() -> dict[str, int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                update(AssessmentAttempt)
                .where(
                    AssessmentAttempt.status == AttemptStatus.IN_PROGRESS,
                    AssessmentAttempt.expires_at.isnot(None),
                    AssessmentAttempt.expires_at < _now(),
                )
                .values(status=AttemptStatus.EXPIRED)
            )
            await db.commit()
            return {"expired": result.rowcount or 0}

    return run_async(_run())


@celery_app.task(name="skillbridge.prune_expired_sessions")
def prune_expired_sessions() -> dict[str, int]:
    """Revoke refresh sessions whose lifetime has elapsed."""
    from app.models.user import UserSession

    async def _run() -> dict[str, int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                update(UserSession)
                .where(
                    UserSession.revoked_at.is_(None), UserSession.expires_at < _now()
                )
                .values(revoked_at=_now(), revoked_reason="expired")
            )
            await db.commit()
            return {"revoked": result.rowcount or 0}

    return run_async(_run())


@celery_app.task(name="skillbridge.process_resume")
def process_resume(document_id: str, student_id: str, job_role_id: str | None = None) -> dict:
    """Extract and analyse an uploaded resume off the request path."""
    from app.models.document import Document
    from app.models.profile import StudentProfile
    from app.models.skill import JobRole
    from app.services import document as document_service

    async def _run() -> dict:
        async with AsyncSessionLocal() as db:
            document = await db.get(Document, uuid.UUID(document_id))
            student = await db.get(StudentProfile, uuid.UUID(student_id))
            if document is None or student is None:
                return {"error": "not_found"}
            role = (
                await db.get(JobRole, uuid.UUID(job_role_id)) if job_role_id else None
            )
            analysis = await document_service.analyse_resume(
                db, document=document, student=student, job_role=role
            )
            await db.commit()
            return {"analysis_id": str(analysis.id), "ats_score": analysis.ats_score}

    return run_async(_run())


@celery_app.task(name="skillbridge.aggregate_analytics")
def aggregate_analytics() -> dict[str, int]:
    """Warm the analytics cache for every institution and company."""
    from app.core.cache import cache_key, cache_set
    from app.models.organization import Company, Institution
    from app.services import analytics as analytics_service

    async def _run() -> dict[str, int]:
        warmed = 0
        async with AsyncSessionLocal() as db:
            institutions = (
                await db.execute(
                    select(Institution.id).where(Institution.deleted_at.is_(None))
                )
            ).scalars().all()
            for institution_id in institutions:
                data = await analytics_service.institution_analytics(db, institution_id)
                await cache_set(cache_key("analytics", "institution", institution_id), data, 3600)
                warmed += 1
            companies = (
                await db.execute(
                    select(Company.id).where(Company.deleted_at.is_(None))
                )
            ).scalars().all()
            for company_id in companies:
                data = await analytics_service.industry_analytics(db, company_id)
                await cache_set(cache_key("analytics", "industry", company_id), data, 3600)
                warmed += 1
        return {"cached": warmed}

    return run_async(_run())
