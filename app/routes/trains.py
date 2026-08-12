from typing import Optional

from fastapi import APIRouter, Query

from app.config import settings
from app.services import erail
from app.parsers import train_parser
from app.utils.cache import get_or_set
from app.utils.errors import success_envelope, InvalidParameterError
from app.utils.dates import parse_ddmmyyyy, erail_weekday_index, python_style_weekday_index
from app.routes._shared import parse_include, IncludeQuery

router = APIRouter(prefix="/api", tags=["trains"])


@router.get("/train/{train_no}")
async def get_train(train_no: str, include: Optional[str] = IncludeQuery):
    """Single train info. Source: erail.in getTrains.aspx?TrainNo=...

    Combines Python RailIN's `getTrain`/`MakeSenseTrain` (full field set)
    with the JS project's `/getTrain` (`CheckTrain`) — both hit the same
    upstream URL, so only ONE upstream request is made; both parser
    strategies are then run against that single raw response.
    """
    if not train_no or not train_no.strip().isdigit():
        raise InvalidParameterError("train_no must be numeric, e.g. /api/train/12951")

    included = parse_include(include)
    cache_key = f"train:{train_no}"
    raw = await get_or_set(
        cache_key, settings.CACHE_TTL_TRAIN_SECONDS, lambda: erail.fetch_train_by_number(train_no)
    )

    data = train_parser.parse_single_train(raw)
    extra = {}
    if "result1" in included:
        extra["result1"] = train_parser.legacy_python_result(raw)[0]
    if "result2" in included:
        extra["result2"] = train_parser.legacy_js_check_train(raw)

    return success_envelope(data, extra or None)


@router.get("/trains")
async def get_trains_between(
    from_: str = Query(..., alias="from", description="Origin station code, e.g. NDLS"),
    to: str = Query(..., description="Destination station code, e.g. BCT"),
    include: Optional[str] = IncludeQuery,
):
    """Trains running between two stations. Source: erail.in getTrains.aspx?Station_From&Station_To.

    Both projects hit this same upstream URL (Python `getAllTrains`, JS
    `/betweenStations`) — one upstream request, both parser strategies run
    against the same raw response.
    """
    from_code = from_.strip().upper()
    to_code = to.strip().upper()
    if not from_code or not to_code:
        raise InvalidParameterError("Both 'from' and 'to' station codes are required.")

    included = parse_include(include)
    cache_key = f"trains_between:{from_code}:{to_code}"
    raw = await get_or_set(
        cache_key,
        settings.CACHE_TTL_TRAINS_BETWEEN_SECONDS,
        lambda: erail.fetch_trains_between(from_code, to_code),
    )

    data = train_parser.parse_trains_raw(raw)
    extra = {}
    if "result1" in included:
        extra["result1"] = train_parser.legacy_python_result(raw)
    if "result2" in included:
        extra["result2"] = train_parser.legacy_js_between_stations(raw)

    return success_envelope(data, extra or None)


@router.get("/trains/date")
async def get_trains_on_date(
    from_: str = Query(..., alias="from", description="Origin station code, e.g. NDLS"),
    to: str = Query(..., description="Destination station code, e.g. BCT"),
    date: str = Query(..., description="DD-MM-YYYY"),
    day_index_mode: str = Query(
        "erail",
        description=(
            "Which running_days weekday-index convention to use: 'erail' "
            "(recommended, Wednesday-indexed — reverse engineered from the JS "
            "project) or 'python' (legacy Monday-indexed, from the original "
            "Python RailIN — kept only for comparison). See app/utils/dates.py."
        ),
    ),
    include: Optional[str] = IncludeQuery,
):
    """Trains between two stations that run on a specific date.

    Combines Python RailIN's `getTrainsOn` with the JS project's
    `/getTrainOn` — see app/utils/dates.py for why the two disagreed on the
    running_days weekday index and which convention this endpoint adopts.
    """
    from_code = from_.strip().upper()
    to_code = to.strip().upper()
    parsed_date = parse_ddmmyyyy(date)

    if day_index_mode not in ("erail", "python"):
        raise InvalidParameterError("day_index_mode must be 'erail' or 'python'.")

    day_index = (
        erail_weekday_index(parsed_date)
        if day_index_mode == "erail"
        else python_style_weekday_index(parsed_date)
    )

    included = parse_include(include)
    cache_key = f"trains_between:{from_code}:{to_code}"
    raw = await get_or_set(
        cache_key,
        settings.CACHE_TTL_TRAINS_BETWEEN_SECONDS,
        lambda: erail.fetch_trains_between(from_code, to_code),
    )

    all_trains = train_parser.parse_trains_raw(raw)
    matching = [
        t
        for t in all_trains
        if t.get("train_base", {}).get("running_days")
        and len(t["train_base"]["running_days"]) > day_index
        and t["train_base"]["running_days"][day_index] == "1"
    ]

    extra = {}
    if "result1" in included:
        extra["result1"] = train_parser.legacy_python_result(raw)
    if "result2" in included:
        extra["result2"] = train_parser.legacy_js_between_stations(raw)

    return success_envelope(
        matching,
        {
            **(extra or {}),
            "day_index_mode": day_index_mode,
            "day_index": day_index,
        },
    )
