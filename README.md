# Unified Indian Railway API

A single **Python 3 + FastAPI** REST API that unifies the data-extraction logic
of two prior unofficial Indian Railways projects:

* **RailIN** (Python) — scraped erail.in / indianrail.gov.in, exposed as a
  Python library (`getPNR`, `getRoute`, `getAllTrains`, `getTrainsOn`,
  `getTrain`, `getAvailability`, `getFare`, `getStatus`).
* **indian-rail-api** (Node.js/Express) — scraped erail.in / confirmtkt.com,
  exposed as HTTP routes (`/getTrain`, `/betweenStations`, `/getTrainOn`,
  `/getRoute`, `/stationLive`, `/pnrstatus`).

This project is **not a rewrite of one into the other** — it is a full audit
and merge. See [FEATURE_MATRIX.md](FEATURE_MATRIX.md) and
[FIELD_MATRIX.md](FIELD_MATRIX.md) for a complete, per-item accounting of
what came from where.

> **⚠️ Unofficial API — not affiliated with Indian Railways, IRCTC, or any
> official body.** All data is scraped from third-party public sources
> (erail.in, indianrail.gov.in, confirmtkt.com, data.tripmgt.com) that can
> change their markup/response format at any time without notice, which
> will break the corresponding endpoint here until updated. Not intended
> for commercial use. Use responsibly — this project does not encourage or
> perform aggressive/high-frequency scraping.

---

## Features

* Train info lookup by number
* Trains running between two stations
* Trains between two stations filtered to a specific date (running-days aware)
* Full station-by-station route for a train
* Fare by class
* Seat/berth availability
* Train running status / delay at a station
* Live "what's happening at this station right now" board
* PNR status (two independent sources: ConfirmTkt [default] and a legacy
  indianrail.gov.in CAPTCHA-OCR path)
* Consistent JSON envelope and error codes on every endpoint
* In-memory response caching (short TTL, per source) to avoid hammering
  upstream sites
* Simple per-IP in-memory rate limiting
* No database required

---

## Architecture

```
app/
  main.py              FastAPI app, global exception handlers, router wiring
  config.py             All tunables (timeouts, cache TTLs, rate limits, URLs)

  routes/                One module per feature area — thin, calls services+parsers
    meta.py               GET /, GET /health
    trains.py              GET /api/train/{no}, /api/trains, /api/trains/date
    route.py                GET /api/route/{no}
    fare.py                  GET /api/fare
    availability.py           GET /api/availability
    status.py                  GET /api/status
    station.py                  GET /api/station-live/{code}
    pnr.py                       GET /api/pnr/{pnr}

  services/               ONE upstream HTTP request per logical operation
    erail.py               all erail.in endpoints (train info, trains-between,
                            route, fare, availability, station-live)
    status.py                data.tripmgt.com (running status)
    pnr_confirmtkt.py         confirmtkt.com (default PNR source)
    pnr_captcha.py             indianrail.gov.in + CAPTCHA OCR (legacy PNR source,
                                isolated, optional dependencies)

  parsers/                 Pure functions: raw upstream text/HTML -> dict(s).
                            No network calls. This is where BOTH projects'
                            extraction logic was merged field-by-field.
    train_parser.py          unifies Python's MakeSenseTrain + JS's
                              CheckTrain/BetweenStation (see docstring for the
                              full field-provenance table)
    route_parser.py           unifies Python's MakeSenseStation + JS's GetRoute
    fare_parser.py             Python-only (FareToJson), hardened
    availability_parser.py      Python-only (AvailToJson), hardened
    station_parser.py            JS-only (LiveStation), ported to BeautifulSoup
    pnr_parser.py                  both PNR sources' payload parsing

  models/                  Pydantic response models (train.py, route.py, common.py)

  utils/
    http.py                Shared httpx.AsyncClient: timeout, UA rotation, retries
    dates.py                 DD-MM-YYYY parsing + the running_days weekday-index
                              mapping (see "Known discrepancies" below)
    cache.py                   In-memory TTL cache
    rate_limit.py                Simple per-IP fixed-window limiter middleware
    errors.py                     Exception hierarchy + JSON envelope helpers

tests/
  test_train_parser.py, test_route_parser.py, test_misc_parsers.py,
  test_api_endpoints.py    Parser + endpoint tests, run against fixtures
  fixtures/                 Synthetic sample raw upstream responses (see
                             "About the test fixtures" below) + the script
                             that generated them
```

