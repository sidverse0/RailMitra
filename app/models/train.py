from typing import Any, Optional

from pydantic import BaseModel


class TrainBase(BaseModel):
    train_no: Optional[str] = None
    train_name: Optional[str] = None
    source_stn_name: Optional[str] = None
    source_stn_code: Optional[str] = None
    dstn_stn_name: Optional[str] = None
    dstn_stn_code: Optional[str] = None
    from_stn_name: Optional[str] = None
    from_stn_code: Optional[str] = None
    to_stn_name: Optional[str] = None
    to_stn_code: Optional[str] = None
    from_time: Optional[str] = None
    to_time: Optional[str] = None
    travel_time: Optional[str] = None
    running_days: Optional[str] = None
    source_depart: Optional[str] = None
    dstn_reach: Optional[str] = None
    type: Optional[str] = None
    train_id: Optional[str] = None
    distance_from_to: Optional[str] = None
    average_speed: Optional[str] = None
    notif_coach: Optional[str] = None


class CoachTypes(BaseModel):
    class Config:
        extra = "allow"


class Train(BaseModel):
    train_base: TrainBase
    coach_types: Optional[dict[str, str]] = None
    train_type: Optional[str] = None
    region: Optional[str] = None
    rake_share: Optional[list] = None
    coach_arrangement: Optional[list[dict[str, Any]]] = None
    notif: Optional[str] = None
