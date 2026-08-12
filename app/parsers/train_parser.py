"""
Unified parser for erail.in's `getTrains.aspx` responses.

Both original projects hit the SAME upstream endpoint for this data:
  * Python RailIN: getAllTrains() / getTrain()  -> Prettify.TrainsToJson/MakeSenseTrain
  * JS project:     /betweenStations / /getTrain -> Prettify.BetweenStation/CheckTrain

Per the "one request, multiple parsers" requirement, this module makes NO
network calls itself — it is handed the raw upstream text once (by
app/services/erail.py) and produces a single, unified, field-complete
result. It also exposes "legacy" reconstructions of each original
project's reduced output, purely by re-slicing the SAME raw text, for
callers that pass `?include=result1,result2`.

Field provenance
-----------------
* train_base.* (train_no ... running_days)   -> both projects (identical)
* coach_types (1A/2A/3A/CC/SL/2S/GN)          -> Python only (JS never parsed these)
* source_depart, dstn_reach                    -> Python only
* type, train_id, distance_from_to,
  average_speed                                -> both, but JS only exposed these
                                                   from the single-train endpoint
                                                   (CheckTrain), not the between-
                                                   stations list (BetweenStation)
* notif_coach, train_type, region, rake_share,
  coach_arrangement                            -> Python only (heuristic `_extract`)

The unified parser always extracts the full superset above, for BOTH the
single-train and between-stations upstream responses, since both are
produced by the same upstream template. Nothing from either project is
dropped.
"""
import re
from typing import Any, Optional

from app.utils.errors import (
    NoTrainsFoundError,
    StationNotFoundError,
    TrainNotFoundError,
    UpstreamUnavailableError,
    MalformedResponseError,
)

RECORD_SEP = "~~~~~~~~"

# Known upstream "soft error" strings observed in both original projects.
_KNOWN_ERRORS = {
    "Please try again after some time.": UpstreamUnavailableError,
    "From station not found": StationNotFoundError,
    "To station not found": StationNotFoundError,
    "Train not found": TrainNotFoundError,
}


def _strip_leading_tildes(s: str) -> str:
    return s.lstrip("~")


def detect_known_errors(raw: str) -> None:
    """Raise a clean, typed error for well-known upstream error strings.

    erail.in returns these as plain-text sentinel responses instead of a
    proper HTTP error code or structured payload. Both original projects
    had partial, inconsistent handling for this (JS checked more cases than
    Python, which had none). We check all known cases up front so the rest
    of the parser never has to deal with garbage input for these cases.
    """
    if raw is None:
        raise MalformedResponseError("Upstream returned no content.")

    stripped = raw.strip()
    for needle, exc_cls in _KNOWN_ERRORS.items():
        if stripped == f"~~~~~{needle}" or stripped == needle or stripped.startswith(needle):
            raise exc_cls(f"Upstream reported: {needle}")

    # "No direct trains found" is embedded mid-record, wrapped in HTML, in the
    # between-stations response (discovered in the JS project's BetweenStation).
    if "No direct trains found" in raw:
        raise NoTrainsFoundError("No direct trains found between the given stations.")

    if stripped == "" or stripped == "^":
        raise NoTrainsFoundError("Upstream returned no train data for this query.")


def _extract_heuristic(segment: str) -> Optional[tuple]:
    """Port of Python RailIN's Prettify._extract heuristic.

    erail.in packs an inconsistent, loosely-typed set of "extra" fields
    (train type, zone/region, rake sharing, coach arrangement, notices)
    into further `~~`-delimited segments. There's no reliable field index
    for these — the ORIGINAL author's heuristic (checked casing, digits,
    presence of ':' etc.) is preserved as-is since it's the only known
    mapping and it degrades gracefully (returns None) when it doesn't
    recognise a segment, rather than throwing.
    """
    val = segment.strip("~")
    parts = val.split("~")
    length = len(parts)

    if length == 1:
        if parts[0] == "":
            return None
        words = len(parts[0].split())
        if words > 3:
            return "notif", parts[0]
        if (
            all((c.isalpha()) or (c == "&") or (c == " ") for c in parts[0])
            and words < 4
            and parts[0] != "BG"
        ):
            return "train_type", parts[0]
        return None

    if length >= 2:
        p1 = parts[1]
        if (
            all((c.isalpha()) or (c == "&") or (c == " ") for c in p1)
            and len(p1.split()) < 4
            and p1 != "BG"
            and len(p1) > 4
        ):
            words_ = [w for w in p1.split() if len(w) > 1]
            if all(w[0].isupper() and all(c.islower() for c in w[1:]) for w in words_):
                return "train_type", p1
        if all(c.isalpha() and c.isupper() for c in p1) and p1 != "":
            return "region", p1
        if p1 != "" and all((c.isdigit()) or (c == ",") for c in p1):
            return "rake_share", p1.split(",")
        if ":" in p1:
            coach = []
            data = p1.strip(":").split(":")
            for i, d in enumerate(data):
                f = d.split(",")
                if len(f) >= 3:
                    coach.append({str(i + 1): {"tag": f[0], "coach_id": f[1], "type": f[2]}})
            if coach:
                return "coach_arrangement", coach
    return None