**Design principle — one upstream request per logical operation:** both
`getTrain` (single train) and `betweenStations` (train list) in the original
projects hit the exact same `erail.in/rail/getTrains.aspx` endpoint. Rather
than querying it twice to get "the Python-style result" and "the JS-style
result" separately, `app/services/erail.py` fetches the raw response **once**,
and `app/parsers/train_parser.py` derives the full unified result (and, on
request, both legacy reconstructions) from that single raw string. The only
endpoint that genuinely needs two upstream requests is `/api/route/{train_no}`,
because both original projects resolve the train's internal numeric ID first
and then fetch the route with a *different* URL — that's an unavoidable
two-step lookup, not duplicate parsing.

---

## Installation

```bash
git clone <this-repo>
cd railway-api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Local development

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: `http://localhost:8000/docs`

Run the test suite:

```bash
pytest
```

---

## Environment variables

All optional — sensible defaults are baked into `app/config.py`.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | (set by host) | Port to bind — **required in production**, see Deployment |
| `ENV` | `development` | Free-text environment label |
| `HTTP_TIMEOUT_SECONDS` | `10` | Upstream request timeout |
| `HTTP_CONNECT_TIMEOUT_SECONDS` | `5` | Upstream connect timeout |
| `HTTP_MAX_RETRIES` | `2` | Retries on network-level failures (not on 4xx) |
| `CACHE_ENABLED` | `true` | Toggle in-memory caching |
| `CACHE_TTL_*_SECONDS` | varies | Per-endpoint cache TTL |
| `CACHE_MAX_ENTRIES` | `2000` | Approximate cache size cap |
| `RATE_LIMIT_ENABLED` | `true` | Toggle the per-IP limiter |
| `RATE_LIMIT_REQUESTS` | `60` | Requests allowed per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Window size |
| `PNR_DEFAULT_SOURCE` | `lostingness` | `lostingness` (default, paid, confirmed working), `confirmtkt`, or `indianrail` |
| `LOSTINGNESS_PNR_URL` | `https://my.lostingness.site/encore.php` | Override if the community-found endpoint moves |
| `LOSTINGNESS_API_KEY` | `fcmencoreog` (shared/public) | Override if you get an individually-issued token |
| `RAILRADAR_API_KEY` | *(unset)* | Your RailRadar API key — see below. Without it, `/api/status` automatically uses the legacy scraped source. |
| `STATUS_SOURCE_DEFAULT` | `railradar` | Default source for `/api/status`: `railradar` or `legacy` |

### RailRadar integration (live train status)

