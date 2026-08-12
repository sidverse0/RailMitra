from fastapi import APIRouter, Query

from app.config import settings
from app.services import erail
from app.parsers import fare_parser
from app.utils.cache import get_or_set
from app.utils.errors import success_envelope, InvalidParameterError

router = APIRouter(prefix="/api", tags=["fare"])


@router.get("/fare")
async def get_fare(
    train_no: str = Query(..., description="Train number, e.g. 12951"),
    from_: str = Query(..., alias="from", description="Origin station code"),
    to: str = Query(..., description="Destination station code"),
):
    """Fare by class. Source: erail.in data.aspx?Action=GetTrainFare (Python-only feature)."""
    if not train_no.strip().isdigit():
        raise InvalidParameterError("train_no must be numeric.")
    from_code = from_.strip().upper()
    to_code = to.strip().upper()

    cache_key = f"fare:{train_no}:{from_code}:{to_code}"
    html = await get_or_set(
        cache_key,
        settings.CACHE_TTL_FARE_SECONDS,
        lambda: erail.fetch_fare(train_no, from_code, to_code),
    )
    data = fare_parser.parse_fare_html(html)
    return success_envelope(data)
