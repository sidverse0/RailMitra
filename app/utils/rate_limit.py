"""
Simple in-memory, fixed-window, per-client-IP rate limiter.

Not distributed (fine for a single-process deployment such as a single
Render web service). Protects the upstream scraping targets from being
hammered and gives API consumers a clear, consistent 429 response instead
of the upstream site silently blocking the server's IP.
"""
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.utils.errors import error_envelope

_hits: dict[str, list] = defaultdict(list)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED or request.url.path in ("/", "/health"):
            return await call_next(request)

        key = _client_key(request)
        now = time.monotonic()
        window_start = now - settings.RATE_LIMIT_WINDOW_SECONDS

        hits = _hits[key]
        while hits and hits[0] < window_start:
            hits.pop(0)

        if len(hits) >= settings.RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=429,
                content=error_envelope(
                    "RATE_LIMIT_EXCEEDED",
                    f"Too many requests. Limit is {settings.RATE_LIMIT_REQUESTS} "
                    f"requests per {settings.RATE_LIMIT_WINDOW_SECONDS}s.",
                ),
            )

        hits.append(now)
        return await call_next(request)
