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
    flights: int
    skiing_days: int
    ga_flights: int


# --- Flights ---


class FlightSummary(BaseModel):
    id: int
    date: date
    dep_airport: str
    arr_airport: str
    dep_airport_name: str | None = None
    arr_airport_name: str | None = None
    flight_number: str | None = None
    airline: str | None = None
    aircraft_type: str | None = None
    registration: str | None = None
    duration: str | None = None  # ISO 8601 duration or HH:MM
    distance_km: int | None = None
    flight_class: int | None = None
    seat_number: str | None = None
    notes: str | None = None
    is_route: bool = False
    times_flown: int | None = None
    has_route_image: bool = False
    has_aircraft_image: bool = False


class FlightDetail(BaseModel):
    id: int
    date: date
    flight_number: str | None = None
    dep_airport: str
    dep_airport_name: str | None = None
    dep_icao: str | None = None
    arr_airport: str
    arr_airport_name: str | None = None
    arr_icao: str | None = None
    dep_time: str | None = None  # HH:MM
    arr_time: str | None = None
    duration: str | None = None
    airline: str | None = None
    airline_code: str | None = None
    aircraft_type: str | None = None
    aircraft_code: str | None = None
    registration: str | None = None
    gate_origin: str | None = None
    gate_destination: str | None = None
    terminal_origin: str | None = None
    terminal_destination: str | None = None
    baggage_claim: str | None = None
    departure_delay: int | None = None
    arrival_delay: int | None = None
    route_distance: int | None = None
    runway_origin: str | None = None
    runway_destination: str | None = None
    codeshares: str | None = None
    seat_number: str | None = None
    seat_type: int | None = None
    flight_class: int | None = None
    flight_reason: int | None = None
    notes: str | None = None
    source: str | None = None
    gps_matched: bool = False
    dep_lat: float | None = None
    dep_lon: float | None = None
    arr_lat: float | None = None
    arr_lon: float | None = None
    distance_km: int | None = None
    is_route: bool = False
    times_flown: int | None = None
    has_route_image: bool = False
    has_aircraft_image: bool = False


class FlightUpdate(BaseModel):
    notes: str | None = None
    seat_number: str | None = None
    seat_type: int | None = None
    flight_class: int | None = None
    flight_reason: int | None = None
    registration: str | None = None
    aircraft_type: str | None = None
    flight_number: str | None = None
    airline: str | None = None
    is_route: bool | None = None
    times_flown: int | None = None


class FlightListResponse(BaseModel):
    items: list[FlightSummary]
    total_count: int
    page: int
    per_page: int
    total_pages: int


# --- GA Flights ---


class GAFlightSummary(BaseModel):
    id: int
    date: date
    aircraft_type: str | None = None
    registration: str | None = None
    captain: str | None = None
    operating_capacity: str | None = None
    dep_airport: str | None = None
    arr_airport: str | None = None
    dep_time: str | None = None
    arr_time: str | None = None
    hours_total: float | None = None
    exercise: str | None = None
    is_local: bool = False
    has_route_image: bool = False
    has_aircraft_image: bool = False


class GAFlightDetail(BaseModel):
    id: int
    date: date
    aircraft_type: str | None = None
    registration: str | None = None
    captain: str | None = None
    operating_capacity: str | None = None
    dep_airport: str | None = None
    arr_airport: str | None = None
    dep_time: str | None = None
    arr_time: str | None = None
    hours_sep_pic: float | None = None
    hours_sep_dual: float | None = None
    hours_mep_pic: float | None = None
    hours_mep_dual: float | None = None
    hours_pic_3: float | None = None
    hours_dual_3: float | None = None
    hours_pic_4: float | None = None
    hours_dual_4: float | None = None
    hours_instrument: float | None = None
    hours_as_instructor: float | None = None
    hours_simulator: float | None = None
    hours_total: float | None = None
    instructor: str | None = None
    exercise: str | None = None
    comments: str | None = None
    is_local: bool = False
    has_route_image: bool = False
    has_aircraft_image: bool = False


class GAFlightUpdate(BaseModel):
    comments: str | None = None
    exercise: str | None = None
    captain: str | None = None
    operating_capacity: str | None = None


class GAFlightListResponse(BaseModel):
    items: list[GAFlightSummary]
    total_count: int
    page: int
    per_page: int
    total_pages: int


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
