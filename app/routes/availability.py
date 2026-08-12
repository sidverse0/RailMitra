from fastapi import APIRouter, Query

from app.config import settings
from app.services import erail
from app.parsers import availability_parser
from app.utils.cache import get_or_set
from app.utils.dates import parse_ddmm
from app.utils.errors import success_envelope, InvalidParameterError

router = APIRouter(prefix="/api", tags=["availability"])


@router.get("/availability")
async def get_availability(
    train_no: str = Query(..., description="Train number, e.g. 12951"),
    from_: str = Query(..., alias="from", description="Origin station code"),
    to: str = Query(..., description="Destination station code"),
    travel_class: str = Query(..., alias="class", description="Class code, e.g. SL, 3A, 2A"),
    quota: str = Query("GN", description="Quota code, e.g. GN, TQ, LD"),
    date: str = Query(..., description="DD-MM"),
):
    """Seat/berth availability. Source: d.erail.in/AVL_Request (Python-only feature)."""
    if not train_no.strip().isdigit():
        raise InvalidParameterError("train_no must be numeric.")

    from datetime import date as date_cls

    parsed = parse_ddmm(date, date_cls.today().year)
    dd = f"{parsed.day:02d}"
    mm = f"{parsed.month:02d}"

    from_code = from_.strip().upper()
    to_code = to.strip().upper()
    cls = travel_class.strip().upper()
    qt = quota.strip().upper()

    cache_key = f"avail:{train_no}:{from_code}:{to_code}:{cls}:{qt}:{dd}-{mm}"
    raw = await get_or_set(
        cache_key,
        settings.CACHE_TTL_AVAILABILITY_SECONDS,
        lambda: erail.fetch_availability(train_no, from_code, to_code, cls, qt, dd, mm),
    )
    data = availability_parser.parse_availability_raw(raw)
    return success_envelope(data)
