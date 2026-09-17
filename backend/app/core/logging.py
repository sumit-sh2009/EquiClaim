"""Structured request logging — Phase 8 hardening.

EquiClaim handles PHI-adjacent financial dispute data, so every inbound
request gets a correlation id and a single structured access-log line
recording who (tenant, once auth has resolved it) touched what endpoint,
the outcome status code, and latency. This is deliberately a thin
`BaseHTTPMiddleware`, not a general logging framework — request bodies and
uploaded documents are never logged.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("equiclaim.access")

REQUEST_ID_HEADER = "X-Request-Id"


def configure_logging(*, environment: str) -> None:
    """Install a single structured stream handler for the whole app.

    Dev/local gets a human-readable line; anything else gets a machine-
    parseable `key=value` line so it can be piped into a log aggregator
    without a separate JSON-logging dependency.
    """
    level = logging.DEBUG if environment == "development" else logging.INFO
    handler = logging.StreamHandler()
    if environment in ("development", "test"):
        fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    else:
        fmt = (
            'time="%(asctime)s" level=%(levelname)s logger=%(name)s msg="%(message)s"'
        )
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet down noisy third-party loggers unless we're actively debugging.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, times the request, and emits one access-log line.

    The resolved `tenant_id` is read off `request.state.tenant_id`, which
    `app.core.security.require_tenant` sets once auth succeeds — so
    unauthenticated requests log `tenant_id=-` rather than failing.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            tenant_id = getattr(request.state, "tenant_id", "-")
            logger.exception(
                "request_id=%s method=%s path=%s tenant_id=%s status=500 duration_ms=%.1f",
                request_id,
                request.method,
                request.url.path,
                tenant_id,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - started) * 1000
        tenant_id = getattr(request.state, "tenant_id", "-")
        logger.info(
            "request_id=%s method=%s path=%s tenant_id=%s status=%d duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            tenant_id,
            response.status_code,
            elapsed_ms,
        )
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
