"""Structured logging configuration with request correlation ids."""
from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

import structlog

from app.core.config import settings

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)

_SENSITIVE_KEYS = {
    "password", "new_password", "current_password", "token", "access_token",
    "refresh_token", "authorization", "secret", "api_key", "jwt_secret",
    "s3_secret_key", "smtp_password",
}


def _redact(_logger: object, _name: str, event_dict: dict) -> dict:
    """Never let credentials reach the logs."""
    for key in list(event_dict):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***redacted***"
    return event_dict


def _add_context(_logger: object, _name: str, event_dict: dict) -> dict:
    if rid := request_id_ctx.get():
        event_dict.setdefault("request_id", rid)
    if uid := user_id_ctx.get():
        event_dict.setdefault("user_id", uid)
    return event_dict


def configure_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)
    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine", "botocore", "asyncio"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))

    renderer = (
        structlog.processors.JSONRenderer()
        if settings.LOG_JSON or settings.is_production
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_context,
            _redact,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "skillbridge") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
