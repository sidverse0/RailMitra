"""
Train running-status / delay service.

Feature exists only in the original Python RailIN project (`getStatus`),
sourced from data.tripmgt.com. The upstream already returns JSON, so no
custom parser module is needed — we just validate and pass it through.
"""
import json

from app.config import settings
from app.utils.http import fetch_text
from app.utils.errors import MalformedResponseError


async def fetch_status_raw(train_no: str, station_code: str) -> str:
    return await fetch_text(
        settings.TRIPMGT_STATUS_URL,
        params={"Action": "TRAIN_STATION_DELAYS", "Data1": train_no, "Data2": station_code},
    )


def parse_status(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MalformedResponseError(
            f"Upstream train-status response was not valid JSON: {exc}"
        ) from exc
