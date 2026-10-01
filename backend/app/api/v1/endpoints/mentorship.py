"""Mentorship: mentor directory, requests and sessions."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import ActiveUser, CurrentStudent, DbSession
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.enums import MentorshipStatus, NotificationCategory, RoleName
from app.models.mentorship import MentorProfile, MentorshipRequest, MentorshipSession
from app.models.profile import StudentProfile
from app.models.skill import Skill
from app.schemas.collaboration import (
    MentorIn,
    MentorOut,
    MentorshipRequestIn,
    MentorshipRequestOut,
    MentorshipRespondIn,
    MentorshipSessionIn,
    MentorshipSessionOut,
    MentorshipSessionUpdate,
)
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.services import notification

router = APIRouter(prefix="/mentorship", tags=["Mentorship"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
}


def _now() -> datetime:
    return datetime.now(UTC)


async def _mentor_out(db, mentor: MentorProfile) -> MentorOut:
    data = MentorOut.model_validate(mentor)
    data.full_name = mentor.user.full_name if mentor.user else ""
    data.avatar_url = mentor.user.avatar_url if mentor.user else None
    ids = [uuid.UUID(str(s)) for s in (mentor.expertise_skill_ids or []) if s]
    if ids:
        names = (
            await db.execute(select(Skill.name).where(Skill.id.in_(ids)))
        ).scalars().all()
        data.expertise_skills = list(names)
    return data


@router.get(
    "/mentors",
    response_model=Page[MentorOut],
    summary="Browse mentors",
    description="Industry professionals and academicians offering mentorship, "
                "filterable by expertise, industry and topic.",
)
async def list_mentors(
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    q: str | None = None,
    industry: str | None = None,
    skill_id: Annotated[list[uuid.UUID] | None, Query()] = None,
    accepting_only: bool = True,
) -> Page[MentorOut]:
    stmt = select(MentorProfile).options(selectinload(MentorProfile.user))
    if accepting_only:
        stmt = stmt.where(MentorProfile.is_accepting_requests.is_(True))
    if industry:
        stmt = stmt.where(func.lower(MentorProfile.industry) == industry.lower())
    if q:
        needle = f"%{q.lower().strip()}%"
        stmt = stmt.where(
            or_(
                func.lower(MentorProfile.headline).like(needle),
                func.lower(MentorProfile.bio).like(needle),
                func.lower(MentorProfile.designation).like(needle),
            )
        )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(MentorProfile.rating.desc(), MentorProfile.experience_years.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()

    if skill_id:
        wanted = {str(s) for s in skill_id}
        rows = [
            r for r in rows if wanted & {str(s) for s in (r.expertise_skill_ids or [])}
        ]
    items = [await _mentor_out(db, r) for r in rows]
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/mentors/{mentor_id}",
    response_model=Envelope[MentorOut],
    responses=ERRORS,
    summary="Mentor profile",
)
async def get_mentor(mentor_id: uuid.UUID, db: DbSession) -> dict:
    mentor = (
        await db.execute(
            select(MentorProfile)
            .where(MentorProfile.id == mentor_id)
            .options(selectinload(MentorProfile.user))
        )
    ).scalar_one_or_none()
    if mentor is None:
        raise NotFoundError("Mentor not found", code="MENTOR_NOT_FOUND")
    return ok(await _mentor_out(db, mentor))


@router.put(
    "/mentors/me",
    response_model=Envelope[MentorOut],
    responses=ERRORS,
    summary="Create or update my mentor profile",
    description="Available to recruiters, company admins and academicians. "
                "Listing expertise skills is what lets students be matched to "
                "the right mentor rather than a random one.",
)
async def upsert_my_mentor_profile(
    payload: MentorIn, db: DbSession, user: ActiveUser
) -> dict:
    allowed = {
        RoleName.INDUSTRY_RECRUITER.value, RoleName.INDUSTRY_ADMIN.value,
        RoleName.ACADEMICIAN.value, RoleName.SUPER_ADMIN.value,
    }
    if not allowed & set(user.role_names):
        raise PermissionDeniedError(
            "Only industry professionals and academicians can offer mentorship",
            code="MENTOR_ROLE_REQUIRED",
        )
    mentor = (
        await db.execute(
            select(MentorProfile)
            .where(MentorProfile.user_id == user.id)
            .options(selectinload(MentorProfile.user))
        )
    ).scalar_one_or_none()
    if mentor is None:
        mentor = MentorProfile(
            user_id=user.id, company_id=user.company_id,
            institution_id=user.institution_id,
        )
        db.add(mentor)
    data = payload.model_dump()
    data["expertise_skill_ids"] = [str(s) for s in data["expertise_skill_ids"]]
    for field, value in data.items():
        setattr(mentor, field, value)
    await db.commit()
    await db.refresh(mentor, ["user"])
    return ok(await _mentor_out(db, mentor))


@router.post(
    "/requests",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[MentorshipRequestOut],
    responses=ERRORS,
    summary="Request mentorship",
)
async def request_mentorship(
    payload: MentorshipRequestIn, student: CurrentStudent, db: DbSession
) -> dict:
    mentor = (
        await db.execute(
            select(MentorProfile)
            .where(MentorProfile.id == payload.mentor_id)
            .options(selectinload(MentorProfile.user))
        )
    ).scalar_one_or_none()
    if mentor is None:
        raise NotFoundError("Mentor not found", code="MENTOR_NOT_FOUND")
    if not mentor.is_accepting_requests:
        raise BusinessRuleError(
            "This mentor is not accepting requests right now",
            code="MENTOR_NOT_ACCEPTING",
        )

    open_request = (
        await db.execute(
            select(MentorshipRequest).where(
                MentorshipRequest.mentor_id == mentor.id,
                MentorshipRequest.student_id == student.id,
                MentorshipRequest.status.in_(
                    [
                        MentorshipStatus.REQUESTED, MentorshipStatus.ACCEPTED,
                        MentorshipStatus.SCHEDULED,
                    ]
                ),
            )
        )
    ).scalar_one_or_none()
    if open_request is not None:
        raise ConflictError(
            "You already have an open request with this mentor",
            code="MENTORSHIP_REQUEST_OPEN",
        )

    # Monthly capacity is the mentor's stated limit, and it is respected.
    from datetime import timedelta

    month_ago = _now() - timedelta(days=30)
    accepted_recently = (
        await db.execute(
            select(func.count())
            .select_from(MentorshipRequest)
            .where(
                MentorshipRequest.mentor_id == mentor.id,
                MentorshipRequest.status.in_(
                    [MentorshipStatus.ACCEPTED, MentorshipStatus.SCHEDULED]
                ),
                MentorshipRequest.created_at >= month_ago,
            )
        )
    ).scalar_one()
    if mentor.capacity_per_month and accepted_recently >= mentor.capacity_per_month:
        raise BusinessRuleError(
            "This mentor has reached their capacity for the month",
            code="MENTOR_AT_CAPACITY",
        )

    request_row = MentorshipRequest(
        mentor_id=mentor.id,
        student_id=student.id,
        topic=payload.topic,
        message=payload.message,
        goals=payload.goals,
        preferred_slots=payload.preferred_slots,
        status=MentorshipStatus.REQUESTED,
    )
    db.add(request_row)
    await db.flush()

    await notification.notify(
        db, mentor.user_id,
        category=NotificationCategory.MENTORSHIP,
        title="New mentorship request",
        body=f"{student.user.full_name if student.user else 'A student'} asked about "
             f"{payload.topic}",
        action_url="/mentorship/requests",
        action_label="Review request",
        icon="users",
        resource_type="mentorship_request",
        resource_id=request_row.id,
        email_template="mentorship_request",
        email_context={
            "student_name": student.user.full_name if student.user else "A student",
            "topic": payload.topic,
        },
    )
    await db.commit()
    return ok(await _request_out(db, request_row))


async def _request_out(db, row: MentorshipRequest) -> MentorshipRequestOut:
    reloaded = (
        await db.execute(
            select(MentorshipRequest)
            .where(MentorshipRequest.id == row.id)
            .options(
                selectinload(MentorshipRequest.mentor).selectinload(MentorProfile.user),
                selectinload(MentorshipRequest.sessions),
            )
        )
    ).scalar_one()
    data = MentorshipRequestOut.model_validate(reloaded)
    if reloaded.mentor:
        data.mentor = await _mentor_out(db, reloaded.mentor)
    student = await db.get(StudentProfile, reloaded.student_id)
    if student is not None:
        await db.refresh(student, ["user"])
        data.student_name = student.user.full_name if student.user else ""
    return data


@router.get(
    "/requests",
    response_model=Page[MentorshipRequestOut],
    responses=ERRORS,
    summary="My mentorship requests",
    description="Students see requests they sent; mentors see requests they "
                "received.",
)
async def list_requests(
    db: DbSession,
    user: ActiveUser,
    page: Annotated[PaginationParams, Depends(pagination)],
    status_filter: Annotated[MentorshipStatus | None, Query(alias="status")] = None,
) -> Page[MentorshipRequestOut]:
    mentor = (
        await db.execute(select(MentorProfile).where(MentorProfile.user_id == user.id))
    ).scalar_one_or_none()
    student = (
        await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user.id)
        )
    ).scalar_one_or_none()

    stmt = select(MentorshipRequest)
    if mentor is not None and student is None:
        stmt = stmt.where(MentorshipRequest.mentor_id == mentor.id)
    elif student is not None:
        stmt = stmt.where(MentorshipRequest.student_id == student.id)
    else:
        return Page.build([], 0, page.page, page.page_size)

    if status_filter:
        stmt = stmt.where(MentorshipRequest.status == status_filter)
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(MentorshipRequest.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()
    items = [await _request_out(db, r) for r in rows]
    return Page.build(items, total, page.page, page.page_size)


@router.post(
    "/requests/{request_id}/respond",
    response_model=Envelope[MentorshipRequestOut],
    responses=ERRORS,
    summary="Accept or decline a request",
)
async def respond_to_request(
    request_id: uuid.UUID,
    payload: MentorshipRespondIn,
    db: DbSession,
    user: ActiveUser,
) -> dict:
    row = (
        await db.execute(
            select(MentorshipRequest)
            .where(MentorshipRequest.id == request_id)
            .options(selectinload(MentorshipRequest.mentor))
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Request not found", code="MENTORSHIP_REQUEST_NOT_FOUND")
    if row.mentor is None or row.mentor.user_id != user.id:
        raise PermissionDeniedError(
            "This request was sent to another mentor", code="NOT_THE_MENTOR"
        )
    if row.status != MentorshipStatus.REQUESTED:
        raise BusinessRuleError(
            f"This request is already {row.status.value.lower()}",
            code="REQUEST_ALREADY_ANSWERED",
        )

    row.status = (
        MentorshipStatus.ACCEPTED
        if payload.decision == "ACCEPTED"
        else MentorshipStatus.DECLINED
    )
    row.response_message = payload.response_message
    row.responded_at = _now()

    student = await db.get(StudentProfile, row.student_id)
    if student is not None:
        await notification.notify(
            db, student.user_id,
            category=NotificationCategory.MENTORSHIP,
            title=f"Mentorship request {row.status.value.lower()}",
            body=payload.response_message or row.topic,
            action_url="/student/mentorship",
            action_label="View",
            icon="users",
            resource_type="mentorship_request",
            resource_id=row.id,
        )
    await db.commit()
    return ok(await _request_out(db, row))


@router.post(
    "/requests/{request_id}/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[MentorshipSessionOut],
    responses=ERRORS,
    summary="Schedule a session",
)
async def schedule_session(
    request_id: uuid.UUID,
    payload: MentorshipSessionIn,
    db: DbSession,
    user: ActiveUser,
) -> dict:
    row = (
        await db.execute(
            select(MentorshipRequest)
            .where(MentorshipRequest.id == request_id)
            .options(selectinload(MentorshipRequest.mentor))
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Request not found", code="MENTORSHIP_REQUEST_NOT_FOUND")
    if row.mentor is None or row.mentor.user_id != user.id:
        raise PermissionDeniedError("Only the mentor can schedule", code="NOT_THE_MENTOR")
    if row.status not in (MentorshipStatus.ACCEPTED, MentorshipStatus.SCHEDULED):
        raise BusinessRuleError(
            "Accept the request before scheduling a session",
            code="REQUEST_NOT_ACCEPTED",
        )
    if payload.scheduled_at <= _now():
        from app.core.exceptions import ValidationError

        raise ValidationError("Sessions must be scheduled in the future",
                              code="SESSION_IN_PAST")

    session = MentorshipSession(
        request_id=row.id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        meeting_link=payload.meeting_link,
        agenda=payload.agenda,
    )
    db.add(session)
    row.status = MentorshipStatus.SCHEDULED

    student = await db.get(StudentProfile, row.student_id)
    if student is not None:
        await notification.notify(
            db, student.user_id,
            category=NotificationCategory.MENTORSHIP,
            title="Mentorship session scheduled",
            body=f"{row.topic} on {payload.scheduled_at:%d %b %Y at %H:%M} UTC",
            action_url="/student/mentorship",
            action_label="View session",
            icon="calendar",
            resource_type="mentorship_session",
        )
    await db.commit()
    return ok(MentorshipSessionOut.model_validate(session))


@router.patch(
    "/sessions/{session_id}",
    response_model=Envelope[MentorshipSessionOut],
    responses=ERRORS,
    summary="Update a session",
    description="Mentors record notes and outcomes; students add their own "
                "notes and rate the session. Each side may only write its own fields.",
)
async def update_session(
    session_id: uuid.UUID,
    payload: MentorshipSessionUpdate,
    db: DbSession,
    user: ActiveUser,
) -> dict:
    session = (
        await db.execute(
            select(MentorshipSession)
            .where(MentorshipSession.id == session_id)
            .options(
                selectinload(MentorshipSession.request).selectinload(
                    MentorshipRequest.mentor
                )
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise NotFoundError("Session not found", code="SESSION_NOT_FOUND")

    request_row = session.request
    student = await db.get(StudentProfile, request_row.student_id)
    is_mentor = bool(request_row.mentor and request_row.mentor.user_id == user.id)
    is_student = bool(student and student.user_id == user.id)
    if not (is_mentor or is_student):
        raise PermissionDeniedError("Not your session", code="SESSION_ACCESS_DENIED")

    changes = payload.model_dump(exclude_unset=True)
    mentor_fields = {"status", "mentor_notes", "action_items"}
    student_fields = {"student_notes", "student_rating", "student_feedback"}
    for field, value in changes.items():
        if field in mentor_fields and not is_mentor:
            continue
        if field in student_fields and not is_student:
            continue
        setattr(session, field, value)

    if changes.get("status") == "COMPLETED" and is_mentor:
        session.completed_at = _now()
        request_row.status = MentorshipStatus.COMPLETED
        if request_row.mentor:
            request_row.mentor.sessions_completed += 1

    if changes.get("student_rating") and is_student and request_row.mentor:
        mentor = request_row.mentor
        completed = max(1, mentor.sessions_completed)
        mentor.rating = round(
            (mentor.rating * (completed - 1) + changes["student_rating"]) / completed, 2
        )

    if student is not None:
        from app.services import student as student_service

        await student_service.evaluate_badges(db, student)
    await db.commit()
    return ok(MentorshipSessionOut.model_validate(session))
