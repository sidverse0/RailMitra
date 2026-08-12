"""
RailRadar API integration (https://railradar.in/docs).

Used as the PRIMARY source for:
  * live train running status  (was: data.tripmgt.com — often unreliable)
  * station live board          (was: erail.in/station-live scrape — often unreliable)

RailRadar has NO endpoint for PNR status or seat/berth availability, so
those two features are intentionally NOT touched here — they remain on
their original sources (see app/services/pnr_confirmtkt.py,
app/services/pnr_captcha.py, app/parsers/availability_parser.py).

Auth: `Authorization: Bearer <RAILRADAR_API_KEY>` on every request.
Free tier is 50 requests/day (10/min burst) — see CACHE_TTL_STATUS_SECONDS
and CACHE_TTL_STATION_LIVE_SECONDS in app/config.py, which are set high on
purpose to conserve quota.

Every call here returns RailRadar's `data` object AS-IS (no reshaping) —
its schema is materially richer than either original project's status
output (per-stop delay, live position, diversion/cancellation exceptions,
etc.), so flattening it down to the old shape would throw away useful
information. The route layer (app/routes/status.py,
app/routes/station.py) exposes it under the same `data` envelope key,
just with a fuller shape than before.
"""
from typing import Any, Optional

from app.config import settings
from app.utils.http import fetch_json
from app.utils.errors import (
    ExternalAPIAuthError,
    ExternalAPIRateLimitError,
    ExternalAPINotConfiguredError,
    TrainNotFoundError,
    StationNotFoundError,
    InvalidParameterError,
    UpstreamUnavailableError,
    UpstreamHTTPError,
)


def _auth_headers() -> dict:
    if not settings.RAILRADAR_API_KEY:
        raise ExternalAPINotConfiguredError(
            "RailRadar is not configured (RAILRADAR_API_KEY is not set). "
            "Set the env var, or call this endpoint with ?source=legacy."
        )
    return {"Authorization": f"Bearer {settings.RAILRADAR_API_KEY}"}


def _raise_for_error(status_code: int, body: dict, not_found_cls=None):
    """Maps RailRadar's own error envelope/status codes onto our exception hierarchy."""
    not_found_cls = not_found_cls or TrainNotFoundError
    err = (body or {}).get("error") or {}
    message = err.get("message") or f"RailRadar returned HTTP {status_code}."

    if status_code == 400:
        raise InvalidParameterError(message)
    if status_code == 401:
        raise ExternalAPIAuthError(f"RailRadar rejected the API key: {message}")
    if status_code == 404:
        raise not_found_cls(message)
    if status_code == 429:
        raise ExternalAPIRateLimitError(
            f"RailRadar rate limit exceeded (free tier is 50 requests/day): {message}"
        )
    if status_code == 503:
        raise UpstreamUnavailableError(f"RailRadar upstream data source is down: {message}")
    raise UpstreamHTTPError(f"RailRadar returned HTTP {status_code}: {message}")


async def fetch_live_status(
    train_no: str,
    date: Optional[str] = None,
    halts_only: Optional[bool] = None,
    geometry: Optional[bool] = None,
    fmt: Optional[str] = None,
    include_coordinates: Optional[bool] = None,
) -> dict[str, Any]:
    """GET /v1/trains/{number}/live"""
    url = settings.RAILRADAR_LIVE_STATUS_URL.format(number=train_no)
    params: dict[str, Any] = {}
    if date:
        params["date"] = date
    if halts_only is not None:
        params["haltsOnly"] = str(halts_only).lower()
    if geometry is not None:
        params["geometry"] = str(geometry).lower()
    if fmt:
        params["format"] = fmt
    if include_coordinates is not None:
        params["includeCoordinates"] = str(include_coordinates).lower()

    status_code, body = await fetch_json(url, params=params, headers=_auth_headers())
    if status_code != 200 or not body.get("success"):
        _raise_for_error(status_code, body, not_found_cls=TrainNotFoundError)
    return body["data"]


async def fetch_station_live_board(
    station_code: str,
    hours: Optional[int] = None,
    include_intermediate: Optional[bool] = None,
) -> dict[str, Any]:
    """GET /v1/stations/{code}/live"""
    url = settings.RAILRADAR_STATION_LIVE_URL.format(code=station_code)
    params: dict[str, Any] = {}
    if hours is not None:
        params["hours"] = hours
    if include_intermediate is not None:
        params["includeIntermediate"] = str(include_intermediate).lower()

    status_code, body = await fetch_json(url, params=params, headers=_auth_headers())
    if status_code != 200 or not body.get("success"):
        _raise_for_error(status_code, body, not_found_cls=StationNotFoundError)
    return body["data"]
