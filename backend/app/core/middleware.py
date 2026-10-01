"""HTTP middleware: correlation ids, security headers, rate limiting, CSRF."""
from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger, request_id_ctx, user_id_ctx
from app.core.security import unsign_value

log = get_logger("http")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id, time the request and emit one structured access log."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request_id_ctx.set(request_id)
        user_id_ctx.set(None)
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = (time.perf_counter() - started) * 1000
            log.exception(
                "http.request_failed",
                method=request.method, path=request.url.path, duration_ms=round(duration, 2),
            )
            raise
        duration = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.1f}ms"
        if not request.url.path.startswith(("/health", "/ready", "/metrics")):
            log.info(
                "http.request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration, 2),
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """OWASP secure-header baseline."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
        )
        headers.setdefault("X-XSS-Protection", "0")  # rely on CSP, not the legacy filter
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        # The API serves JSON and the Swagger UI only; the docs pages need
        # the CDN assets, everything else is locked down.
        if request.url.path in ("/docs", "/redoc", "/openapi.json"):
            headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "font-src 'self' data: https://cdn.jsdelivr.net; "
                "worker-src 'self' blob:; "
                "frame-ancestors 'none'",
            )
        else:
            headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
        if settings.is_production:
            headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window limiter keyed on client IP + route class.

    Authentication routes get a much tighter budget than reads. The window is
    process-local; a multi-worker deployment should front this with the Nginx
    ``limit_req`` zone shipped in infrastructure/nginx (documented in the README).
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _limit_for(self, request: Request) -> tuple[str, int]:
        path = request.url.path
        if "/auth/" in path and request.method == "POST":
            return "auth", settings.RATE_LIMIT_AUTH_PER_MINUTE
        if request.method not in SAFE_METHODS:
            return "write", settings.RATE_LIMIT_WRITE_PER_MINUTE
        return "read", settings.RATE_LIMIT_DEFAULT_PER_MINUTE

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.RATE_LIMIT_ENABLED or request.url.path.startswith(
            ("/health", "/ready")
        ):
            return await call_next(request)

        bucket, limit = self._limit_for(request)
        ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "anonymous")
        )
        key = f"{bucket}:{ip}"
        now = time.time()
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            retry_after = max(1, int(60 - (now - window[0])))
            log.warning("http.rate_limited", bucket=bucket, path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests, please slow down",
                    },
                },
                headers={"Retry-After": str(retry_after)},
            )
        window.append(now)
        if len(self._hits) > 20000:  # bound memory under a distributed scan
            for stale in [k for k, v in list(self._hits.items())[:5000] if not v]:
                self._hits.pop(stale, None)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(window)))
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF protection for cookie-authenticated state changes.

    Requests carrying an ``Authorization: Bearer`` header are exempt: a bearer
    token is not sent automatically by the browser, so it is not forgeable
    cross-site. Only cookie-authenticated mutations require the token.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (
            not settings.CSRF_ENABLED
            or request.method in SAFE_METHODS
            or request.headers.get("authorization", "").lower().startswith("bearer ")
            or not request.cookies.get("access_token")
        ):
            return await call_next(request)

        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("x-csrf-token")
        if not cookie_token or not header_token or unsign_value(cookie_token) is None:
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {
                        "code": "CSRF_TOKEN_INVALID",
                        "message": "Missing or invalid CSRF token",
                    },
                },
            )
        if cookie_token != header_token:
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {
                        "code": "CSRF_TOKEN_MISMATCH",
                        "message": "CSRF token does not match",
                    },
                },
            )
        return await call_next(request)
