"""Small shared helpers used across route modules."""
from typing import Optional

from fastapi import Query


def parse_include(include: Optional[str]) -> set[str]:
    """Parses `?include=result1,result2` into a set like {"result1", "result2"}."""
    if not include:
        return set()
    return {part.strip() for part in include.split(",") if part.strip()}


IncludeQuery = Query(
    default=None,
    description=(
        "Optional comma-separated list to also expose the raw per-source parser "
        "outputs alongside the unified `data` field, e.g. `include=result1,result2`. "
        "`result1` = legacy Python-RailIN-style output, `result2` = legacy "
        "JS-project-style output. Default response omits both and returns only "
        "the normalized, unified `data`."
    ),
)
