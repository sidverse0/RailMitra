"""
PNR status via a paid third-party endpoint (my.lostingness.site/encore.php).

Confirmed working against a real PNR by the person integrating this — the
service appears to be a proxy/wrapper around ConfirmTkt's own internal PNR
API (the response schema — `pnrResponse`, `showBlaBlaAd`, `flightBannerUrl`
pointing at `cdn.confirmtkt.com`, etc. — matches ConfirmTkt's own app
response shape, not a from-scratch schema).

Response shape (confirmed from a live call):
    {
      "data": {
        "ctProResponse": null,
        "pnrResponse": {
          "pnr": ..., "trainNo": ..., "trainName": ..., "doj": ...,
          "from": ..., "to": ..., "class": ..., "chartPrepared": ...,
          "passengerStatus": ..., "error": <str|null>, "errorCode": <int>,
          ... (many more fields — see below)
        }
      }
    }

IMPORTANT: `pnrResponse` is present even on a FAILED lookup — it just comes
back with every field `null` and `error`/`errorCode` populated (e.g.
`errorCode: 201, error: "Flushed PNR /PNR not yet generated"` for a PNR
that doesn't exist / hasn't been generated / is stale). A naive
`if response: return response` would silently return an all-null blob as
if it were a successful lookup — this module explicitly checks
`errorCode`/`error` and raises a proper PNRError instead.

Still worth noting even though this is now the default and confirmed
working: it's a third-party proxy with a token that was shared in plain
text rather than looked up from a per-account dashboard. If it ever stops
working, override `LOSTINGNESS_API_KEY` / `LOSTINGNESS_PNR_URL` via env
vars, or switch `PNR_DEFAULT_SOURCE` back to `confirmtkt`/`indianrail`, or
per-request via `?source=`.
"""
from typing import Any

from app.config import settings
from app.utils.http import post_json
from app.utils.errors import (
    PNRError,
    InvalidParameterError,
    ExternalAPIAuthError,
    UpstreamUnavailableError,
    UpstreamHTTPError,
    NotFoundError,
    MalformedResponseError,
)

# errorCode values observed/expected to mean "this PNR genuinely has no
# data" rather than "the service is broken" — mapped to a 404-style
# NotFoundError instead of a 502-style PNRError.
_NOT_FOUND_ERROR_CODES = {201}


async def get_pnr_status(pnr: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {settings.LOSTINGNESS_API_KEY}"}
    status_code, body = await post_json(
        settings.LOSTINGNESS_PNR_URL, json_body={"pnr": pnr}, headers=headers
    )

    if status_code == 400:
        raise InvalidParameterError(
            body.get("message", "Invalid PNR or request.") if isinstance(body, dict) else "Invalid PNR or request."
        )
    if status_code in (401, 403):
        raise ExternalAPIAuthError(
            "lostingness PNR source rejected the bearer token."
        )
    if status_code == 429:
        raise UpstreamUnavailableError("lostingness PNR source rate-limited this request.")
    if status_code >= 500:
        raise UpstreamUnavailableError(f"lostingness PNR source returned HTTP {status_code}.")
    if status_code != 200:
        raise UpstreamHTTPError(f"lostingness PNR source returned unexpected HTTP {status_code}.")

    if not body or not isinstance(body, dict):
        raise MalformedResponseError("lostingness PNR source returned an empty/unparseable response.")

    pnr_response = (body.get("data") or {}).get("pnrResponse")
    if pnr_response is None:
        raise MalformedResponseError(
            "lostingness PNR source response did not contain the expected "
            "'data.pnrResponse' field (the API shape may have changed)."
        )

    error_code = pnr_response.get("errorCode")
    error_message = pnr_response.get("error")

    # errorCode 0 (or absent) with no error message = genuine success.
    if error_code and error_code != 0:
        if error_code in _NOT_FOUND_ERROR_CODES or pnr_response.get("pnr") is None:
            raise NotFoundError(
                error_message or f"PNR not found (errorCode {error_code}).",
                code="PNR_NOT_FOUND",
            )
        raise PNRError(error_message or f"lostingness PNR source reported errorCode {error_code}.")

    if error_message:
        # errorCode absent/0 but an error string is still present — treat as failure defensively.
        raise PNRError(error_message)

    return pnr_response