[RailRadar](https://railradar.in) is now the **primary** source for
`/api/status` — its data is significantly more reliable than the original
scraped source (data.tripmgt.com).

`/api/station-live/{code}` intentionally stays on the legacy erail.in
scrape only and is NOT wired to RailRadar — that endpoint tends to get hit
far more frequently, and RailRadar's free tier is only 50 requests/day, so
routing it through RailRadar too would burn through the quota fast for
comparatively little benefit. (RailRadar does support a station-live board
too — `GET /v1/stations/{code}/live` — if you want to wire it up later,
`app/services/railradar.py` already has `fetch_station_live_board()`
ready to use.)

1. Sign up free at [railradar.in](https://railradar.in) and grab your API
   key from the [Developers dashboard](https://railradar.in/developers).
2. Set it as an environment variable — **never commit it or paste it into
   chat/code**:
   ```bash
   export RAILRADAR_API_KEY="rr_live_xxxxxxxxxxxx"
   ```
   On Render: Dashboard → your service → **Environment** → add
   `RAILRADAR_API_KEY`.
3. That's it — `/api/status` will use RailRadar automatically.

**Free tier is only 50 requests/day** (10/min burst). This project handles
that in two ways:
* Aggressive caching — `CACHE_TTL_STATUS_SECONDS` (180s) is set well above
  the original default specifically to conserve quota.
* **Automatic fallback** — if RailRadar isn't configured, hits its rate
  limit (429), rejects the key (401), or is down (503), `/api/status`
  transparently falls back to the original legacy scraped source (as long
  as you didn't explicitly pin `?source=railradar`, and you supplied a
  `station` query param, which the legacy source needs). The response
  always tells you which one served the request via the `"source"` field.

You can also force a specific source per-request:
```
GET /api/status?train_no=12951&station=NDLS&source=legacy
GET /api/status?train_no=12951&source=railradar
```

**⚠️ RailRadar does NOT cover PNR status or seat/berth availability** — it
has no endpoints for either. `/api/pnr/{pnr}` and `/api/availability`
remain on their original sources (ConfirmTkt / indianrail.gov.in, and
erail.in's `AVL_Request` respectively) — see the "PNR: two sources"
section below for the known limitations there.

---

## API endpoints

All responses use one consistent envelope.

**Success:**
```json
{ "success": true, "timestamp": 1733740800, "data": { "...": "..." } }
```

**Error:**
```json
{ "success": false, "timestamp": 1733740800,
  "error": { "code": "TRAIN_NOT_FOUND", "message": "Upstream reported: Train not found" } }
```

### `GET /`
API info / self-description.

### `GET /health`
Liveness check.

### `GET /api/train/{train_no}`
Single train info.
Query params: `include` (optional) = `result1,result2`

```
GET /api/train/12951
```

### `GET /api/trains?from=NDLS&to=BCT`
Trains running between two stations.
Query params: `include` (optional)

### `GET /api/trains/date?from=NDLS&to=BCT&date=09-08-2026`
Trains between two stations that run on a specific date.
Query params: `day_index_mode` = `erail` (default) or `python` (legacy), `include`

### `GET /api/route/{train_no}`
Full station-by-station route.

### `GET /api/fare?train_no=12951&from=NDLS&to=BCT`
Fare by class. *(Python-only feature; not present in the JS project.)*

### `GET /api/availability?train_no=12951&from=NDLS&to=BCT&class=SL&quota=GN&date=09-08`
Seat/berth availability. *(Python-only feature.)*

### `GET /api/status?train_no=12951&station=NDLS`
Running status / delay at a station. *(Python-only feature.)*

### `GET /api/station-live/{station_code}`
Trains currently live/expected at a station. *(JS-only feature, ported to
Python/BeautifulSoup.)*

### `GET /api/pnr/{pnr}`
PNR status. Query param `source` = `confirmtkt` (default) or `indianrail`
(legacy, best-effort — see "PNR: two sources" below).

### Example response — `GET /api/train/12951`

```json
{
  "success": true,
  "timestamp": 1733740800,
  "data": {
    "train_base": {
      "train_no": "12951",
      "train_name": "MUMBAI RAJDHANI",
      "source_stn_name": "NEW DELHI", "source_stn_code": "NDLS",
      "dstn_stn_name": "MUMBAI CENTRAL", "dstn_stn_code": "BCT",
      "from_stn_name": "NEW DELHI", "from_stn_code": "NDLS",
      "to_stn_name": "MUMBAI CENTRAL", "to_stn_code": "BCT",
      "from_time": "16:25", "to_time": "08:15", "travel_time": "15:50",
      "running_days": "1111111",
      "source_depart": "16:25", "dstn_reach": "08:15",
      "type": "Rajdhani", "train_id": "12951",
      "distance_from_to": "1384", "average_speed": "87",
      "notif_coach": "PantryCarAvailable"
    },
    "coach_types": {"1A":"1","2A":"1","3A":"1","CC":"1","SL":"1","2S":"1","GN":"1"},
    "train_type": "Rajdhani Express",
    "region": "NR",
    "rake_share": ["12","34"],
    "coach_arrangement": [{"1": {"tag":"A","coach_id":"101","type":"GEN"}}]
  }
}
```

---

## Known discrepancies between the two original projects (and how they were resolved)

### 1. `running_days` weekday index (date filtering)

* **Python RailIN** (`getTrainsOn`) used `datetime.date.weekday()`
  (Monday=0) directly as the index into `running_days`.
* **JS project** (`getDayOnDate`) used JavaScript's `Date.getDay()`
  (Sunday=0) and remapped it to a **Wednesday=0** scheme.

These disagree on 6 of 7 days. We could not reach erail.in from the build
environment to verify which is empirically correct against a live response.
`/api/trains/date` defaults to the JS-derived **Wednesday=0** mapping
(`?day_index_mode=erail`) since it was the more deliberately reverse-engineered
of the two, but exposes `?day_index_mode=python` to reproduce the original
Python behaviour for comparison. **Recommendation: verify against a live
response before depending on this for anything important.** See
`app/utils/dates.py` for the full reasoning.

### 2. Route/station field indices

Python's route parser (`MakeSenseStation`) indexes fields by fixed position.
JS's route parser (`GetRoute`) **filters out empty-string fields before
indexing**, which silently shifts field positions whenever an intermediate
field is blank (e.g. a station with no scheduled halt) — and its `zone`
field ends up reading a different raw index than Python's `zone`. Since we
couldn't test against live data, we adopted Python's fixed-position,
non-filtering approach as canonical (it's also a strict superset of JS's
fields). See `app/parsers/route_parser.py` docstring.

### 3. Train list completeness

JS's `/betweenStations` only ever extracted the 14 `train_base` fields —
never `coach_types`, `type`, `train_id`, `distance_from_to`,
`average_speed`, or the heuristic extras. Python's `getAllTrains` /
`TrainsToJson` extracted the full set. The unified `/api/trains` endpoint
always returns the full set (both come from the same upstream request; see
Architecture above).

### 4. Error-case detection

JS's `BetweenStation`/`CheckTrain` explicitly recognized several upstream
"soft error" strings (`"No direct trains found"`, `"From station not
found"`, `"To station not found"`, `"Please try again after some time."`,
`"Train not found"`) and returned a clean failure. Python's parsers had
**no such handling** and would have thrown confusing index errors on these
inputs. The unified parser (`train_parser.detect_known_errors`) checks all
of these up front, for both the single-train and list endpoints.

---

## PNR: three sources

* **`lostingness` (default)** — a paid third-party proxy
  (`my.lostingness.site/encore.php`), confirmed working against real PNR
  lookups. It appears to wrap ConfirmTkt's own internal PNR API (the
  response schema — `pnrResponse`, `showBlaBlaAd`, a `flightBannerUrl`
  pointing at `cdn.confirmtkt.com`, etc. — matches ConfirmTkt's own app
  response, not a from-scratch schema). Set as the default source since it
  proved more reliable than the free `confirmtkt` scrape path in practice.
  Two important parsing details baked into `app/services/pnr_lostingness.py`:
  * `pnrResponse` is present even on a **failed** lookup — every field
    comes back `null` with `errorCode`/`error` populated instead (e.g.
    `errorCode: 201, error: "Flushed PNR /PNR not yet generated"` for a
    stale/invalid PNR). This is explicitly checked and raised as a proper
    `PNR_NOT_FOUND` error — it is **not** treated as a successful response.
  * The bearer token was shared as plain text with the API key rather than
    pulled from a private per-account dashboard — if it ever stops working,
    override `LOSTINGNESS_API_KEY` / `LOSTINGNESS_PNR_URL` via env vars, or
    switch `PNR_DEFAULT_SOURCE` back, or use `?source=` per-request.
* **`confirmtkt`** — ported from the JS project. Scrapes confirmtkt.com
  directly and extracts an embedded JSON blob. No CAPTCHA required, but
  proved less reliable in practice than the `lostingness` proxy above (same
  underlying data, different delivery path).
* **`indianrail`** — ported from the original Python RailIN project.
  Uses indianrail.gov.in's PNR enquiry endpoint, which is gated behind an
  image CAPTCHA solved via OCR (Pillow + pytesseract + a system Tesseract
  binary). This path:
  * is fully isolated in `app/services/pnr_captcha.py` — it cannot crash
    the rest of the server, and its optional dependencies
    (`pillow`, `pytesseract`) are commented out of `requirements.txt` by
    default;
  * had a latent bug fixed during the port: `PIL.Image.ANTIALIAS` was
    removed in Pillow 10+; this now uses `Image.Resampling.LANCZOS`;
  * is inherently unreliable (OCR-guessing a CAPTCHA) and is **not**
    recommended for production use — it's preserved for completeness, not
    because it's the recommended path.

All three are unofficial scrapes/wrappers of third-party sites and may
break without notice. Switch source per-request with `?source=confirmtkt`,
`?source=indianrail`, or `?source=lostingness`.

---

## Error handling

Every upstream/parsing failure mode maps to a specific error code — no raw
Python traceback or exception `repr()` is ever returned to the client:

| Code | Meaning |
|---|---|
| `INVALID_PARAMETER` | Missing/malformed query or path parameter |
| `INVALID_DATE` | Date failed to parse as DD-MM-YYYY / DD-MM, or is a calendar-invalid date |
| `TRAIN_NOT_FOUND` | Upstream reported the train number doesn't exist |
| `STATION_NOT_FOUND` | Upstream reported the station code doesn't exist |
| `NO_TRAINS_FOUND` | No trains matched the query |
| `ROUTE_NOT_FOUND` | No route data returned for the train |
| `STATION_LIVE_NOT_FOUND` | No live data for the station |
| `UPSTREAM_TIMEOUT` | Upstream site didn't respond in time |
| `UPSTREAM_HTTP_ERROR` | Upstream returned a non-2xx HTTP status |
| `UPSTREAM_UNAVAILABLE` | Upstream explicitly said "try again later" |
| `EMPTY_UPSTREAM_RESPONSE` | Upstream returned nothing |
| `MALFORMED_UPSTREAM_RESPONSE` | Upstream response didn't match the expected shape |
| `PARSER_ERROR` | Internal parsing failure |
| `PNR_ERROR` | PNR-specific lookup/parse failure |
| `CAPTCHA_ERROR` | Legacy PNR CAPTCHA OCR failed |
| `RATE_LIMIT_EXCEEDED` | Too many requests from this client |
| `INTERNAL_ERROR` | Unexpected/unclassified failure |

---

## About the test fixtures

`tests/fixtures/` contains **hand-built synthetic samples** of each upstream
response format (`trains_between.txt`, `route.txt`, `fare.html`, etc.),
generated by `tests/fixtures/_generate_fixtures.py`. This build environment
has no network access to erail.in / indianrail.gov.in / confirmtkt.com, so
these fixtures were constructed directly from the exact delimiter logic in
both original projects' source (documented at the top of each file), **not**
captured from a live response. They're accurate to the documented parsing
logic but should be cross-checked against a real live response before
relying on this in production, especially for the flagged discrepancies
above.

Run `pytest -v` to see all 41 tests (parser-level + full API endpoint tests
with the upstream HTTP layer mocked).

---

## Deployment (Render)

1. Push this repo to GitHub.
2. On Render: **New → Web Service**, connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command (or use the included `Procfile`):
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   The app **never** hardcodes port 8000/3000 in production — it always
   binds `0.0.0.0:$PORT`, which Render sets automatically.
5. No database or persistent disk needed.

---

## Limitations

* Unofficial, scraping-based — will break if any upstream site changes its
  markup/response format, with no advance warning.
* Not intended for commercial use; be a good citizen with request volume
  (the built-in cache + rate limiter help, but this is still a shared,
  unofficial data source).
* The legacy `indianrail` PNR source's CAPTCHA-OCR is best-effort and may
  fail more often than it succeeds.
* Single-process in-memory cache/rate-limiter — state is not shared across
  multiple server instances/replicas.
* See "Known discrepancies" above for the two flagged, unverified
  behavioural decisions (date/weekday mapping, route field indices).

---

## License

Data and its rights are reserved to their respective owners (erail.in,
indianrail.gov.in, confirmtkt.com, Indian Railways). This project claims no
rights over the underlying data and does not promote its use for commercial
applications, consistent with the license terms of both source projects.
