"""Authentication request/response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import EmailStr, Field, field_validator, model_validator

from app.models.enums import RoleName, UserStatus
from app.schemas.common import APIModel

PasswordStr = Annotated[str, Field(min_length=10, max_length=128, examples=["Str0ng!Passw0rd"])]

SIGNUP_ROLES = Literal[
    "STUDENT", "ACADEMICIAN", "INDUSTRY_RECRUITER", "INDUSTRY_ADMIN"
]


class RegisterRequest(APIModel):
    email: EmailStr = Field(examples=["aditi.sharma@example.edu"])
    password: PasswordStr
    full_name: str = Field(min_length=2, max_length=160, examples=["Aditi Sharma"])
    role: SIGNUP_ROLES = Field(
        default="STUDENT",
        description="Institution and platform admin accounts are provisioned by an "
                    "administrator and cannot be self-registered.",
    )
    phone: str | None = Field(default=None, max_length=32)
    institution_id: uuid.UUID | None = Field(
        default=None, description="Required for students and academicians"
    )
    company_id: uuid.UUID | None = Field(
        default=None, description="Existing company to join as a recruiter"
    )
    company_name: str | None = Field(
        default=None, max_length=200,
        description="Creates a new company workspace (INDUSTRY_ADMIN only)",
    )
    accept_terms: bool = Field(description="Must be true")

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        cleaned = " ".join(v.split())
        if not cleaned.replace("-", " ").replace("'", " ").replace(".", " ").strip():
            raise ValueError("Please provide a valid name")
        return cleaned

    @field_validator("accept_terms")
    @classmethod
    def _terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the terms to create an account")
        return v

    @model_validator(mode="after")
    def _role_requirements(self) -> RegisterRequest:
        if self.role == "INDUSTRY_RECRUITER" and not (self.company_id or self.company_name):
            raise ValueError("Recruiters must select or name a company")
        if self.role == "INDUSTRY_ADMIN" and not (self.company_name or self.company_id):
            raise ValueError("Provide the company you are registering")
        return self


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class TokenPair(APIModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - scheme name, not a secret
    expires_in: int = Field(description="Access-token lifetime in seconds")
    expires_at: datetime


class RefreshRequest(APIModel):
    refresh_token: str | None = Field(
        default=None, description="Omit when the refresh token is sent as a cookie"
    )


class LogoutRequest(APIModel):
    refresh_token: str | None = None
    all_sessions: bool = False


class ForgotPasswordRequest(APIModel):
    email: EmailStr


class ResetPasswordRequest(APIModel):
    token: str = Field(min_length=10)
    new_password: PasswordStr


class ChangePasswordRequest(APIModel):
    current_password: str = Field(min_length=1)
    new_password: PasswordStr

    @model_validator(mode="after")
    def _different(self) -> ChangePasswordRequest:
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current one")
        return self


class VerifyEmailRequest(APIModel):
    token: str = Field(min_length=10)


class ResendVerificationRequest(APIModel):
    email: EmailStr


class RoleOut(APIModel):
    name: RoleName
    label: str
    description: str


class UserOut(APIModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    status: UserStatus
    is_email_verified: bool
    locale: str
    timezone_name: str
    institution_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    roles: list[RoleOut] = []
    created_at: datetime
    last_login_at: datetime | None = None


class SessionOut(APIModel):
    id: uuid.UUID
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


class AuthenticatedUser(APIModel):
    """Everything the frontend needs immediately after authenticating."""

    user: UserOut
    roles: list[str]
    permissions: list[str]
    home_route: str
    profile_id: uuid.UUID | None = None
    profile_completion: int = 0
    requires_onboarding: bool = False
    csrf_token: str | None = None


class AuthResponse(APIModel):
    tokens: TokenPair
    session: AuthenticatedUser


class UpdateMeRequest(APIModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    avatar_url: str | None = Field(default=None, max_length=512)
    locale: str | None = Field(default=None, max_length=10)
    timezone_name: str | None = Field(default=None, max_length=64)
