"""Exception handlers producing the standard error envelope."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.core.logging import get_logger

log = get_logger("errors")

_STATUS_CODES = {
    400: "BAD_REQUEST", 401: "NOT_AUTHENTICATED", 403: "PERMISSION_DENIED",
    404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE", 415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR", 429: "RATE_LIMIT_EXCEEDED", 500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def _envelope(code: str, message: str, details=None) -> dict:
    error: dict = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"success": False, "error": error}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            log.error("app_error", code=exc.code, message=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = []
        for err in exc.errors():
            location = [str(p) for p in err.get("loc", []) if p not in ("body", "query")]
            fields.append(
                {
                    "field": ".".join(location) or "body",
                    "message": err.get("msg", "Invalid value"),
                    "type": err.get("type", "invalid"),
                }
            )
        return JSONResponse(
            status_code=422,
            content=_envelope(
                "VALIDATION_ERROR", "Submitted data is invalid", {"fields": fields}
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, detail),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_request: Request, exc: IntegrityError) -> JSONResponse:
        # Constraint text can reveal schema internals - log it, don't return it.
        log.warning("db.integrity_error", detail=str(exc.orig)[:300])
        return JSONResponse(
            status_code=409,
            content=_envelope(
                "CONSTRAINT_VIOLATION",
                "This action conflicts with existing data",
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        log.exception("db.error", detail=str(exc)[:300])
        return JSONResponse(
            status_code=503,
            content=_envelope("DATABASE_ERROR", "The database is temporarily unavailable"),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        log.exception("unhandled_error", path=request.url.path, error=str(exc)[:500])
        return JSONResponse(
            status_code=500,
            content=_envelope(
                "INTERNAL_ERROR",
                "Something went wrong on our side. "
                + (f"Reference: {request_id}" if request_id else ""),
            ),
        )
