"""
Fare parser for erail.in `data.aspx?Action=GetTrainFare`.

This feature exists ONLY in the original Python RailIN project (`getFare` /
`FareToJson`) — the JS project has no equivalent endpoint. Ported here with
added defensive handling so a change in the upstream HTML table structure
raises a clean MalformedResponseError instead of an IndexError.
"""
from typing import Any

from bs4 import BeautifulSoup

from app.utils.errors import MalformedResponseError


def parse_fare_html(html: str) -> dict[str, dict[str, Any]]:
    if not html or not html.strip():
        raise MalformedResponseError("Upstream returned an empty fare response.")

    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all(
        "table", {"class": "tableSingleFare table table-bordered table-condensed"}
    )
    if len(tables) < 2:
        raise MalformedResponseError(
            "Could not locate the fare table in the upstream response "
            "(the upstream page layout may have changed)."
        )

    fare_table = tables[1]
    rows = fare_table.find_all("tr")
    if len(rows) < 2:
        raise MalformedResponseError("Fare table has no data rows.")

    header_cells = rows[0].find_all(["td", "th"])[1:]
    fare_types = [c.get_text(strip=True) for c in header_cells]

    result: dict[str, dict[str, Any]] = {}
    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue
        class_name = cells[0].get_text(strip=True)
        result[class_name] = {}
        for fare_type, cell in zip(fare_types, cells[1:]):
            text = cell.get_text(strip=True)
            if text and text != "-" and cell.find("b"):
                result[class_name][fare_type] = cell.find("b").get_text(strip=True)
            else:
                result[class_name][fare_type] = text or "-"

    if not result:
        raise MalformedResponseError("Fare table parsed but produced no rows.")
    return result
