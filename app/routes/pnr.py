from fastapi import APIRouter, Query

from app.config import settings
from app.services import pnr_confirmtkt, pnr_captcha, pnr_lostingness
from app.utils.errors import success_envelope, InvalidParameterError, PNRError

router = APIRouter(prefix="/api", tags=["pnr"])

_VALID_SOURCES = ("confirmtkt", "indianrail", "lostingness")


@router.get("/pnr/{pnr}")
async def get_pnr(
    pnr: str,
    source: str = Query(
        None,
        description=(
            "Which upstream source to use: 'confirmtkt' (default, no CAPTCHA, "
            "reasonably reliable), 'indianrail' (legacy CAPTCHA-OCR based, "
            "best-effort, may be unavailable in this deployment — see README "
            "Phase 9 notes), or 'lostingness' (community-found third-party "
            "endpoint — UNOFFICIAL, UNVERIFIED, uses a shared token, may "
            "disappear without notice; see app/services/pnr_lostingness.py)."
        ),
    ),
):
    """PNR status lookup. See app/parsers/pnr_parser.py and
    app/services/pnr_lostingness.py for source details.

    These are THREE INDEPENDENT unofficial sources (not the same upstream),
    so unlike the erail.in endpoints there is no shared-raw-response
    scenario to combine — each source needs its own request.
    """
    if not pnr or len(pnr) != 10 or not pnr.isdigit():
        raise InvalidParameterError("PNR must be exactly 10 digits.")

    chosen = (source or settings.PNR_DEFAULT_SOURCE).strip().lower()
    if chosen not in _VALID_SOURCES:
        raise InvalidParameterError(f"source must be one of: {', '.join(_VALID_SOURCES)}.")

    if chosen == "confirmtkt":
        data = await pnr_confirmtkt.get_pnr_status(pnr)
    elif chosen == "lostingness":
        try:
            data = await pnr_lostingness.get_pnr_status(pnr)
        except PNRError:
            raise
        except Exception as exc:  # noqa: BLE001 - this path must never crash the server
            raise PNRError(
                f"lostingness PNR lookup failed: {exc}"
            ) from exc
    else:
        try:
            data = await pnr_captcha.get_pnr_status_legacy(pnr)
        except PNRError:
            raise
        except Exception as exc:  # noqa: BLE001 - this path must never crash the server
            raise PNRError(
                f"Legacy indianrail.gov.in PNR lookup failed: {exc}"
            ) from exc

    return success_envelope(data, {"source": chosen})
