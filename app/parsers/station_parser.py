"""
Station-live parser for `erail.in/station-live/{code}`.

This feature exists ONLY in the JS project (`stationLive` / `LiveStation`,
which used cheerio). Ported here to BeautifulSoup against the same page
structure (elements with class `.name` inside a table row, each followed by
a sibling div containing "SOURCE → DESTINATION" and a sibling `<td>` with
the scheduled/actual time and status detail).
"""
from typing import Any

from bs4 import BeautifulSoup

from app.utils.errors import MalformedResponseError, NotFoundError


def parse_station_live_html(html: str) -> list[dict[str, Any]]:
    if not html or not html.strip():
        raise MalformedResponseError("Upstream returned an empty station-live response.")

    soup = BeautifulSoup(html, "lxml")
    name_elements = soup.select(".name")

    trains = []
    for el in name_elements:
        text = el.get_text(strip=True)
        train_no = text[:5] if len(text) >= 5 else None
        train_name = text[5:].strip() if len(text) > 5 else None

        source_name = dest_name = None
        sibling_div = el.find_next_sibling("div")
        if sibling_div:
            route_text = sibling_div.get_text(strip=True)
            if "→" in route_text:
                left, _, right = route_text.partition("→")
                source_name = left.strip() or None
                dest_name = right.strip() or None

        time_at = detail = None
        parent_td = el.find_parent("td")
        if parent_td:
            next_td = parent_td.find_next_sibling("td")
            if next_td:
                td_text = next_td.get_text(strip=True)
                time_at = td_text[:5] if len(td_text) >= 5 else (td_text or None)
                detail = td_text[5:].strip() if len(td_text) > 5 else None

        trains.append(
            {
                "train_no": train_no,
                "train_name": train_name,
                "source_stn_name": source_name,
                "dstn_stn_name": dest_name,
                "time_at": time_at,
                "detail": detail,
            }
        )

    if not trains:
        raise NotFoundError(
            "No live train data found for this station.", code="STATION_LIVE_NOT_FOUND"
        )
    return trains
