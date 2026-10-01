"""Workshops, webinars, hackathons and other events."""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import ActiveUser, DbSession, OptionalUser, require_permission
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.enums import EventType, NotificationCategory, RegistrationStatus, RoleName
from app.models.event import Event, EventRegistration
from app.schemas.collaboration import (
    AttendanceIn,
    EventFeedbackIn,
    EventIn,
    EventOut,
    EventRegistrationOut,
)
from app.schemas.common import (
    Envelope,
    ErrorResponse,
    MessageResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.services import notification
from app.services.auth import unique_slug

router = APIRouter(prefix="/events", tags=["Events"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
}


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


@router.get(
    "",
    response_model=Page[EventOut],
    summary="Browse events",
    description="Workshops, guest lectures, hackathons, webinars, industry "
                "visits and career sessions.",
)
async def list_events(
    db: DbSession,
    page: Annotated[PaginationParams, Depends(pagination)],
    user: OptionalUser = None,
    q: str | None = None,
    event_type: EventType | None = None,
    upcoming_only: bool = True,
    company_id: uuid.UUID | None = None,
    institution_id: uuid.UUID | None = None,
) -> Page[EventOut]:
    stmt = (
        select(Event)
        .where(Event.is_published.is_(True), Event.deleted_at.is_(None))
        .options(selectinload(Event.registrations))
    )
    if q:
        needle = f"%{q.lower().strip()}%"
        stmt = stmt.where(
            or_(func.lower(Event.title).like(needle), Event.search_text.like(needle))
        )
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if upcoming_only:
        stmt = stmt.where(Event.starts_at >= _now())
    if company_id:
        stmt = stmt.where(Event.host_company_id == company_id)
    if institution_id:
        stmt = stmt.where(Event.host_institution_id == institution_id)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Event.starts_at.asc()).offset(page.offset).limit(page.limit)
        )
    ).scalars().all()

    registered: set[uuid.UUID] = set()
    if user is not None and rows:
        registered = set(
            (
                await db.execute(
                    select(EventRegistration.event_id).where(
                        EventRegistration.user_id == user.id,
                        EventRegistration.event_id.in_([r.id for r in rows]),
                    )
                )
            ).scalars()
        )

    items = []
    for row in rows:
        item = EventOut.model_validate(row)
        item.is_registered = row.id in registered
        item.has_capacity = row.has_capacity
        items.append(item)
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/{event_id}",
    response_model=Envelope[EventOut],
    responses=ERRORS,
    summary="Event detail",
)
async def get_event(
    event_id: uuid.UUID, db: DbSession, user: OptionalUser = None
) -> dict:
    event = (
        await db.execute(
            select(Event).where(Event.id == event_id, Event.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if event is None:
        raise NotFoundError("Event not found", code="EVENT_NOT_FOUND")
    item = EventOut.model_validate(event)
    item.has_capacity = event.has_capacity
    if user is not None:
        existing = (
            await db.execute(
                select(EventRegistration).where(
                    EventRegistration.event_id == event.id,
                    EventRegistration.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        item.is_registered = existing is not None
    return ok(item)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[EventOut],
    responses=ERRORS,
    summary="Create an event",
    description="Companies, institutions and academicians can host events.",
)
async def create_event(
    payload: EventIn,
    db: DbSession,
    user: Annotated[object, Depends(require_permission("event:manage"))],
) -> dict:
    event = Event(
        **payload.model_dump(),
        slug=await unique_slug(db, Event, payload.title),
        host_company_id=user.company_id,
        host_institution_id=user.institution_id,
        created_by_id=user.id,
    )
    event.search_text = " ".join(
        [event.title, event.description, event.speaker_name or "",
         " ".join(str(t) for t in (event.skill_tags or []))]
    ).lower()[:12000]
    db.add(event)
    await db.commit()
    return ok(EventOut.model_validate(event))


@router.patch(
    "/{event_id}",
    response_model=Envelope[EventOut],
    responses=ERRORS,
    summary="Update an event",
)
async def update_event(
    event_id: uuid.UUID,
    payload: EventIn,
    db: DbSession,
    user: Annotated[object, Depends(require_permission("event:manage"))],
) -> dict:
    event = (
        await db.execute(
            select(Event).where(Event.id == event_id, Event.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if event is None:
        raise NotFoundError("Event not found", code="EVENT_NOT_FOUND")
    if (
        event.created_by_id != user.id
        and RoleName.SUPER_ADMIN.value not in user.role_names
    ):
        raise PermissionDeniedError("This event belongs to someone else",
                                    code="EVENT_NOT_OWNED")
    for field, value in payload.model_dump().items():
        setattr(event, field, value)
    await db.commit()
    return ok(EventOut.model_validate(event))


@router.post(
    "/{event_id}/register",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[EventRegistrationOut],
    responses=ERRORS,
    summary="Register for an event",
    description="Registers the caller. When capacity is reached, further "
                "registrations are waitlisted rather than rejected.",
)
async def register_for_event(
    event_id: uuid.UUID, db: DbSession, user: ActiveUser
) -> dict:
    event = (
        await db.execute(
            select(Event).where(Event.id == event_id, Event.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if event is None or not event.is_published:
        raise NotFoundError("Event not found", code="EVENT_NOT_FOUND")
    deadline = _aware(event.registration_deadline) or _aware(event.starts_at)
    if deadline and deadline < _now():
        raise BusinessRuleError("Registration has closed", code="REGISTRATION_CLOSED")

    existing = (
        await db.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event.id,
                EventRegistration.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("You are already registered", code="ALREADY_REGISTERED")

    waitlisted = not event.has_capacity
    registration = EventRegistration(
        event_id=event.id,
        user_id=user.id,
        status=(
            RegistrationStatus.WAITLISTED if waitlisted else RegistrationStatus.REGISTERED
        ),
    )
    db.add(registration)
    if not waitlisted:
        event.registered_count += 1

    await notification.notify(
        db, user.id,
        category=NotificationCategory.EVENT,
        title=("Waitlisted for " if waitlisted else "Registered for ") + event.title,
        body=f"{event.starts_at:%d %b %Y at %H:%M} UTC",
        action_url=f"/events/{event.id}",
        action_label="View event",
        icon="calendar",
        resource_type="event",
        resource_id=event.id,
    )
    await db.commit()
    data = EventRegistrationOut.model_validate(registration)
    data.event = EventOut.model_validate(event)
    return ok(data)


@router.delete(
    "/{event_id}/register",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Cancel a registration",
)
async def cancel_registration(
    event_id: uuid.UUID, db: DbSession, user: ActiveUser
) -> MessageResponse:
    registration = (
        await db.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if registration is None:
        raise NotFoundError("You are not registered", code="REGISTRATION_NOT_FOUND")
    event = await db.get(Event, event_id)
    if registration.status == RegistrationStatus.REGISTERED and event:
        event.registered_count = max(0, event.registered_count - 1)
        # Promote the earliest waitlisted registration into the freed seat.
        promoted = (
            await db.execute(
                select(EventRegistration)
                .where(
                    EventRegistration.event_id == event_id,
                    EventRegistration.status == RegistrationStatus.WAITLISTED,
                )
                .order_by(EventRegistration.created_at)
                .limit(1)
            )
        ).scalar_one_or_none()
        if promoted is not None:
            promoted.status = RegistrationStatus.REGISTERED
            event.registered_count += 1
            await notification.notify(
                db, promoted.user_id,
                category=NotificationCategory.EVENT,
                title=f"A place opened up: {event.title}",
                body="You have moved off the waitlist.",
                action_url=f"/events/{event.id}", icon="calendar",
                resource_type="event", resource_id=event.id,
            )
    registration.status = RegistrationStatus.CANCELLED
    await db.commit()
    return MessageResponse(message="Registration cancelled")


@router.get(
    "/registrations/mine",
    response_model=Page[EventRegistrationOut],
    responses=ERRORS,
    summary="My event registrations",
)
async def my_registrations(
    db: DbSession, user: ActiveUser, page: Annotated[PaginationParams, Depends(pagination)]
) -> Page[EventRegistrationOut]:
    stmt = (
        select(EventRegistration)
        .where(EventRegistration.user_id == user.id)
        .options(selectinload(EventRegistration.event))
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(EventRegistration.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
    ).scalars().all()
    items = []
    for row in rows:
        data = EventRegistrationOut.model_validate(row)
        if row.event:
            data.event = EventOut.model_validate(row.event)
        items.append(data)
    return Page.build(items, total, page.page, page.page_size)


@router.post(
    "/{event_id}/attendance",
    response_model=Envelope[dict],
    responses=ERRORS,
    summary="Mark attendance",
    description="Organisers mark who attended and optionally issue certificates "
                "with a verifiable code.",
)
async def mark_attendance(
    event_id: uuid.UUID,
    payload: AttendanceIn,
    db: DbSession,
    user: Annotated[object, Depends(require_permission("event:manage"))],
) -> dict:
    event = await db.get(Event, event_id)
    if event is None:
        raise NotFoundError("Event not found", code="EVENT_NOT_FOUND")
    if (
        event.created_by_id != user.id
        and RoleName.SUPER_ADMIN.value not in user.role_names
    ):
        raise PermissionDeniedError("This event belongs to someone else",
                                    code="EVENT_NOT_OWNED")

    registrations = (
        await db.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id.in_(payload.user_ids),
            )
        )
    ).scalars().all()

    marked = issued = 0
    for registration in registrations:
        registration.status = RegistrationStatus.ATTENDED
        registration.attended_at = _now()
        marked += 1
        if payload.issue_certificates and event.grants_certificate:
            if not registration.certificate_issued:
                registration.certificate_issued = True
                registration.certificate_code = (
                    f"SB-{str(event.id)[:4].upper()}-{secrets.token_hex(4).upper()}"
                )
                issued += 1
            await notification.notify(
                db, registration.user_id,
                category=NotificationCategory.EVENT,
                title=f"Certificate issued: {event.title}",
                body=f"Certificate code {registration.certificate_code}",
                action_url="/student/workshops", icon="award",
                resource_type="event", resource_id=event.id,
            )
    await db.commit()
    return ok({"attendance_marked": marked, "certificates_issued": issued})


@router.post(
    "/{event_id}/feedback",
    response_model=MessageResponse,
    responses=ERRORS,
    summary="Leave event feedback",
)
async def event_feedback(
    event_id: uuid.UUID, payload: EventFeedbackIn, db: DbSession, user: ActiveUser
) -> MessageResponse:
    registration = (
        await db.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if registration is None:
        raise NotFoundError("You did not register for this event",
                            code="REGISTRATION_NOT_FOUND")
    registration.feedback_rating = payload.rating
    registration.feedback_comment = payload.comment
    await db.commit()
    return MessageResponse(message="Thanks for the feedback")
