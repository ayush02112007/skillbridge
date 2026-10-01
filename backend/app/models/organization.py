"""Institutions, companies and departments."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import VerificationStatus

if TYPE_CHECKING:
    from app.models.user import User


class Institution(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    short_name: Mapped[str | None] = mapped_column(String(40))
    institution_type: Mapped[str] = mapped_column(String(60), default="UNIVERSITY")
    accreditation: Mapped[str | None] = mapped_column(String(120))
    website: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), default="India")
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    established_year: Mapped[int | None] = mapped_column(Integer)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, native_enum=False, length=20),
        default=VerificationStatus.UNVERIFIED, nullable=False,
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    departments: Mapped[list[Department]] = relationship(
        back_populates="institution", cascade="all, delete-orphan", lazy="selectin"
    )
    members: Mapped[list[User]] = relationship(
        back_populates="institution", foreign_keys="User.institution_id", lazy="noload"
    )


class Department(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="department_code_unique"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    hod_name: Mapped[str | None] = mapped_column(String(160))

    institution: Mapped[Institution] = relationship(back_populates="departments", lazy="noload")


class Company(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint("employee_count is null or employee_count >= 0", name="employee_count_non_negative"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    industry_sector: Mapped[str] = mapped_column(String(80), default="Technology", index=True)
    website: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    about: Mapped[str] = mapped_column(Text, default="")
    headquarters_city: Mapped[str | None] = mapped_column(String(100), index=True)
    headquarters_country: Mapped[str] = mapped_column(String(100), default="India")
    locations: Mapped[list[Any]] = mapped_column(default=list)
    employee_count: Mapped[int | None] = mapped_column(Integer)
    founded_year: Mapped[int | None] = mapped_column(Integer)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    tech_stack: Mapped[list[Any]] = mapped_column(default=list)
    benefits: Mapped[list[Any]] = mapped_column(default=list)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, native_enum=False, length=20),
        default=VerificationStatus.UNVERIFIED, nullable=False, index=True,
    )
    is_hiring: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    members: Mapped[list[User]] = relationship(
        back_populates="company", foreign_keys="User.company_id", lazy="noload"
    )


class IndustryPartnership(UUIDMixin, TimestampMixin, Base):
    """A formal collaboration between an institution and a company."""

    __tablename__ = "industry_partnerships"
    __table_args__ = (
        UniqueConstraint("institution_id", "company_id", "partnership_type", name="partnership_unique"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    partnership_type: Mapped[str] = mapped_column(String(60), default="PLACEMENT")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    started_on: Mapped[str | None] = mapped_column(String(20))
    engagement_score: Mapped[int] = mapped_column(Integer, default=0)

    institution: Mapped[Institution] = relationship(lazy="selectin")
    company: Mapped[Company] = relationship(lazy="selectin")
