from __future__ import annotations

import logging
import re
import time
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from config import settings


logger = logging.getLogger("antiquar.http")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


class ApplicationHttpMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming_id = request.headers.get("x-request-id", "")
        request_id = incoming_id if _REQUEST_ID_RE.fullmatch(incoming_id) else uuid4().hex
        request.state.request_id = request_id
        request.state.client_ip = _client_ip(request)

        if (
            settings.is_production
            and request.method in _UNSAFE_METHODS
            and request.url.path.startswith("/api/admin/")
        ):
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            valid_origin = origin == settings.public_origin
            valid_referer = referer is not None and referer.startswith(f"{settings.public_origin}/")
            if not (valid_origin or valid_referer):
                logger.warning(
                    "Rejected admin request with invalid origin",
                    extra={
                        "event": "csrf_origin_rejected",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "client_ip": request.state.client_ip,
                    },
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Invalid request origin"},
                    headers={"X-Request-ID": request_id},
                )

        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            logger.exception(
                "Unhandled request exception",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "client_ip": request.state.client_ip,
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.state.client_ip,
                },
            )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if request.url.path.startswith("/api/admin/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"

        return response
