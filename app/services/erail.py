"""
erail.in service layer.

Each function here makes exactly ONE upstream HTTP request and returns the
raw text/bytes. Parsing is left entirely to app/parsers/* so the same raw
response can be run through multiple parser strategies without any extra
network calls (see train_parser.py's legacy_* helpers).
"""
from app.config import settings
from app.utils.http import fetch_text


async def fetch_train_by_number(train_no: str) -> str:
    return await fetch_text(
        settings.ERAIL_TRAINS_URL,
        params={"TrainNo": train_no, "DataSource": 0, "Language": 0, "Cache": "true"},
    )


async def fetch_trains_between(from_code: str, to_code: str) -> str:
    return await fetch_text(
        settings.ERAIL_TRAINS_URL,
        params={
            "Station_From": from_code,
            "Station_To": to_code,
            "DataSource": 0,
            "Language": 0,
            "Cache": "true",
        },
    )


async def fetch_route(train_id: str) -> str:
    return await fetch_text(
        settings.ERAIL_DATA_URL,
        params={
            "Action": "TRAINROUTE",
            "Password": "2012",
            "Data1": train_id,
            "Data2": 0,
            "Cache": "true",
        },
    )


async def fetch_fare(train_no: str, from_code: str, to_code: str) -> str:
    return await fetch_text(
        settings.ERAIL_DATA_URL,
        params={"Action": "GetTrainFare", "train": train_no, "from": from_code, "to": to_code},
    )


async def fetch_availability(
    train_no: str, from_code: str, to_code: str, travel_class: str, quota: str, dd: str, mm: str
) -> str:
    # This upstream endpoint takes a single pre-joined `Key` query value rather
    # than discrete params (matches both original projects' exact format).
    key = "_".join([str(train_no), from_code, to_code, travel_class, quota, f"{dd}-{mm}"])
    return await fetch_text(settings.ERAIL_AVAILABILITY_URL, params={"Key": key})


async def fetch_station_live(station_code: str) -> str:
    url = settings.ERAIL_STATION_LIVE_URL.format(code=station_code)
    return await fetch_text(
        url, params={"DataSource": 0, "Language": 0, "Cache": "true"}
    )
