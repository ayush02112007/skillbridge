"""Materialised, explainable recommendations.

Recommendations are recomputed by a Celery task (or on demand) and stored with
their full reasoning so the UI can always answer "why was this recommended?".
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import GUID, Base, TimestampMixin, UUIDMixin


class Recommendation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "recommendation_type", "target_id", name="recommendation_unique"
        ),
        CheckConstraint("match_score between 0 and 100", name="recommendation_score_range"),
        Index("ix_recommendations_user_type_score", "user_id", "recommendation_type", "match_score"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # INTERNSHIP | JOB | LEARNING | SKILL | CAREER_ROLE | MENTOR | PROJECT | FACULTY_OPPORTUNITY
    recommendation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    target_title: Mapped[str] = mapped_column(String(250), default="")
    match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # {"skills": 0.82, "education": 1.0, ...} - contribution of each factor.
    breakdown: Mapped[dict[str, Any]] = mapped_column(default=dict)
    matching_skills: Mapped[list[Any]] = mapped_column(default=list)
    missing_skills: Mapped[list[Any]] = mapped_column(default=list)
    reasons: Mapped[list[Any]] = mapped_column(default=list)
    reason_summary: Mapped[str] = mapped_column(Text, default="")
    next_steps: Mapped[list[Any]] = mapped_column(default=list)
    generated_by: Mapped[str] = mapped_column(String(32), default="deterministic", nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecommendationFeedback(UUIDMixin, TimestampMixin, Base):
    """Outcome signal used to tune the engine (see docs/recommendation-engine.md)."""

    __tablename__ = "recommendation_feedback"

    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("recommendations.id", ondelete="SET NULL"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # VIEWED | CLICKED | APPLIED | DISMISSED | IRRELEVANT | HIRED
    signal: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    comment: Mapped[str] = mapped_column(String(400), default="")
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
