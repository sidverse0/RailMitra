"""
PNR status via ConfirmTkt scraping.

Ported from the JS project's `/pnrstatus` route, which credits
RobinKumar5986 (PR #3) for the approach. No CAPTCHA required, which makes
it far more reliable in a server context than the indianrail.gov.in path
(see app/services/pnr_captcha.py) — this is why it's the default PNR
source (PNR_DEFAULT_SOURCE=confirmtkt).
"""
from app.config import settings
from app.utils.http import fetch_text
from app.parsers.pnr_parser import parse_confirmtkt_pnr


async def get_pnr_status(pnr: str) -> dict:
    url = settings.CONFIRMTKT_PNR_URL.format(pnr=pnr)
    html = await fetch_text(url)
    return parse_confirmtkt_pnr(html)
