from typing import Optional

from pydantic import BaseModel


class RouteStation(BaseModel):
    index: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    arrival: Optional[str] = None
    depart: Optional[str] = None
    halt: Optional[str] = None
    distance_from_source: Optional[str] = None
    day: Optional[str] = None
    platform: Optional[str] = None
    zone: Optional[str] = None
    division: Optional[str] = None
    lat: Optional[str] = None
    lng: Optional[str] = None