def _parse_one_record(record: str) -> Optional[dict[str, Any]]:
    """Parse a single `^`-delimited train record (Python MakeSenseTrain, extended)."""
    if not record.strip("~"):
        return None

    parts = record.split(RECORD_SEP)
    base_fields = parts[0].split("~")
    if len(base_fields) < 14:
        # Not enough fields to be a real train_base record — skip rather than crash.
        return None

    train_base: dict[str, Any] = {
        "train_no": base_fields[0] or None,
        "train_name": base_fields[1] or None,
        "source_stn_name": base_fields[2] or None,
        "source_stn_code": base_fields[3] or None,
        "dstn_stn_name": base_fields[4] or None,
        "dstn_stn_code": base_fields[5] or None,
        "from_stn_name": base_fields[6] or None,
        "from_stn_code": base_fields[7] or None,
        "to_stn_name": base_fields[8] or None,
        "to_stn_code": base_fields[9] or None,
        "from_time": base_fields[10] or None,
        "to_time": base_fields[11] or None,
        "travel_time": base_fields[12] or None,
        "running_days": base_fields[13] or None,
    }

    result: dict[str, Any] = {"train_base": train_base}

    if len(parts) < 2 or not parts[1]:
        return result

    data2 = parts[1].split("~~")
    data2_1 = data2[0].split("~") if data2 else []

    # Coach type availability flags, packed as single characters in data2_1[0].
    if data2_1 and len(data2_1[0]) >= 9:
        flags = data2_1[0]
        result["coach_types"] = {
            "1A": flags[0],
            "2A": flags[1],
            "3A": flags[2],
            "CC": flags[3],
            "SL": flags[5],
            "2S": flags[6],
            "GN": flags[8],
        }

    def _safe_get(lst, idx):
        return lst[idx] if idx < len(lst) and lst[idx] != "" else None

    if len(data2_1) > 19:
        train_base["source_depart"] = _safe_get(data2_1, 5)
        train_base["dstn_reach"] = _safe_get(data2_1, 6)
        train_base["type"] = _safe_get(data2_1, 11)
        train_base["train_id"] = _safe_get(data2_1, 12)
        train_base["distance_from_to"] = _safe_get(data2_1, 18)
        train_base["average_speed"] = _safe_get(data2_1, 19)

    # Segment 1: coach notification, if present.
    if len(data2) > 1:
        notif_parts = data2[1].split("~")
        if len(notif_parts) > 3 and notif_parts[3]:
            train_base["notif_coach"] = notif_parts[3]

    # Segments 2..6: train type / region / rake share / coach arrangement (heuristic).
    for i in range(2, min(7, len(data2))):
        seg = data2[i]
        if not seg:
            continue
        extracted = _extract_heuristic(seg)
        if extracted:
            key, value = extracted
            result[key] = value

    return result


def parse_trains_raw(raw: str) -> list[dict[str, Any]]:
    """Full, unified parse of a getTrains.aspx response. Returns a list of train dicts."""
    detect_known_errors(raw)

    records = raw.split("^")
    # The first chunk (before the first '^') is boilerplate/empty, matching the
    # original Python implementation's documented behaviour ("data[0] is useless").
    trains = []
    for record in records[1:]:
        parsed = _parse_one_record(record)
        if parsed:
            trains.append(parsed)

    if not trains:
        raise NoTrainsFoundError("No trains found for this query.")
    return trains


def parse_single_train(raw: str) -> dict[str, Any]:
    """Parse a getTrains.aspx?TrainNo=... response into a single unified train dict."""
    trains = parse_trains_raw(raw)
    return trains[0]


# ---------------------------------------------------------------------------
# Legacy reconstructions (for ?include=result1,result2), built from the SAME
# raw text — no extra upstream request is made for these.
# ---------------------------------------------------------------------------

def legacy_python_result(raw: str) -> list[dict[str, Any]]:
    """Reconstructs what the original Python `TrainsToJson` would have returned."""
    return parse_trains_raw(raw)


def legacy_js_between_stations(raw: str) -> dict[str, Any]:
    """Reconstructs the original JS `BetweenStation` output shape (train_base only,
    no coach_types/type/train_id/distance/speed — JS never extracted those for lists)."""
    try:
        detect_known_errors(raw)
    except (NoTrainsFoundError, StationNotFoundError, UpstreamUnavailableError) as exc:
        return {"success": False, "data": str(exc)}

    trains = parse_trains_raw(raw)
    reduced = []
    for t in trains:
        base = dict(t.get("train_base", {}))
        # JS's BetweenStation only ever populated these 14 keys.
        keys = [
            "train_no", "train_name", "source_stn_name", "source_stn_code",
            "dstn_stn_name", "dstn_stn_code", "from_stn_name", "from_stn_code",
            "to_stn_name", "to_stn_code", "from_time", "to_time", "travel_time",
            "running_days",
        ]
        reduced.append({"train_base": {k: base.get(k) for k in keys}})
    return {"success": True, "data": reduced}


def legacy_js_check_train(raw: str) -> dict[str, Any]:
    """Reconstructs the original JS `CheckTrain` output shape (flat dict, subset of fields)."""
    try:
        detect_known_errors(raw)
    except (TrainNotFoundError, UpstreamUnavailableError) as exc:
        return {"success": False, "data": str(exc)}

    train = parse_single_train(raw)
    base = train.get("train_base", {})
    flat = {
        "train_no": base.get("train_no"),
        "train_name": base.get("train_name"),
        "from_stn_name": base.get("from_stn_name"),
        "from_stn_code": base.get("from_stn_code"),
        "to_stn_name": base.get("to_stn_name"),
        "to_stn_code": base.get("to_stn_code"),
        "from_time": base.get("from_time"),
        "to_time": base.get("to_time"),
        "travel_time": base.get("travel_time"),
        "running_days": base.get("running_days"),
        "type": base.get("type"),
        "train_id": base.get("train_id"),
        "distance_from_to": base.get("distance_from_to"),
        "average_speed": base.get("average_speed"),
    }
    return {"success": True, "data": flat}
