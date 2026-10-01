"""Applications: submission, the status state machine and interviews."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.logging import get_logger
from app.models.application import Application, ApplicationStatusHistory, Interview
from app.models.document import Document
from app.models.enums import (
    APPLICATION_TRANSITIONS,
    ApplicationStatus,
    NotificationCategory,
    OpportunityStatus,
    OpportunityType,
)
from app.models.opportunity import Opportunity
from app.models.profile import AcademicianProfile, ExperienceRecord, StudentProfile
from app.models.user import User
from app.services import notification
from app.services import opportunity as opportunity_service

log = get_logger("applications")

# Statuses whose email is worth sending, and which template to use.
STATUS_EMAIL: dict[ApplicationStatus, str] = {
    ApplicationStatus.SHORTLISTED: "application_update",
    ApplicationStatus.INTERVIEW: "application_update",
    ApplicationStatus.OFFERED: "application_update",
    ApplicationStatus.SELECTED: "selection",
    ApplicationStatus.REJECTED: "rejection",
}

STATUS_MESSAGE: dict[ApplicationStatus, str] = {
    ApplicationStatus.UNDER_REVIEW: "Your application is being reviewed",
    ApplicationStatus.SHORTLISTED: "You have been shortlisted",
    ApplicationStatus.INTERVIEW: "You have an interview",
    ApplicationStatus.OFFERED: "You have received an offer",
    ApplicationStatus.SELECTED: "You have been selected",
    ApplicationStatus.REJECTED: "Your application was not successful this time",
    ApplicationStatus.WITHDRAWN: "You withdrew your application",
}


def _now() -> datetime:
    return datetime.now(UTC)


async def get_application_or_404(
    db: AsyncSession, application_id: uuid.UUID
) -> Application:
    row = (
        await db.execute(
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.opportunity).selectinload(Opportunity.company),
                selectinload(Application.student).selectinload(StudentProfile.user),
                selectinload(Application.history),
                selectinload(Application.interviews),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Application not found", code="APPLICATION_NOT_FOUND")
    return row


# ---------------------------------------------------------------- submit ---
async def apply_to_opportunity(
    db: AsyncSession,
    *,
    opportunity: Opportunity,
    student: StudentProfile,
    cover_letter: str = "",
    resume_document_id: uuid.UUID | None = None,
    answers: dict[str, Any] | None = None,
) -> Application:
    """Submit an application, capturing the match explanation as evidence."""
    if opportunity.opportunity_type == OpportunityType.FACULTY_OPPORTUNITY:
        raise BusinessRuleError(
            "This programme is for academicians", code="WRONG_APPLICANT_TYPE"
        )
    if opportunity.status != OpportunityStatus.PUBLISHED:
        raise BusinessRuleError(
            "This opportunity is not accepting applications",
            code="OPPORTUNITY_NOT_OPEN",
        )
    if not opportunity.is_open:
        raise BusinessRuleError(
            "The application deadline has passed", code="DEADLINE_PASSED"
        )

    existing = (
        await db.execute(
            select(Application).where(
                Application.opportunity_id == opportunity.id,
                Application.student_id == student.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.status == ApplicationStatus.WITHDRAWN:
            raise ConflictError(
                "You withdrew from this opportunity and cannot reapply",
                code="ALREADY_WITHDRAWN",
            )
        raise ConflictError(
            "You have already applied to this opportunity", code="ALREADY_APPLIED"
        )

    if resume_document_id is not None:
        document = await db.get(Document, resume_document_id)
        if document is None or document.deleted_at is not None:
            raise NotFoundError("Resume document not found", code="DOCUMENT_NOT_FOUND")
        if document.owner_id != student.user_id:
            raise PermissionDeniedError(
                "That document belongs to another user", code="DOCUMENT_NOT_OWNED"
            )

    result = await opportunity_service.match_student_to_opportunity(
        db, student, opportunity
    )
    # Hard eligibility is the employer's stated rule, so it is enforced.
    if not result.is_eligible:
        raise BusinessRuleError(
            "You do not meet the eligibility criteria for this opportunity",
            code="NOT_ELIGIBLE",
            details={"reasons": result.ineligibility_reasons},
        )

    application = Application(
        opportunity_id=opportunity.id,
        student_id=student.id,
        status=ApplicationStatus.APPLIED,
        cover_letter=cover_letter,
        resume_document_id=resume_document_id,
        answers=answers or {},
        match_score=result.match_score,
        match_breakdown=result.breakdown,
        matching_skills=result.matching_skills,
        missing_skills=result.missing_skills,
        submitted_at=_now(),
        last_status_change_at=_now(),
    )
    db.add(application)
    await db.flush()

    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status=None,
            to_status=ApplicationStatus.APPLIED,
            changed_by_id=student.user_id,
            note="Application submitted",
        )
    )
    opportunity.applications_count = (opportunity.applications_count or 0) + 1

    if opportunity.posted_by_id:
        await notification.notify(
            db, opportunity.posted_by_id,
            category=NotificationCategory.APPLICATION,
            title=f"New application for {opportunity.title}",
            body=(
                f"{student.user.full_name if student.user else 'A student'} applied "
                f"with a {result.match_score:.0f}% skill match."
            ),
            action_url=f"/industry/applicants?opportunity={opportunity.id}",
            action_label="Review applicant",
            icon="user-plus",
            resource_type="application",
            resource_id=application.id,
        )

    await db.flush()
    log.info(
        "applications.submitted",
        application_id=str(application.id), match_score=result.match_score,
        opportunity=str(opportunity.id),
    )
    return application


async def apply_to_faculty_opportunity(
    db: AsyncSession,
    *,
    opportunity: Opportunity,
    academician: AcademicianProfile,
    cover_letter: str = "",
) -> Application:
    if opportunity.opportunity_type != OpportunityType.FACULTY_OPPORTUNITY:
        raise BusinessRuleError(
            "This opportunity is for students", code="WRONG_APPLICANT_TYPE"
        )
    if opportunity.status != OpportunityStatus.PUBLISHED or not opportunity.is_open:
        raise BusinessRuleError(
            "This programme is not accepting applications", code="OPPORTUNITY_NOT_OPEN"
        )
    minimum = getattr(opportunity, "min_teaching_experience_years", 0) or 0
    if academician.teaching_experience_years < minimum:
        raise BusinessRuleError(
            f"This programme requires at least {minimum} year(s) of teaching experience",
            code="NOT_ELIGIBLE",
        )

    existing = (
        await db.execute(
            select(Application).where(
                Application.opportunity_id == opportunity.id,
                Application.academician_id == academician.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("You have already applied", code="ALREADY_APPLIED")

    application = Application(
        opportunity_id=opportunity.id,
        # Faculty applications are keyed on academician_id; student_id is unused.
        student_id=None,
        academician_id=academician.id,
        status=ApplicationStatus.APPLIED,
        cover_letter=cover_letter,
        submitted_at=_now(),
        last_status_change_at=_now(),
    )
    db.add(application)
    await db.flush()
    db.add(
        ApplicationStatusHistory(
            application_id=application.id, to_status=ApplicationStatus.APPLIED,
            changed_by_id=academician.user_id, note="Application submitted",
        )
    )
    opportunity.applications_count = (opportunity.applications_count or 0) + 1
    await db.flush()
    return application


# --------------------------------------------------------- state machine ---
async def change_status(
    db: AsyncSession,
    application: Application,
    new_status: ApplicationStatus,
    *,
    actor: User,
    note: str = "",
    reason: str | None = None,
) -> Application:
    """Move an application through the pipeline, enforcing legal transitions."""
    current = application.status
    if new_status == current:
        raise BusinessRuleError(
            f"The application is already {current.value}", code="STATUS_UNCHANGED"
        )
    allowed = APPLICATION_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise BusinessRuleError(
            f"Cannot move an application from {current.value} to {new_status.value}",
            code="INVALID_STATUS_TRANSITION",
            details={
                "current_status": current.value,
                "allowed_next": sorted(s.value for s in allowed),
            },
        )

    application.status = new_status
    application.last_status_change_at = _now()
    if new_status == ApplicationStatus.REJECTED:
        application.rejection_reason = reason or note or None
    if new_status == ApplicationStatus.WITHDRAWN:
        application.withdrawn_reason = reason or note or None
    if new_status in (
        ApplicationStatus.SELECTED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN
    ):
        application.decided_at = _now()

    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status=current,
            to_status=new_status,
            changed_by_id=actor.id,
            note=note,
        )
    )

    # Selection creates verified experience - this is the "verified experience"
    # step of the product's core loop.
    if new_status == ApplicationStatus.SELECTED and application.student_id:
        await _record_verified_experience(db, application)

    if application.student_id and new_status != ApplicationStatus.WITHDRAWN:
        await _notify_student(db, application, new_status, note)

    await db.flush()
    log.info(
        "applications.status_changed",
        application_id=str(application.id), from_status=current.value,
        to_status=new_status.value, actor=str(actor.id),
    )
    return application


async def _record_verified_experience(
    db: AsyncSession, application: Application
) -> None:
    opportunity = application.opportunity or await db.get(
        Opportunity, application.opportunity_id
    )
    if opportunity is None:
        return
    existing = (
        await db.execute(
            select(ExperienceRecord).where(
                ExperienceRecord.source_application_id == application.id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return

    skills = await opportunity_service.skill_service.load_opportunity_requirements(
        db, opportunity.id
    )
    kind = (
        "INTERNSHIP"
        if opportunity.opportunity_type == OpportunityType.INTERNSHIP
        else "JOB"
    )
    db.add(
        ExperienceRecord(
            student_id=application.student_id,
            kind=kind,
            title=opportunity.title,
            organization=opportunity.company.name if opportunity.company else "",
            location=opportunity.location_city,
            work_mode=opportunity.work_mode,
            description=(
                f"Selected through SkillBridge for {opportunity.title}."
            ),
            start_date=opportunity.starts_on,
            skill_tags=[r.skill_name for r in skills],
            source_application_id=application.id,
            is_verified=True,
            verified_by_company_id=opportunity.company_id,
        )
    )
    student = application.student or await db.get(StudentProfile, application.student_id)
    if student and opportunity.opportunity_type == OpportunityType.JOB:
        student.is_placed = True
        student.placed_company_id = opportunity.company_id
    await db.flush()


async def _notify_student(
    db: AsyncSession, application: Application, status: ApplicationStatus, note: str
) -> None:
    student = application.student or await db.get(StudentProfile, application.student_id)
    if student is None:
        return
    opportunity = application.opportunity or await db.get(
        Opportunity, application.opportunity_id
    )
    company_name = (
        opportunity.company.name if opportunity and opportunity.company else ""
    )
    title = opportunity.title if opportunity else "your application"
    template = STATUS_EMAIL.get(status)
    await notification.notify(
        db,
        student.user_id,
        category=NotificationCategory.APPLICATION,
        title=STATUS_MESSAGE.get(status, "Your application was updated"),
        body=f"{title}" + (f" at {company_name}" if company_name else ""),
        action_url="/student/applications",
        action_label="Track application",
        icon="briefcase",
        resource_type="application",
        resource_id=application.id,
        email_template=template,
        email_context={
            "opportunity_title": title,
            "company_name": company_name,
            "status": status.value.replace("_", " ").title(),
            "note": note,
        },
    )


async def withdraw(
    db: AsyncSession, application: Application, student: StudentProfile, reason: str = ""
) -> Application:
    if application.student_id != student.id:
        raise PermissionDeniedError(
            "This application belongs to another student", code="APPLICATION_NOT_OWNED"
        )
    return await change_status(
        db, application, ApplicationStatus.WITHDRAWN,
        actor=student.user, note=reason or "Withdrawn by applicant", reason=reason,
    )


# ------------------------------------------------------------ interviews ---
async def schedule_interview(
    db: AsyncSession,
    application: Application,
    *,
    actor: User,
    scheduled_at: datetime,
    round_name: str,
    duration_minutes: int,
    mode: str,
    location_or_link: str | None,
    interviewer_name: str | None,
    instructions: str,
) -> Interview:
    if application.status in (
        ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN, ApplicationStatus.SELECTED
    ):
        raise BusinessRuleError(
            f"Cannot schedule an interview for a {application.status.value.lower()} "
            "application",
            code="APPLICATION_CLOSED",
        )
    if scheduled_at <= _now():
        raise ValidationError(
            "Interview time must be in the future", code="INTERVIEW_IN_PAST"
        )

    rounds = (
        await db.execute(
            select(func.count())
            .select_from(Interview)
            .where(Interview.application_id == application.id)
        )
    ).scalar_one()

    interview = Interview(
        application_id=application.id,
        round_number=rounds + 1,
        round_name=round_name,
        mode=mode,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        location_or_link=location_or_link,
        interviewer_user_id=actor.id,
        interviewer_name=interviewer_name or actor.full_name,
        instructions=instructions,
    )
    db.add(interview)

    if application.status in (
        ApplicationStatus.APPLIED, ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.SHORTLISTED,
    ):
        # Scheduling implies shortlisting; move through the pipeline correctly.
        if application.status != ApplicationStatus.SHORTLISTED:
            await change_status(
                db, application, ApplicationStatus.SHORTLISTED, actor=actor,
                note="Shortlisted for interview",
            )
        await change_status(
            db, application, ApplicationStatus.INTERVIEW, actor=actor,
            note=f"{round_name} scheduled",
        )

    student = application.student or await db.get(StudentProfile, application.student_id)
    opportunity = application.opportunity or await db.get(
        Opportunity, application.opportunity_id
    )
    if student and opportunity:
        await notification.notify(
            db, student.user_id,
            category=NotificationCategory.APPLICATION,
            title=f"Interview scheduled: {opportunity.title}",
            body=f"{round_name} on {scheduled_at:%d %b %Y at %H:%M} UTC",
            action_url="/student/applications",
            action_label="View details",
            icon="calendar",
            resource_type="interview",
            resource_id=interview.id,
            email_template="interview_invitation",
            email_context={
                "opportunity_title": opportunity.title,
                "company_name": opportunity.company.name if opportunity.company else "",
                "round_name": round_name,
                "scheduled_at": f"{scheduled_at:%d %b %Y at %H:%M} UTC",
                "duration": duration_minutes,
                "location": location_or_link,
                "instructions": instructions,
            },
        )
    await db.flush()
    return interview


# ------------------------------------------------------------- timeline ----
def build_timeline(application: Application) -> list[dict[str, Any]]:
    """Visual pipeline for the student's application tracker."""
    from app.models.enums import APPLICATION_PIPELINE

    history = sorted(application.history, key=lambda h: h.created_at)
    reached: dict[str, datetime] = {}
    for entry in history:
        reached.setdefault(entry.to_status.value, entry.created_at)

    terminal = application.status in (
        ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN
    )
    current_index = -1
    for index, stage in enumerate(APPLICATION_PIPELINE):
        if stage.value in reached:
            current_index = index

    steps: list[dict[str, Any]] = []
    for index, stage in enumerate(APPLICATION_PIPELINE):
        if index <= current_index:
            state = "complete" if index < current_index else "current"
        else:
            state = "upcoming"
        steps.append(
            {
                "status": stage.value,
                "label": stage.value.replace("_", " ").title(),
                "state": state,
                "reached_at": reached.get(stage.value),
            }
        )
    if terminal:
        for step in steps:
            if step["state"] == "current":
                step["state"] = "stopped"
        steps.append(
            {
                "status": application.status.value,
                "label": application.status.value.title(),
                "state": "terminal",
                "reached_at": reached.get(application.status.value),
            }
        )
    return steps
