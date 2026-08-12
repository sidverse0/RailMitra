from fastapi import APIRouter

from app.config import settings
from app.utils.errors import success_envelope

router = APIRouter(tags=["meta"])


@router.get("/")
async def root():
    return success_envelope(
        {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "description": (
                "Unofficial Indian Railways REST API — unifies data extraction from "
                "two prior unofficial projects (a Python scraper and a Node.js/Express "
                "scraper) into a single Python + FastAPI service."
            ),
            "endpoints": [
                "GET /api/train/{train_no}",
                "GET /api/trains?from=&to=",
                "GET /api/trains/date?from=&to=&date=DD-MM-YYYY",
                "GET /api/route/{train_no}",
                "GET /api/fare?train_no=&from=&to=",
                "GET /api/availability?train_no=&from=&to=&class=&quota=&date=DD-MM",
                "GET /api/status?train_no=&station=",
                "GET /api/station-live/{station_code}",
                "GET /api/pnr/{pnr}",
                "GET /health",
            ],
            "docs": "/docs",
            "disclaimer": (
                "Unofficial API. Not affiliated with Indian Railways/IRCTC. Data is "
                "scraped from third-party public sources and may break without notice."
            ),
        }
    )


@router.get("/health")
async def health():
    return success_envelope({"status": "ok"})
