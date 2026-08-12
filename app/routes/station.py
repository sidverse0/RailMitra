from fastapi import APIRouter

from app.config import settings
from app.services import erail
from app.parsers import station_parser
from app.utils.cache import get_or_set
from app.utils.errors import success_envelope, InvalidParameterError

router = APIRouter(prefix="/api", tags=["station"])


@router.get("/station-live/{station_code}")
async def get_station_live(station_code: str):
    """Trains currently live/expected at a station. Source: erail.in/station-live/{code}
    (JS-only feature originally scraped with cheerio; ported to BeautifulSoup here).

    NOTE: intentionally kept on the legacy scrape only (not RailRadar) — this
    endpoint is expected to be hit frequently, and RailRadar's free tier is
    only 50 requests/day. RailRadar is reserved for /api/status (live train
    status), which is the endpoint that actually needed it. See
    app/services/railradar.py if you want to wire this endpoint to RailRadar
    later (RailRadar's GET /v1/stations/{code}/live already supports it).
    """
    if not station_code or not station_code.strip():
        raise InvalidParameterError("station_code is required.")
    code = station_code.strip().upper()

    cache_key = f"station_live:{code}"
    html = await get_or_set(
        cache_key,
        settings.CACHE_TTL_STATION_LIVE_SECONDS,
        lambda: erail.fetch_station_live(code),
    )
    data = station_parser.parse_station_live_html(html)
    return success_envelope(data)
