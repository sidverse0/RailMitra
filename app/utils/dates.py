"""
Date handling utilities.

--------------------------------------------------------------------------
IMPORTANT — running_days weekday index mapping
--------------------------------------------------------------------------
erail.in returns a 7-character `running_days` string such as "1101000",
one character per day of the week, where '1' means the train runs that day.

The two original projects disagreed on how to map a calendar date to an
index into that string:

  * Python RailIN (getTrainsOn) used `datetime.date.weekday()` DIRECTLY as
    the index. `date.weekday()` returns Monday=0 ... Sunday=6. This
    implicitly assumes running_days[0] == Monday.

  * The JS project (getDayOnDate) used JavaScript's `Date.getDay()`
    (Sunday=0 ... Saturday=6) and then remapped it:
        day = (getDay in [0,1,2]) ? getDay + 4 : getDay - 3
    which produces: Wed=0, Thu=1, Fri=2, Sat=3, Sun=4, Mon=5, Tue=6.
    In other words running_days[0] == WEDNESDAY, not Monday.

These two are NOT equivalent — they disagree on 6 out of 7 days. Since we
could not reach erail.in from this sandboxed build environment to verify
against a live response, we cannot empirically re-derive the mapping here.
We adopt the JS project's mapping (Wednesday-indexed) as canonical because
it was reverse-engineered more recently and is explicitly documented in
its own source rather than being an unexamined assumption, but this
decision is flagged clearly in the README and should be verified against a
live upstream response before being relied on for anything critical.

Both interpretations are exposed:
  * `erail_weekday_index(d)`      -> the adopted (JS-style, Wed=0) index
  * `python_style_weekday_index(d)` -> the original Python (Mon=0) index

The `/api/trains/date` endpoint uses `erail_weekday_index` by default and
accepts `?day_index_mode=python` to opt into the legacy behaviour for
comparison/debugging.
--------------------------------------------------------------------------
"""
from datetime import date as date_cls
from app.utils.errors import InvalidDateError


def parse_ddmmyyyy(value: str) -> date_cls:
    """Parse a DD-MM-YYYY string into a date, raising InvalidDateError on failure."""
    if not value or not isinstance(value, str):
        raise InvalidDateError("Date is required in DD-MM-YYYY format.")
    parts = value.strip().split("-")
    if len(parts) != 3:
        raise InvalidDateError(f"Invalid date '{value}'. Expected format DD-MM-YYYY.")
    dd_s, mm_s, yyyy_s = parts
    if not (dd_s.isdigit() and mm_s.isdigit() and yyyy_s.isdigit()):
        raise InvalidDateError(f"Invalid date '{value}'. Expected format DD-MM-YYYY.")
    dd, mm, yyyy = int(dd_s), int(mm_s), int(yyyy_s)
    if yyyy < 100:
        yyyy += 2000
    try:
        return date_cls(yyyy, mm, dd)
    except ValueError as exc:
        raise InvalidDateError(f"Invalid date '{value}': {exc}") from exc


def parse_ddmm(value: str, year: int) -> date_cls:
    """Parse a DD-MM string (used by /api/availability) into a date for a given year."""
    if not value or not isinstance(value, str):
        raise InvalidDateError("Date is required in DD-MM format.")
    parts = value.strip().split("-")
    if len(parts) != 2:
        raise InvalidDateError(f"Invalid date '{value}'. Expected format DD-MM.")
    dd_s, mm_s = parts
    if not (dd_s.isdigit() and mm_s.isdigit()):
        raise InvalidDateError(f"Invalid date '{value}'. Expected format DD-MM.")
    try:
        return date_cls(year, int(mm_s), int(dd_s))
    except ValueError as exc:
        raise InvalidDateError(f"Invalid date '{value}': {exc}") from exc


def erail_weekday_index(d: date_cls) -> int:
    """Wednesday-indexed weekday (matches the JS project's reverse-engineered mapping)."""
    # date.weekday(): Mon=0 .. Sun=6.  We want Wed=0 .. Tue=6.
    return (d.weekday() - 2) % 7


def python_style_weekday_index(d: date_cls) -> int:
    """Monday-indexed weekday (matches the ORIGINAL Python RailIN, kept for comparison only)."""
    return d.weekday()
