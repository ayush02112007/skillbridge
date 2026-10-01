"""Lightweight, permissioned messaging between platform participants."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base, TimestampMixin, UUIDMixin


class Conversation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_context", "context_type", "context_id"),
    )

    subject: Mapped[str] = mapped_column(String(220), default="")
    # Conversations are always anchored to a legitimate context (an application,
    # a mentorship request, a project) - this is what authorises the thread.
    context_type: Mapped[str] = mapped_column(String(40), nullable=False)
    context_id: Mapped[uuid.UUID | None] = mapped_column(GUID)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    participants: Mapped[list[ConversationParticipant]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", lazy="selectin"
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at", lazy="noload",
    )


class ConversationParticipant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="conversation_participant_unique"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    conversation: Mapped[Conversation] = relationship(
        back_populates="participants", lazy="noload"
    )


class Message(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("documents.id", ondelete="SET NULL")
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages", lazy="noload")
