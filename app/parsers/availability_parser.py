"""
Seat/berth availability parser for `d.erail.in/AVL_Request`.

Feature exists only in the original Python RailIN project (`getAvailability`
/ `AvailToJson`). The JS project has no equivalent endpoint.
"""
from typing import Any

from app.utils.errors import MalformedResponseError


def parse_availability_raw(raw: str) -> dict[str, Any]:
    if raw is None or raw.strip() == "":
        raise MalformedResponseError("Upstream returned an empty availability response.")

    string_arr = raw.split("~")[1:]
    if not string_arr:
        raise MalformedResponseError("Unexpected availability response format.")

    if ")" in string_arr[0]:
        return {"status": "No Results Found", "raw": string_arr[0]}

    data = string_arr[0].split("^")
    if not data or "_" not in data[0]:
        raise MalformedResponseError("Unexpected availability response format.")

    head = data[0].split("_")
    if len(head) < 5:
        raise MalformedResponseError("Unexpected availability response format.")

    return {
        "train_no": head[0] or None,
        "from_code": head[1] or None,
        "to_code": head[2] or None,
        "class": head[3] or None,
        "date": head[4] or None,
        "status": data[1] if len(data) > 1 else None,
    }
