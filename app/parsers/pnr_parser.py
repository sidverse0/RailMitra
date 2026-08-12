"""
PNR status parsers.

Two independent upstream sources were used across the two original
projects:

  * ConfirmTkt scraping (JS project, `PnrStatus`): fetches
    confirmtkt.com/pnr-status/{pnr} and regex-extracts an embedded
    `data = {...};` JSON blob from the page's inline script.

  * indianrail.gov.in + CAPTCHA OCR (Python RailIN, `getPNR`): the
    official-ish enquiry endpoint, gated behind an image CAPTCHA that the
    original project solved with pytesseract OCR. See
    app/services/pnr_captcha.py — this path is isolated and best-effort;
    see Phase 9 notes in the README for why it's not the default.

Both are unofficial scrapes and may break without notice if the upstream
site changes its markup/response shape.
"""
import json
import re
from typing import Any

from app.utils.errors import PNRError, MalformedResponseError

_CONFIRMTKT_DATA_PATTERN = re.compile(r"data\s*=\s*(\{.*?\});", re.DOTALL)


def parse_confirmtkt_pnr(html: str) -> dict[str, Any]:
    if not html or not html.strip():
        raise MalformedResponseError("Upstream (ConfirmTkt) returned an empty response.")

    match = _CONFIRMTKT_DATA_PATTERN.search(html)
    if not match:
        raise PNRError(
            "Could not locate PNR data in the ConfirmTkt response "
            "(the upstream page layout may have changed, or the PNR may be invalid/expired)."
        )
    blob = match.group(1)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise PNRError(f"Failed to parse PNR data from ConfirmTkt: {exc}") from exc

    if not data:
        raise PNRError("ConfirmTkt returned no PNR data for this number.")
    return data


def parse_indianrail_pnr(raw_json_text: str) -> dict[str, Any]:
    if not raw_json_text or not raw_json_text.strip():
        raise MalformedResponseError("Upstream (indianrail.gov.in) returned an empty response.")
    try:
        return json.loads(raw_json_text)
    except json.JSONDecodeError as exc:
        raise PNRError(
            f"Failed to parse PNR data from indianrail.gov.in: {exc}"
        ) from exc
