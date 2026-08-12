"""
Shared, reusable HTTP client.

Centralizes: timeouts, User-Agent header, connection reuse, and bounded
retries for transient failures. Every service module funnels its upstream
requests through `fetch_text()` / `fetch_bytes()` here instead of creating
ad-hoc requests, so behaviour (timeouts, retries, headers) stays consistent
project-wide and each logical API call makes exactly one upstream request
unless the feature genuinely requires a chained lookup (e.g. route lookup
needs the train's internal id first).
"""
import asyncio
import random
from typing import Optional

import httpx

from app.config import settings
from app.utils.errors import UpstreamTimeoutError, UpstreamHTTPError, EmptyResponseError

_client: Optional[httpx.AsyncClient] = None

# A small pool of realistic desktop User-Agent strings. Rotating avoids
# relying on a single static UA (mirrors the intent of the `user_agent` /
# `user-agents` packages used by the original projects) without adding an
# extra dependency.
_USER_AGENTS = [
    settings.DEFAULT_USER_AGENT,
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def random_user_agent() -> str:
    return random.choice(_USER_AGENTS)


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        timeout = httpx.Timeout(
            settings.HTTP_TIMEOUT_SECONDS,
            connect=settings.HTTP_CONNECT_TIMEOUT_SECONDS,
        )
        _client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": settings.DEFAULT_USER_AGENT},
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def fetch_text(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    retries: Optional[int] = None,
    allow_empty: bool = False,
) -> str:
    """GET a URL and return response text, with bounded retries on network errors."""
    client = get_client()
    req_headers = {"User-Agent": random_user_agent()}
    if headers:
        req_headers.update(headers)

    max_retries = settings.HTTP_MAX_RETRIES if retries is None else retries
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            resp = await client.get(url, params=params, headers=req_headers)
            if resp.status_code >= 500:
                raise UpstreamHTTPError(
                    f"Upstream returned HTTP {resp.status_code} for {url}"
                )
            if resp.status_code >= 400:
                # Client errors are not retried — the request itself is bad.
                raise UpstreamHTTPError(
                    f"Upstream returned HTTP {resp.status_code} for {url}",
                )
            text = resp.text
            if not allow_empty and (text is None or text.strip() == ""):
                raise EmptyResponseError(f"Upstream returned an empty response for {url}")
            return text
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException) as exc:
            last_exc = exc
        except httpx.RequestError as exc:
            last_exc = exc
        except UpstreamHTTPError:
            raise

        if attempt < max_retries:
            await asyncio.sleep(settings.HTTP_RETRY_BACKOFF_SECONDS * (attempt + 1))

    if isinstance(last_exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException)):
        raise UpstreamTimeoutError(f"Timed out contacting upstream: {url}") from last_exc
    raise UpstreamHTTPError(f"Failed to contact upstream: {url} ({last_exc})") from last_exc


async def fetch_json(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    retries: Optional[int] = None,
) -> tuple[int, dict]:
    """GET a URL and return (http_status_code, parsed_json_body).

    Unlike fetch_text, this does NOT raise on 4xx/5xx — some APIs (like
    RailRadar) return a structured JSON error body alongside a non-2xx
    status that the caller needs to inspect (e.g. to distinguish 401 auth
    errors from 404 not-found from 429 rate-limits). Network-level failures
    (timeouts, connection errors) still raise, with bounded retries, same
    as fetch_text.
    """
    import json as _json

    client = get_client()
    req_headers = {"User-Agent": random_user_agent()}
    if headers:
        req_headers.update(headers)

    max_retries = settings.HTTP_MAX_RETRIES if retries is None else retries
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            resp = await client.get(url, params=params, headers=req_headers)
            try:
                body = resp.json()
            except ValueError:
                body = {}
            return resp.status_code, body
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException) as exc:
            last_exc = exc
        except httpx.RequestError as exc:
            last_exc = exc

        if attempt < max_retries:
            await asyncio.sleep(settings.HTTP_RETRY_BACKOFF_SECONDS * (attempt + 1))

    if isinstance(last_exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException)):
        raise UpstreamTimeoutError(f"Timed out contacting upstream: {url}") from last_exc
    raise UpstreamHTTPError(f"Failed to contact upstream: {url} ({last_exc})") from last_exc


async def post_json(
    url: str,
    json_body: Optional[dict] = None,
    headers: Optional[dict] = None,
    retries: Optional[int] = None,
) -> tuple[int, dict]:
    """POST a JSON body and return (http_status_code, parsed_json_body).

    Mirrors fetch_json's behaviour but for POST requests (used for APIs like
    the PNR lookup source in app/services/pnr_lostingness.py, which expect a
    JSON body rather than query params). Does NOT raise on 4xx/5xx — the
    caller inspects the status code/body to decide how to map it onto our
    exception hierarchy. Network-level failures still raise, with bounded
    retries, same as fetch_json/fetch_text.
    """
    client = get_client()
    req_headers = {"User-Agent": random_user_agent(), "Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    max_retries = settings.HTTP_MAX_RETRIES if retries is None else retries
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            resp = await client.post(url, json=json_body, headers=req_headers)
            try:
                body = resp.json()
            except ValueError:
                body = {}
            return resp.status_code, body
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException) as exc:
            last_exc = exc
        except httpx.RequestError as exc:
            last_exc = exc

        if attempt < max_retries:
            await asyncio.sleep(settings.HTTP_RETRY_BACKOFF_SECONDS * (attempt + 1))

    if isinstance(last_exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException)):
        raise UpstreamTimeoutError(f"Timed out contacting upstream: {url}") from last_exc
    raise UpstreamHTTPError(f"Failed to contact upstream: {url} ({last_exc})") from last_exc


async def fetch_bytes(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    retries: Optional[int] = None,
) -> bytes:
    """GET a URL and return raw response bytes (used for the captcha image)."""
    client = get_client()
    req_headers = {"User-Agent": random_user_agent()}
    if headers:
        req_headers.update(headers)

    max_retries = settings.HTTP_MAX_RETRIES if retries is None else retries
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            resp = await client.get(url, params=params, headers=req_headers)
            if resp.status_code >= 400:
                raise UpstreamHTTPError(f"Upstream returned HTTP {resp.status_code} for {url}")
            content = resp.content
            if not content:
                raise EmptyResponseError(f"Upstream returned an empty response for {url}")
            return content
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException) as exc:
            last_exc = exc
        except httpx.RequestError as exc:
            last_exc = exc
        except UpstreamHTTPError:
            raise

        if attempt < max_retries:
            await asyncio.sleep(settings.HTTP_RETRY_BACKOFF_SECONDS * (attempt + 1))

    if isinstance(last_exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException)):
        raise UpstreamTimeoutError(f"Timed out contacting upstream: {url}") from last_exc
    raise UpstreamHTTPError(f"Failed to contact upstream: {url} ({last_exc})") from last_exc
