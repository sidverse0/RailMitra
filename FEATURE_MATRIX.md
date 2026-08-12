# Feature Matrix

| Feature | Python RailIN (original) | JS indian-rail-api (original) | Final Unified API |
|---|---|---|---|
| Single train info | ✅ `getTrain` / `TrainsToJson` | ✅ `/getTrain` (`CheckTrain`) — reduced field set | ✅ `GET /api/train/{no}` — full field set (superset of both) |
| Trains between two stations | ✅ `getAllTrains` / `TrainsToJson` — full field set | ✅ `/betweenStations` (`BetweenStation`) — reduced field set, extra error-string handling | ✅ `GET /api/trains?from=&to=` — full field set + JS's error-string handling |
| Trains between stations on a specific date | ✅ `getTrainsOn` — Monday-indexed weekday, **no known-error handling** | ✅ `/getTrainOn` — Wednesday-indexed weekday, delegates to `BetweenStation` | ✅ `GET /api/trains/date` — configurable weekday index (`erail` default / `python` legacy), full field set, error handling. See README "Known discrepancies #1". |
| Full train route (station-by-station) | ✅ `getRoute` / `StationToJson` — 13 fields/station | ✅ `/getRoute` (`GetRoute`) — 7 fields/station, index-shift bug when fields are empty | ✅ `GET /api/route/{no}` — 13 fields/station (Python's superset adopted as canonical; see README "Known discrepancies #2") |
| Fare by class | ✅ `getFare` / `FareToJson` (BeautifulSoup HTML table scrape) | ❌ not present | ✅ `GET /api/fare` — hardened against layout changes (raises `MALFORMED_UPSTREAM_RESPONSE` instead of crashing) |
| Seat/berth availability | ✅ `getAvailability` / `AvailToJson` | ❌ not present | ✅ `GET /api/availability` |
| Train running status / delay | ✅ `getStatus` (raw JSON passthrough from tripmgt.com) | ❌ not present | ✅ `GET /api/status` — **RailRadar `/v1/trains/{no}/live` is now the default source** (richer: live position, delay, per-stop status, diversions); auto-falls-back to the legacy tripmgt.com passthrough on RailRadar auth/quota/outage errors, or via `?source=legacy` |
| Live station board ("what's happening right now") | ❌ not present | ✅ `/stationLive` (`LiveStation`, cheerio) | ✅ `GET /api/station-live/{code}` — ported to BeautifulSoup, same extraction logic. Kept on the legacy erail.in scrape only (not RailRadar) since it's hit frequently and RailRadar's free tier is only 50 req/day |
| PNR status (ConfirmTkt source) | ❌ not present | ✅ `/pnrstatus` (`PnrStatus`, regex-extracted embedded JSON) | ✅ `GET /api/pnr/{pnr}?source=confirmtkt` |
| PNR status (indianrail.gov.in + CAPTCHA) | ✅ `getPNR` / `CaptchaBreak` (Pillow + pytesseract OCR) | ❌ not present | ✅ `GET /api/pnr/{pnr}?source=indianrail` — isolated module, optional deps, `Image.ANTIALIAS` deprecation bug fixed, never crashes the server on failure |
| PNR status (lostingness proxy) | ❌ not present | ❌ not present | ✅ `GET /api/pnr/{pnr}` — **NEW, DEFAULT source**. Paid third-party proxy (wraps ConfirmTkt's own internal API), confirmed working; correctly distinguishes a genuine "PNR not found" (`errorCode`) from a real success rather than returning an all-null blob as success |
| Root / info endpoint | ❌ not present | ✅ `GET /` (static message) | ✅ `GET /` — structured API info + endpoint list |
| Health check | ❌ not present | ❌ not present | ✅ `GET /health` (new — needed for Render/uptime monitoring) |
| Consistent JSON error envelope | ❌ ad-hoc `{'error': '...'}` strings, or bare exceptions | ⚠️ partial — some routes have `{success, time_stamp, data}`, others just `console.log` and return nothing on error | ✅ Every endpoint: `{success, timestamp, error: {code, message}}` on failure, `{success, timestamp, data}` on success |
| Known upstream "soft error" detection (bad station, train not found, etc.) | ❌ none | ⚠️ partial (only in `BetweenStation`/`CheckTrain`, not consistently) | ✅ Centralized in `train_parser.detect_known_errors`, used everywhere the erail.in train-list format is parsed |
| Combined single-request, multi-parser extraction | N/A (single language/parser) | N/A (single language/parser) | ✅ `?include=result1,result2` reconstructs BOTH original projects' output shapes from the SAME upstream response, no duplicate request |
| Caching | ❌ none | ❌ none | ✅ in-memory TTL cache, per-endpoint-tunable |
| Rate limiting | ❌ none | ❌ none | ✅ simple in-memory per-IP fixed-window limiter |
| Reusable HTTP client (timeout/UA/retry) | ⚠️ partial (UA only, via `user_agent` lib, no timeout/retry) | ⚠️ partial (UA only, via `user-agents` lib, no timeout/retry) | ✅ shared `httpx.AsyncClient`, timeout + UA rotation + bounded retries on transient errors |
| Deployment-ready for Render/Heroku-style PaaS | ⚠️ was a pip-installable library, no server | ⚠️ `app.listen(PORT \|\| 3000)` — hardcoded fallback port | ✅ `Procfile` + `$PORT` binding, no hardcoded ports |
| Automated tests / fixtures | ❌ none | ❌ none | ✅ 41 tests across parsers + API endpoints, with synthetic fixtures for every upstream format |

Legend: ✅ fully present · ⚠️ partially present / has issues · ❌ not present
