"""
Custom exception hierarchy + standard JSON envelope helpers.

Every error the API can produce maps to one of these exceptions so that the
global FastAPI exception handlers (see app/main.py) can convert it into a
consistent JSON body without ever leaking a raw Python traceback.
"""
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Optional

IST = ZoneInfo("Asia/Kolkata")


def now_ts() -> int:
    return int(time.time())


def now_ist_str() -> str:
    """Human-readable IST timestamp, e.g. '09-08-2026 04:15:32 PM IST'."""
    return datetime.now(IST).strftime("%d-%m-%Y %I:%M:%S %p IST")


def success_envelope(data: Any, extra: Optional[dict] = None) -> dict:
    body = {
        "success": True,
        "timestamp": now_ist_str(),
        "data": data,
    }
    if extra:
        body.update(extra)
    return body


def error_envelope(code: str, message: str) -> dict:
    return {
        "success": False,
        "timestamp": now_ist_str(),
        "error": {
            "code": code,
            "message": message,
        },
    }


class RailAPIError(Exception):
    """Base class for all handled application errors."""
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, code: Optional[str] = None, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class InvalidParameterError(RailAPIError):
    status_code = 400
    code = "INVALID_PARAMETER"


class InvalidDateError(RailAPIError):
    status_code = 400
    code = "INVALID_DATE"


class NotFoundError(RailAPIError):
    status_code = 404
    code = "NOT_FOUND"


class TrainNotFoundError(NotFoundError):
    code = "TRAIN_NOT_FOUND"


class StationNotFoundError(NotFoundError):
    code = "STATION_NOT_FOUND"


class NoTrainsFoundError(NotFoundError):
    code = "NO_TRAINS_FOUND"


class UpstreamTimeoutError(RailAPIError):
    status_code = 504
    code = "UPSTREAM_TIMEOUT"


class UpstreamHTTPError(RailAPIError):
    status_code = 502
    code = "UPSTREAM_HTTP_ERROR"


class UpstreamUnavailableError(RailAPIError):
    status_code = 503
    code = "UPSTREAM_UNAVAILABLE"


class EmptyResponseError(RailAPIError):
    status_code = 502
    code = "EMPTY_UPSTREAM_RESPONSE"


class MalformedResponseError(RailAPIError):
    status_code = 502
    code = "MALFORMED_UPSTREAM_RESPONSE"


class ParserError(RailAPIError):
    status_code = 502
    code = "PARSER_ERROR"


class PNRError(RailAPIError):
    status_code = 502
    code = "PNR_ERROR"


class CaptchaError(RailAPIError):
    status_code = 502
    code = "CAPTCHA_ERROR"


class RateLimitExceededError(RailAPIError):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"


class ExternalAPIAuthError(RailAPIError):
    """Raised when a configured external API (e.g. RailRadar) rejects our API key."""
    status_code = 502
    code = "EXTERNAL_API_AUTH_ERROR"


class ExternalAPIRateLimitError(RailAPIError):
    """Raised when an external API's OWN rate limit is hit (distinct from our
    own RateLimitExceededError, which is about OUR clients hitting US)."""
    status_code = 429
    code = "EXTERNAL_API_RATE_LIMIT"


class ExternalAPINotConfiguredError(RailAPIError):
    """Raised when a feature needs an external API key that isn't set."""
    status_code = 501
    code = "EXTERNAL_API_NOT_CONFIGURED"
