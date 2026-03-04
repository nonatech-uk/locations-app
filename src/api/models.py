"""Pydantic response models."""

from datetime import date, datetime

from pydantic import BaseModel


class GpsPoint(BaseModel):
    lat: float
    lon: float
    ts: datetime
    speed_mph: float | None = None
    altitude_m: float | None = None


class GpsPointsResponse(BaseModel):
    points: list[GpsPoint]
    total_count: int
    returned_count: int
    simplified: bool


class GpsBoundsResponse(BaseModel):
    earliest: date
    latest: date
    total_points: int


class OverviewStats(BaseModel):
    gps_points: int
    flights: int
    skiing_days: int
    ga_flights: int
