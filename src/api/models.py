"""Pydantic response models."""

from datetime import date, datetime, time, timedelta

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
    skiing_days: int


# --- Place Types ---


class PlaceTypeCreate(BaseModel):
    name: str


class PlaceTypeResponse(BaseModel):
    id: int
    name: str


class PlaceTypeListResponse(BaseModel):
    items: list[PlaceTypeResponse]
    total_count: int


# --- Places ---


class PlaceCreate(BaseModel):
    name: str
    place_type_id: int
    lat: float
    lon: float
    distance_m: int = 200
    date_from: date | None = None
    date_to: date | None = None
    notes: str | None = None


class PlaceUpdate(BaseModel):
    name: str | None = None
    place_type_id: int | None = None
    lat: float | None = None
    lon: float | None = None
    distance_m: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    notes: str | None = None


class PlaceSummary(BaseModel):
    id: int
    name: str
    place_type_id: int
    place_type_name: str
    lat: float
    lon: float
    distance_m: int
    date_from: date | None = None
    date_to: date | None = None
    notes: str | None = None


class PlaceListResponse(BaseModel):
    items: list[PlaceSummary]
    total_count: int
    page: int
    per_page: int
    total_pages: int


class PlaceLookupResult(BaseModel):
    place: PlaceSummary | None = None
    distance_m: float | None = None
    source: str


# --- Daily GPS Summary ---


class DayEndpoint(BaseModel):
    lat: float
    lon: float
    ts: datetime
    place_name: str | None = None
    place_type: str | None = None


class DailySummaryResponse(BaseModel):
    date: date
    point_count: int
    start: DayEndpoint | None = None
    end: DayEndpoint | None = None
    track_svg_url: str | None = None
