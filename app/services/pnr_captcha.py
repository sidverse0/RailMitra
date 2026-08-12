"""
Legacy PNR status via indianrail.gov.in + CAPTCHA OCR.

Ported from the original Python RailIN project (`getPNR` / `CaptchaBreak`).

Per Phase 9 of the audit brief, this is deliberately ISOLATED from the rest
of the API:
  * It depends on Pillow + pytesseract + a system Tesseract OCR binary,
    none of which are required for any other endpoint.
  * `Image.ANTIALIAS` (used by the original code) was removed in Pillow
    10+; this module uses `Image.Resampling.LANCZOS` instead (the direct
    replacement) with a fallback for older Pillow versions.
  * OCR-guessing a CAPTCHA is inherently unreliable and the upstream site
    can change its CAPTCHA scheme at any time without notice.
  * A failure here (missing Tesseract binary, OCR miss, upstream change)
    NEVER propagates as an unhandled exception — every failure mode is
    caught and converted into a `CaptchaError`, and the route layer treats
    this whole source as optional/best-effort (selectable via
    `?source=indianrail`, default is the more reliable ConfirmTkt source).

Documented limitation: this path is unofficial, fragile, and may fail
silently more often than it succeeds. It is preserved for completeness
(per the "do not remove functionality" requirement) rather than because
it's recommended for production use.
"""
import io

from app.config import settings
from app.utils.http import fetch_bytes, fetch_text
from app.utils.errors import CaptchaError, InvalidParameterError
from app.parsers.pnr_parser import parse_indianrail_pnr


def _decode_captcha(image_bytes: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        raise CaptchaError(
            "The legacy indianrail.gov.in PNR source requires optional "
            "dependencies (Pillow, pytesseract, and a system Tesseract OCR "
            "install) that are not available in this deployment."
        ) from exc

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        data = image.getdata()
        opaque_on_white = [
            (255, 255, 255, 255) if pixel[3] == 0 else pixel for pixel in data
        ]
        image.putdata(opaque_on_white)

        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", None)
        if resample is None:
            resample = getattr(Image, "ANTIALIAS", 1)  # last-resort fallback
        image = image.resize((300, 128), resample)

        raw_text = pytesseract.image_to_string(image)
    except Exception as exc:  # noqa: BLE001 - genuinely need to catch anything OCR-related
        raise CaptchaError(f"CAPTCHA OCR failed: {exc}") from exc

    for sep in ("=", ":"):
        if sep in raw_text:
            expression = raw_text.split(sep)[0].strip()
            try:
                # The CAPTCHA is a simple arithmetic expression (e.g. "3+4").
                # Restrict eval to digits/operators only for safety.
                if expression and all(c in "0123456789+-*/() " for c in expression):
                    return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307
            except Exception:  # noqa: BLE001
                break
    raise CaptchaError("Could not confidently decode the CAPTCHA image.")


async def get_pnr_status_legacy(pnr: str) -> dict:
    if not pnr or len(str(pnr)) != 10 or not str(pnr).isdigit():
        raise InvalidParameterError("PNR must be exactly 10 digits.")

    image_bytes = await fetch_bytes(settings.INDIANRAIL_CAPTCHA_URL)
    captcha_answer = _decode_captcha(image_bytes)

    raw = await fetch_text(
        settings.INDIANRAIL_PNR_URL,
        params={"inputCaptcha": captcha_answer, "inputPnrNo": pnr, "inputPage": "PNR"},
    )
    return parse_indianrail_pnr(raw)
