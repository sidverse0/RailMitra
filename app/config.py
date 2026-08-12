"""
Central configuration for the unified Railway API.

All tunables (timeouts, cache TTLs, rate limits, upstream URLs) live here so
behaviour can be adjusted without touching business logic.
"""
import os


class Settings:
    # --- General ---
    APP_NAME: str = "Unified Indian Railway API"
    APP_VERSION: str = "1.0.0"
    ENV: str = os.getenv("ENV", "development")

    # --- HTTP client ---
    HTTP_TIMEOUT_SECONDS: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
    HTTP_CONNECT_TIMEOUT_SECONDS: float = float(os.getenv("HTTP_CONNECT_TIMEOUT_SECONDS", "5"))
    HTTP_MAX_RETRIES: int = int(os.getenv("HTTP_MAX_RETRIES", "2"))
    HTTP_RETRY_BACKOFF_SECONDS: float = float(os.getenv("HTTP_RETRY_BACKOFF_SECONDS", "0.5"))

    # --- Caching (in-memory, per-process) ---
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL_TRAIN_SECONDS: int = int(os.getenv("CACHE_TTL_TRAIN_SECONDS", "120"))
    CACHE_TTL_TRAINS_BETWEEN_SECONDS: int = int(os.getenv("CACHE_TTL_TRAINS_BETWEEN_SECONDS", "120"))
    CACHE_TTL_ROUTE_SECONDS: int = int(os.getenv("CACHE_TTL_ROUTE_SECONDS", "600"))
    CACHE_TTL_FARE_SECONDS: int = int(os.getenv("CACHE_TTL_FARE_SECONDS", "1800"))
    CACHE_TTL_AVAILABILITY_SECONDS: int = int(os.getenv("CACHE_TTL_AVAILABILITY_SECONDS", "60"))
    # Bumped up from the original 60s/30s defaults: RailRadar's free tier is
    # only 50 requests/day, so these need to be cached much longer than the
    # old direct-scrape defaults to avoid burning through quota fast.
    CACHE_TTL_STATUS_SECONDS: int = int(os.getenv("CACHE_TTL_STATUS_SECONDS", "180"))
    CACHE_TTL_STATION_LIVE_SECONDS: int = int(os.getenv("CACHE_TTL_STATION_LIVE_SECONDS", "120"))
    CACHE_MAX_ENTRIES: int = int(os.getenv("CACHE_MAX_ENTRIES", "2000"))
    # --- Rate limiting (simple in-memory, per-process, per-client-IP) ---
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # --- Upstream sources ---
    ERAIL_BASE: str = "https://erail.in"
    ERAIL_TRAINS_URL: str = ERAIL_BASE + "/rail/getTrains.aspx"
    ERAIL_DATA_URL: str = ERAIL_BASE + "/data.aspx"
    ERAIL_STATION_LIVE_URL: str = ERAIL_BASE + "/station-live/{code}"
    ERAIL_AVAILABILITY_URL: str = "https://d.erail.in/AVL_Request"
    TRIPMGT_STATUS_URL: str = "https://data.tripmgt.com/Data.aspx"
    CONFIRMTKT_PNR_URL: str = "https://www.confirmtkt.com/pnr-status/{pnr}"
    INDIANRAIL_CAPTCHA_URL: str = "http://www.indianrail.gov.in/enquiry/captchaDraw.png"
    INDIANRAIL_PNR_URL: str = "http://www.indianrail.gov.in/enquiry/CommonCaptcha"

    # Third, community-found PNR source. UNOFFICIAL AND UNVERIFIED: it's a
    # random third-party domain with a shared/public bearer token (not
    # individually issued), no public documentation, and no uptime/reliability
    # guarantee. Kept fully optional (never the default) and isolated the same
    # way as the legacy indianrail CAPTCHA source — a failure here can never
    # crash the rest of the API. Override the token via env var if the person
    # providing it ever gets an individually-issued key instead of the shared one.
    LOSTINGNESS_PNR_URL: str = os.getenv(
        "LOSTINGNESS_PNR_URL", "https://my.lostingness.site/encore.php"
    )
    LOSTINGNESS_API_KEY: str = os.getenv("LOSTINGNESS_API_KEY", "fcmencoreog")

    # --- RailRadar (https://railradar.in/docs) ---
    # Used as the PRIMARY source for live train status and station live boards
    # (both were unreliable via the raw erail.in/tripmgt.com scrapes). Falls
    # back automatically to the legacy scraped source if RailRadar is not
    # configured, or if it errors/rate-limits/is unavailable — nothing is
    # removed, RailRadar just sits in front of it.
    #
    # NOTE: RailRadar has NO endpoint for PNR status or seat/berth
    # availability — those two features remain on their original sources
    # (ConfirmTkt/indianrail.gov.in for PNR, erail.in AVL_Request for
    # availability) since there's nothing to migrate them to.
    RAILRADAR_BASE_URL: str = "https://api.railradar.in/v1"
    RAILRADAR_API_KEY: str = os.getenv("RAILRADAR_API_KEY", "")
    RAILRADAR_LIVE_STATUS_URL: str = RAILRADAR_BASE_URL + "/trains/{number}/live"
    RAILRADAR_STATION_LIVE_URL: str = RAILRADAR_BASE_URL + "/stations/{code}/live"
    # Free tier is only 50 requests/day (10/min burst) — cache aggressively
    # and prefer the legacy fallback once you're out of quota rather than
    # hammering a 429. RailRadar is used ONLY for /api/status (live train
    # status) — /api/station-live intentionally stays on the legacy erail.in
    # scrape since it's expected to be hit far more frequently and would
    # burn through the daily quota fast.
    STATUS_SOURCE_DEFAULT: str = os.getenv("STATUS_SOURCE_DEFAULT", "railradar")  # railradar | legacy

    # --- PNR ---
    # 'lostingness' is a paid third-party proxy the person integrating this
    # confirmed works reliably (unlike the free scraped ConfirmTkt path,
    # which they found unreliable). Kept overridable via env var / per-request
    # ?source= in case that ever changes.
    PNR_DEFAULT_SOURCE: str = os.getenv("PNR_DEFAULT_SOURCE", "lostingness")  # confirmtkt | indianrail | lostingness

    # --- Misc ---
    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )


settings = Settings()
