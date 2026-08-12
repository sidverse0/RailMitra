import logging

from fastapi import APIRouter, Query

from app.config import settings
from app.services import status as status_service
from app.services import railradar
from app.utils.cache import get_or_set
from app.utils.errors import (
    success_envelope,
    InvalidParameterError,
    ExternalAPIAuthError,
    ExternalAPIRateLimitError,
    ExternalAPINotConfiguredError,
    UpstreamUnavailableError,
    UpstreamHTTPError,
    UpstreamTimeoutError,
    EmptyResponseError,
    MalformedResponseError,
)

router = APIRouter(prefix="/api", tags=["status"])
logger = logging.getLogger("railway_api")

# Infra-type failures worth silently falling back to the legacy source for,
# when the caller didn't pin an explicit `source`. NOT included:
# TrainNotFoundError/InvalidParameterError — those describe the query
# itself, not a source outage, so retrying against the other source
# wouldn't make sense.
_FALLBACK_TRIGGERS = (
    ExternalAPIAuthError,
    ExternalAPIRateLimitError,
    ExternalAPINotConfiguredError,
    UpstreamUnavailableError,
    UpstreamHTTPError,
    UpstreamTimeoutError,
    EmptyResponseError,
    MalformedResponseError,
)


@router.get("/status")
async def get_status(
    train_no: str = Query(..., description="Train number, e.g. 12951"),
    station: str = Query(
        None,
        description="Legacy-source-only: station code to check delay/status at.",
    ),
    date: str = Query(None, description="RailRadar-only: journey date YYYY-MM-DD. Omit to auto-detect."),
    source: str = Query(
        None,
        description=(
            "Which source to use: 'railradar' (default, real-time position/delay/"
            "per-stop status, richer) or 'legacy' (data.tripmgt.com passthrough). "
            "If omitted, RailRadar is tried first and this endpoint falls back to "
            "'legacy' automatically on auth/quota/outage errors."
        ),
    ),
):
    """Train running status/delay.

    Default source is RailRadar (GET /v1/trains/{no}/live) — richer live
    position, delay, and per-stop data than the original Python-only
    tripmgt.com passthrough. Falls back to the legacy source automatically
    unless a `source` is explicitly pinned. See app/services/railradar.py.
    """
    if not train_no.strip().isdigit():
        raise InvalidParameterError("train_no must be numeric.")

    chosen = (source or settings.STATUS_SOURCE_DEFAULT).strip().lower()
    if chosen not in ("railradar", "legacy"):
        raise InvalidParameterError("source must be 'railradar' or 'legacy'.")

    auto_fallback_allowed = source is None  # only auto-fallback if caller didn't pin one

    async def _legacy():
        if not station:
            raise InvalidParameterError(
                "The legacy status source requires a 'station' query parameter."
            )
        station_code = station.strip().upper()
        cache_key = f"status:legacy:{train_no}:{station_code}"
        raw = await get_or_set(
            cache_key,
            settings.CACHE_TTL_STATUS_SECONDS,
            lambda: status_service.fetch_status_raw(train_no, station_code),
        )
        return status_service.parse_status(raw), "legacy"

    async def _railradar():
        cache_key = f"status:railradar:{train_no}:{date or 'auto'}"
        data = await get_or_set(
            cache_key,
            settings.CACHE_TTL_STATUS_SECONDS,
            lambda: railradar.fetch_live_status(train_no, date=date),
        )
        return data, "railradar"

    if chosen == "legacy":
        data, used_source = await _legacy()
    else:
        try:
            data, used_source = await _railradar()
        except _FALLBACK_TRIGGERS as exc:
            if not auto_fallback_allowed or not station:
                raise
            logger.warning("RailRadar status lookup failed (%s), falling back to legacy.", exc)
            data, used_source = await _legacy()

    return success_envelope(data, {"source": used_source})
