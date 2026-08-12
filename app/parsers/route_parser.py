"""
Unified parser for erail.in's `data.aspx?Action=TRAINROUTE` response.

Both original projects hit the same upstream URL for this:
  * Python RailIN: Prettify.StationToJson / MakeSenseStation
  * JS project:     Prettify.GetRoute

Field comparison (see FIELD_MATRIX.md for the full table):
  Python captures 13 fields per station: index, code, name, arrival, depart,
  halt, distance_from_source, day, platform, zone, division, lat, lng.

  JS captures 7: source_stn_code, source_stn_name, arrive, depart, distance,
  day, zone — and does so by FILTERING OUT empty string fields before
  indexing, which shifts field positions whenever an intermediate field is
  blank (e.g. a station with no scheduled halt). Cross-checking indices,
  JS's `zone` (raw index 9 after filtering) does not line up with Python's
  `zone` (raw index 10, no filtering) — the filtering shifts the index. We
  could not reach erail.in from this build environment to verify against a
  live response, so rather than propagate a suspected bug, this module
  adopts Python's fixed-position (non-filtering) indexing as canonical,
  since it does not suffer from the empty-field shift problem, and is a
  strict superset of the fields JS exposed (name==source_stn_name,
  code==source_stn_code, arrival==arrive, distance_from_source==distance).
  This is flagged in FIELD_MATRIX.md so it can be verified/corrected against
  a live response.
"""
from typing import Any

from app.utils.errors import MalformedResponseError, NotFoundError

RECORD_SEP = "^"


def parse_route_raw(raw: str) -> list[dict[str, Any]]:
    if raw is None or raw.strip() == "":
        raise MalformedResponseError("Upstream returned an empty route response.")

    records = raw.split(RECORD_SEP)
    # Skip a leading pipe-delimited header row if present (matches Python's
    # `if '|' in data[0]: start = 1` behaviour).
    start = 1 if "|" in records[0] else 0

    stations = []
    for record in records[start:]:
        fields = record.split("~")
        if len(fields) < 9:
            continue
        station = {
            "index": fields[0] or None,
            "code": fields[1] or None,
            "name": fields[2] or None,
            "arrival": fields[3] or None,
            "depart": fields[4] or None,
            "halt": fields[5] or None,
            "distance_from_source": fields[6] or None,
            "day": fields[7] or None,
            "platform": fields[8] or None,
            "zone": fields[10] if len(fields) > 10 else None,
            "division": fields[11] if len(fields) > 11 else None,
            "lat": fields[14] if len(fields) > 14 else None,
            "lng": fields[15] if len(fields) > 15 else None,
        }
        stations.append(station)

    if not stations:
        raise NotFoundError("No route data found for this train.", code="ROUTE_NOT_FOUND")
    return stations
