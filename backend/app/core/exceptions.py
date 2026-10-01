"""Domain exceptions and the standardised API error envelope.

Every error returned by the API has the shape::

    {"success": false, "error": {"code": "...", "message": "...", "details": ...}}

Internal exception text is never leaked to clients: unhandled errors are logged
with a correlation id and reported as a generic INTERNAL_ERROR.
"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all expected application errors."""

    status_code: int = 400
    code: str = "BAD_REQUEST"
    message: str = "Request could not be processed"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            payload["details"] = self.details
        return payload


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "Resource already exists"


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "Submitted data is invalid"


class AuthenticationError(AppError):
    status_code = 401
    code = "NOT_AUTHENTICATED"
    message = "Authentication credentials were not provided or are invalid"


class InvalidCredentialsError(AuthenticationError):
    code = "INVALID_CREDENTIALS"
    message = "Incorrect email or password"


class TokenError(AuthenticationError):
    code = "INVALID_TOKEN"
    message = "Token is invalid or has expired"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action"


class RateLimitError(AppError):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests, please slow down"


class BusinessRuleError(AppError):
    status_code = 409
    code = "BUSINESS_RULE_VIOLATION"
    message = "This action is not allowed in the current state"


class StorageError(AppError):
    status_code = 500
    code = "STORAGE_ERROR"
    message = "File could not be stored"


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = "UNSUPPORTED_FILE_TYPE"
    message = "This file type is not allowed"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "FILE_TOO_LARGE"
    message = "Uploaded file exceeds the maximum allowed size"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    message = "Dependent service is unavailable"


# Convenience factories used across the service layer -------------------------
def not_found(resource: str) -> NotFoundError:
    slug = resource.upper().replace(" ", "_")
    return NotFoundError(f"{resource} not found", code=f"{slug}_NOT_FOUND")


def conflict(resource: str, message: str) -> ConflictError:
    slug = resource.upper().replace(" ", "_")
    return ConflictError(message, code=f"{slug}_CONFLICT")
