import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.utils.errors import RailAPIError, error_envelope
from app.utils.http import close_client
from app.utils.rate_limit import RateLimitMiddleware

from app.routes import meta, trains, route, fare, availability, status, station, pnr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("railway_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_client()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Unified, unofficial Indian Railways REST API combining data extraction "
        "logic from two prior unofficial projects. See /README for details, "
        "limitations, and upstream-source disclaimers."
    ),
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)

app.include_router(meta.router)
app.include_router(trains.router)
app.include_router(route.router)
app.include_router(fare.router)
app.include_router(availability.router)
app.include_router(status.router)
app.include_router(station.router)
app.include_router(pnr.router)


# ---------------------------------------------------------------------------
# Global exception handlers — every error path returns the SAME JSON shape,
# and no raw Python traceback is ever exposed to the client (Phase 8).
# ---------------------------------------------------------------------------

@app.exception_handler(RailAPIError)
async def handle_rail_api_error(request: Request, exc: RailAPIError):
    logger.warning("RailAPIError [%s] on %s: %s", exc.code, request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(exc.code, exc.message),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    messages = "; ".join(
        f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content=error_envelope("INVALID_PARAMETER", messages or "Invalid request parameters."),
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(code, str(exc.detail)),
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content=error_envelope("INTERNAL_ERROR", "An unexpected error occurred."),
    )
