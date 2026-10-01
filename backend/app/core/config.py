"""Application configuration.

All settings are sourced from environment variables (or a local ``.env`` file).
No secret is ever hard-coded: the defaults here are development-only values and
the application refuses to boot in production if they have not been replaced.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]

# Development-only defaults. Production boot fails if these are still in place.

# not credentials. validate_runtime() refuses to boot production while either
# is still in effect.
DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me"  # noqa: S105
DEV_REFRESH_SECRET = "dev-only-insecure-refresh-secret-change-me"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # Without this, pydantic-settings JSON-decodes every list-typed field
        # straight out of the .env file and raises before any validator runs —
        # so the comma-separated form that .env.example documents
        # (CORS_ORIGINS=http://a,http://b) would be a hard startup failure.
        # Decoding is left to `_split_csv` below, which accepts both forms.
        enable_decoding=False,
    )

    # ------------------------------------------------------------------ app
    APP_NAME: str = "SkillBridge"
    APP_SUBTITLE: str = "Academia-Industry Collaboration & Employability Platform"
    ENVIRONMENT: Environment = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # ------------------------------------------------------------- database
    # Async SQLAlchemy URL. Docker/production => postgresql+asyncpg://...
    # Local quick-start / tests => sqlite+aiosqlite:///./skillbridge.db
    DATABASE_URL: str = "sqlite+aiosqlite:///./skillbridge.db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800

    # ---------------------------------------------------------------- redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 300
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    CELERY_TASK_ALWAYS_EAGER: bool = True  # run inline when no worker is present

    # ----------------------------------------------------------------- auth
    JWT_SECRET: str = DEV_JWT_SECRET
    JWT_REFRESH_SECRET: str = DEV_REFRESH_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 48
    PASSWORD_RESET_EXPIRE_MINUTES: int = 60
    PASSWORD_MIN_LENGTH: int = 10
    REQUIRE_EMAIL_VERIFICATION: bool = False
    MAX_ACTIVE_SESSIONS: int = 10

    # ------------------------------------------------------------ rate limit
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 300
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_WRITE_PER_MINUTE: int = 60

    # ----------------------------------------------------------------- cors
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    TRUSTED_HOSTS: list[str] = Field(default_factory=lambda: ["*"])
    CSRF_ENABLED: bool = True
    SECURE_COOKIES: bool = False
    COOKIE_DOMAIN: str | None = None

    # ----------------------------------------------------------------- mail
    EMAIL_PROVIDER: Literal["console", "smtp", "sendgrid", "ses", "resend"] = "console"
    EMAIL_FROM: str = "no-reply@skillbridge.local"
    EMAIL_FROM_NAME: str = "SkillBridge"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = False
    EMAIL_API_KEY: str = ""

    # -------------------------------------------------------------- storage
    STORAGE_PROVIDER: Literal["local", "s3"] = "local"
    STORAGE_LOCAL_PATH: str = "./var/uploads"
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "skillbridge"
    S3_USE_SSL: bool = False
    SIGNED_URL_EXPIRE_SECONDS: int = 900
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_UPLOAD_MIME: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/png",
            "image/jpeg",
        ]
    )
    VIRUS_SCAN_ENABLED: bool = False

    # ------------------------------------------------------------------- ai
    AI_PROVIDER: Literal["deterministic", "openai", "anthropic", "local"] = "deterministic"
    AI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_BASE_URL: str = ""
    AI_TIMEOUT_SECONDS: int = 30
    AI_ENABLE_LLM_NARRATIVES: bool = True

    # ------------------------------------------------------- matching engine
    # Weights must sum to 1.0; validated below. Configurable per deployment.
    MATCH_WEIGHT_SKILLS: float = 0.50
    MATCH_WEIGHT_EDUCATION: float = 0.15
    MATCH_WEIGHT_INTEREST: float = 0.10
    MATCH_WEIGHT_EXPERIENCE: float = 0.10
    MATCH_WEIGHT_LOCATION: float = 0.05
    MATCH_WEIGHT_CERTIFICATION: float = 0.05
    MATCH_WEIGHT_PROJECT: float = 0.05

    # ---------------------------------------------------------------- seeds
    # Development fixture password shared by every demo account. The seeder
    # refuses to run when ENVIRONMENT=production; never use it there.
    SEED_DEMO_PASSWORD: str = "DemoPass!2024"  # noqa: S105

    @field_validator("CORS_ORIGINS", "TRUSTED_HOSTS", "ALLOWED_UPLOAD_MIME", mode="before")
    @classmethod
    def _split_csv(cls, v: Any) -> Any:
        """Accept both JSON arrays and comma separated strings from env.

        Both forms appear in the wild: a JSON array is what an orchestrator
        tends to inject, a comma separated list is what a human writes in a
        `.env`. Rejecting either would be a needless trap.
        """
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "expected a JSON array or a comma separated list, "
                        f"got {v[:60]!r}"
                    ) from exc
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT in ("production", "staging")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Synchronous URL, used by Alembic."""
        return (
            self.DATABASE_URL.replace("+asyncpg", "+psycopg2")
            .replace("+aiosqlite", "")
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @computed_field  # type: ignore[prop-decorator]
    @property
    def match_weights(self) -> dict[str, float]:
        return {
            "skills": self.MATCH_WEIGHT_SKILLS,
            "education": self.MATCH_WEIGHT_EDUCATION,
            "interest": self.MATCH_WEIGHT_INTEREST,
            "experience": self.MATCH_WEIGHT_EXPERIENCE,
            "location": self.MATCH_WEIGHT_LOCATION,
            "certification": self.MATCH_WEIGHT_CERTIFICATION,
            "project": self.MATCH_WEIGHT_PROJECT,
        }

    def validate_runtime(self) -> list[str]:
        """Return a list of fatal misconfigurations (checked on startup)."""
        problems: list[str] = []
        if self.is_production:
            if self.JWT_SECRET == DEV_JWT_SECRET:
                problems.append("JWT_SECRET must be set to a unique value in production")
            if self.JWT_REFRESH_SECRET == DEV_REFRESH_SECRET:
                problems.append("JWT_REFRESH_SECRET must be set to a unique value in production")
            if self.DEBUG:
                problems.append("DEBUG must be false in production")
            if "*" in self.CORS_ORIGINS:
                problems.append("CORS_ORIGINS must not be a wildcard in production")
            # A wildcard here disables Host-header validation entirely, which
            # is what makes cache-poisoning and password-reset-link poisoning
            # possible. It must name the real hostnames.
            if "*" in self.TRUSTED_HOSTS:
                problems.append("TRUSTED_HOSTS must list real hostnames in production")
            if self.JWT_SECRET == self.JWT_REFRESH_SECRET:
                problems.append(
                    "JWT_SECRET and JWT_REFRESH_SECRET must differ, so a refresh "
                    "token cannot be replayed as an access token"
                )
            if not self.SECURE_COOKIES:
                problems.append("SECURE_COOKIES must be true in production")
        total = sum(self.match_weights.values())
        if abs(total - 1.0) > 1e-6:
            problems.append(f"MATCH_WEIGHT_* values must sum to 1.0 (got {total:.4f})")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
