"""Permissioned messaging between students, recruiters, mentors and faculty.

A conversation is always anchored to a legitimate context - an application, a
mentorship request or a project - which is what authorises the thread. There is
no open inbox, so the platform cannot be used for unsolicited outreach.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import ActiveUser, DbSession
from app.core.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.application import Application
from app.models.enums import NotificationCategory, RoleName
from app.models.mentorship import MentorshipRequest
from app.models.messaging import Conversation, ConversationParticipant, Message
from app.models.opportunity import Opportunity
from app.models.profile import StudentProfile
from app.models.user import User
from app.schemas.common import (
    APIModel,
    Envelope,
    ErrorResponse,
    Page,
    PaginationParams,
    ok,
    pagination,
)
from app.services import notification

router = APIRouter(prefix="/messages", tags=["Messaging"])

ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not permitted"},
    404: {"model": ErrorResponse, "description": "Not found"},
}


class ParticipantOut(APIModel):
    user_id: uuid.UUID
    full_name: str = ""
    avatar_url: str | None = None
    roles: list[str] = []


class MessageOut(APIModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str = ""
    body: str
    attachment_document_id: uuid.UUID | None = None
    is_system: bool = False
    created_at: datetime
    edited_at: datetime | None = None


class ConversationOut(APIModel):
    id: uuid.UUID
    subject: str = ""
    context_type: str
    context_id: uuid.UUID | None = None
    last_message_at: datetime | None = None
    is_closed: bool = False
    unread_count: int = 0
    participants: list[ParticipantOut] = []
    last_message: MessageOut | None = None


class StartConversationIn(APIModel):
    context_type: Literal["application", "mentorship_request"]
    context_id: uuid.UUID
    subject: str = ""
    body: str


class SendMessageIn(APIModel):
    body: str
    attachment_document_id: uuid.UUID | None = None


def _now() -> datetime:
    return datetime.now(UTC)


async def _authorised_counterpart(
    db, user: User, context_type: str, context_id: uuid.UUID
) -> tuple[uuid.UUID, str]:
    """Resolve who the caller is allowed to message, and the thread subject.

    This is the whole authorisation model for messaging: if the caller is not
    one side of a real application or mentorship request, there is nobody they
    are entitled to contact.
    """
    if context_type == "application":
        application = (
            await db.execute(
                select(Application)
                .where(Application.id == context_id)
                .options(
                    selectinload(Application.opportunity).selectinload(Opportunity.company),
                    selectinload(Application.student).selectinload(StudentProfile.user),
                )
            )
        ).scalar_one_or_none()
        if application is None:
            raise NotFoundError("Application not found", code="APPLICATION_NOT_FOUND")
        opportunity = application.opportunity
        student = application.student
        subject = opportunity.title if opportunity else "Application"

        if student and student.user_id == user.id:
            if opportunity is None or opportunity.posted_by_id is None:
                raise BusinessRuleError(
                    "There is no recruiter to contact for this posting",
                    code="NO_COUNTERPART",
                )
            return opportunity.posted_by_id, subject
        if (
            opportunity
            and user.company_id
            and opportunity.company_id == user.company_id
            and set(user.role_names)
            & {RoleName.INDUSTRY_RECRUITER.value, RoleName.INDUSTRY_ADMIN.value}
        ):
            if student is None:
                raise BusinessRuleError("No applicant to contact", code="NO_COUNTERPART")
            return student.user_id, subject
        raise PermissionDeniedError(
            "You are not part of this application", code="NOT_A_PARTICIPANT"
        )

    if context_type == "mentorship_request":
        request_row = (
            await db.execute(
                select(MentorshipRequest)
                .where(MentorshipRequest.id == context_id)
                .options(selectinload(MentorshipRequest.mentor))
            )
        ).scalar_one_or_none()
        if request_row is None:
            raise NotFoundError("Request not found", code="MENTORSHIP_REQUEST_NOT_FOUND")
        from app.models.enums import MentorshipStatus

        if request_row.status == MentorshipStatus.REQUESTED:
            raise BusinessRuleError(
                "Messaging opens once the mentor accepts the request",
                code="MENTORSHIP_NOT_ACCEPTED",
            )
        student = await db.get(StudentProfile, request_row.student_id)
        subject = request_row.topic
        if student and student.user_id == user.id:
            if request_row.mentor is None:
                raise BusinessRuleError("No mentor to contact", code="NO_COUNTERPART")
            return request_row.mentor.user_id, subject
        if request_row.mentor and request_row.mentor.user_id == user.id:
            if student is None:
                raise BusinessRuleError("No student to contact", code="NO_COUNTERPART")
            return student.user_id, subject
        raise PermissionDeniedError(
            "You are not part of this mentorship", code="NOT_A_PARTICIPANT"
        )

    raise BusinessRuleError("Unsupported conversation context", code="UNSUPPORTED_CONTEXT")


async def _conversation_for_user(db, conversation_id: uuid.UUID, user: User) -> Conversation:
    conversation = (
        await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.participants))
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise NotFoundError("Conversation not found", code="CONVERSATION_NOT_FOUND")
    if not any(p.user_id == user.id for p in conversation.participants):
        raise NotFoundError("Conversation not found", code="CONVERSATION_NOT_FOUND")
    return conversation


async def _to_out(db, conversation: Conversation, user: User) -> ConversationOut:
    participants = []
    for participant in conversation.participants:
        person = await db.get(User, participant.user_id)
        if person is not None:
            await db.refresh(person, ["roles"])
            participants.append(
                ParticipantOut(
                    user_id=person.id, full_name=person.full_name,
                    avatar_url=person.avatar_url, roles=person.role_names,
                )
            )
    mine = next((p for p in conversation.participants if p.user_id == user.id), None)
    unread_stmt = select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation.id, Message.sender_id != user.id
    )
    if mine is not None and mine.last_read_at is not None:
        unread_stmt = unread_stmt.where(Message.created_at > mine.last_read_at)
    unread = (await db.execute(unread_stmt)).scalar_one()

    last = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    data = ConversationOut.model_validate(conversation)
    data.participants = participants
    data.unread_count = unread
    if last is not None:
        sender = await db.get(User, last.sender_id)
        data.last_message = MessageOut(
            **MessageOut.model_validate(last).model_dump()
            | {"sender_name": sender.full_name if sender else ""}
        )
    return data


@router.post(
    "/conversations",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[ConversationOut],
    responses=ERRORS,
    summary="Start a conversation",
    description=(
        "Opens a thread anchored to an application or an accepted mentorship "
        "request. Only the two parties to that context may take part - there is "
        "no way to message a stranger."
    ),
)
async def start_conversation(
    payload: StartConversationIn, db: DbSession, user: ActiveUser
) -> dict:
    counterpart_id, subject = await _authorised_counterpart(
        db, user, payload.context_type, payload.context_id
    )

    existing = (
        await db.execute(
            select(Conversation)
            .where(
                Conversation.context_type == payload.context_type,
                Conversation.context_id == payload.context_id,
            )
            .options(selectinload(Conversation.participants))
        )
    ).scalar_one_or_none()
    conversation = existing
    if conversation is None:
        conversation = Conversation(
            subject=(payload.subject or subject)[:220],
            context_type=payload.context_type,
            context_id=payload.context_id,
            created_by_id=user.id,
        )
        db.add(conversation)
        await db.flush()
        db.add(ConversationParticipant(conversation_id=conversation.id, user_id=user.id))
        db.add(
            ConversationParticipant(
                conversation_id=conversation.id, user_id=counterpart_id
            )
        )
        await db.flush()

    message = Message(
        conversation_id=conversation.id, sender_id=user.id, body=payload.body.strip()
    )
    db.add(message)
    conversation.last_message_at = _now()

    await notification.notify(
        db, counterpart_id,
        category=NotificationCategory.MESSAGE,
        title=f"New message from {user.full_name}",
        body=payload.body[:160],
        action_url="/messages",
        action_label="Open conversation",
        icon="message-square",
        resource_type="conversation",
        resource_id=conversation.id,
    )
    await db.commit()
    reloaded = await _conversation_for_user(db, conversation.id, user)
    return ok(await _to_out(db, reloaded, user))


@router.get(
    "/conversations",
    response_model=Page[ConversationOut],
    responses=ERRORS,
    summary="My conversations",
)
async def list_conversations(
    db: DbSession, user: ActiveUser, page: Annotated[PaginationParams, Depends(pagination)]
) -> Page[ConversationOut]:
    stmt = (
        select(Conversation)
        .join(
            ConversationParticipant,
            ConversationParticipant.conversation_id == Conversation.id,
        )
        .where(ConversationParticipant.user_id == user.id)
        .options(selectinload(Conversation.participants))
        .order_by(Conversation.last_message_at.desc().nullslast())
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.offset(page.offset).limit(page.limit))).scalars().all()
    items = [await _to_out(db, row, user) for row in rows]
    return Page.build(items, total, page.page, page.page_size)


@router.get(
    "/conversations/{conversation_id}",
    response_model=Page[MessageOut],
    responses=ERRORS,
    summary="Read a conversation",
    description="Returns the messages and marks the thread read for the caller.",
)
async def read_conversation(
    conversation_id: uuid.UUID,
    db: DbSession,
    user: ActiveUser,
    page: Annotated[PaginationParams, Depends(pagination)],
) -> Page[MessageOut]:
    conversation = await _conversation_for_user(db, conversation_id, user)
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.offset(page.offset).limit(page.limit))).scalars().all()

    mine = next((p for p in conversation.participants if p.user_id == user.id), None)
    if mine is not None:
        mine.last_read_at = _now()
    await db.commit()

    items = []
    for row in rows:
        sender = await db.get(User, row.sender_id)
        data = MessageOut.model_validate(row)
        data.sender_name = sender.full_name if sender else ""
        items.append(data)
    return Page.build(items, total, page.page, page.page_size)


@router.post(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[MessageOut],
    responses=ERRORS,
    summary="Send a message",
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageIn,
    db: DbSession,
    user: ActiveUser,
) -> dict:
    conversation = await _conversation_for_user(db, conversation_id, user)
    if conversation.is_closed:
        raise BusinessRuleError("This conversation is closed", code="CONVERSATION_CLOSED")
    body = payload.body.strip()
    if not body:
        from app.core.exceptions import ValidationError

        raise ValidationError("Message cannot be empty", code="EMPTY_MESSAGE")

    message = Message(
        conversation_id=conversation.id,
        sender_id=user.id,
        body=body[:8000],
        attachment_document_id=payload.attachment_document_id,
    )
    db.add(message)
    conversation.last_message_at = _now()

    for participant in conversation.participants:
        if participant.user_id != user.id and not participant.is_muted:
            await notification.notify(
                db, participant.user_id,
                category=NotificationCategory.MESSAGE,
                title=f"New message from {user.full_name}",
                body=body[:160],
                action_url="/messages",
                icon="message-square",
                resource_type="conversation",
                resource_id=conversation.id,
            )
    await db.commit()
    data = MessageOut.model_validate(message)
    data.sender_name = user.full_name
    return ok(data)
