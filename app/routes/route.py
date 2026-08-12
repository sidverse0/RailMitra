from fastapi import APIRouter

from app.config import settings
from app.services import erail
from app.parsers import train_parser, route_parser
from app.utils.cache import get_or_set
from app.utils.errors import success_envelope, InvalidParameterError

router = APIRouter(prefix="/api", tags=["route"])


@router.get("/route/{train_no}")
async def get_route(train_no: str):
    """Full station-by-station route for a train.

    Both original projects implement this as a genuine TWO-request chain
    against TWO different upstream URLs (first resolve the train's internal
    numeric `train_id`, then fetch its route using that id) — this is not a
    duplicate-parse situation, so both requests are necessary and kept.
    """
    if not train_no or not train_no.strip().isdigit():
        raise InvalidParameterError("train_no must be numeric, e.g. /api/route/12951")

    train_raw = await get_or_set(
        f"train:{train_no}",
        settings.CACHE_TTL_TRAIN_SECONDS,
        lambda: erail.fetch_train_by_number(train_no),
    )
    train = train_parser.parse_single_train(train_raw)
    train_id = train.get("train_base", {}).get("train_id")
    if not train_id:
        train_id = train_no  # best-effort fallback, matches original Python behaviour

    route_raw = await get_or_set(
        f"route:{train_id}",
        settings.CACHE_TTL_ROUTE_SECONDS,
        lambda: erail.fetch_route(train_id),
    )
    stations = route_parser.parse_route_raw(route_raw)

    return success_envelope(
        {
            "train_no": train.get("train_base", {}).get("train_no"),
            "train_name": train.get("train_base", {}).get("train_name"),
            "train_id": train_id,
            "stations": stations,
        }
    )
