"""Flights endpoints — ingest from pipeline, list, detail, update, images."""

import math
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.api.deps import get_conn
from src.api.images import (
    aircraft_image_path,
    has_aircraft_image,
    has_route_image,
    route_image_path,
    schedule_prefetch,
)
from src.api.models import FlightDetail, FlightListResponse, FlightSummary, FlightUpdate
from src.api.settings import settings

router = APIRouter(prefix="/flights")


# --- Auth ---


def _check_pipeline_auth(authorization: str = Header(...)):
    expected = settings.pipeline_secret
    if not expected:
        raise HTTPException(503, "Pipeline endpoint not configured")
    if not authorization.startswith("Bearer "):
        raise HTTPException(403, "Invalid credentials")
    if not secrets.compare_digest(authorization[7:], expected):
        raise HTTPException(403, "Invalid credentials")


# --- Ingest ---

_CABIN_CLASS_MAP = {"economy": 1, "business": 2, "first": 3}


class FlightIngest(BaseModel):
    date: str
    dep_airport: str
    arr_airport: str
    flight_number: str | None = None
    airline: str | None = None
    seat_number: str | None = None
    cabin_class: str | None = None
    source: str = "pipeline"


INSERT_SQL = """
    INSERT INTO flights (date, dep_airport, arr_airport, flight_number, airline, seat_number, flight_class, source)
    VALUES (%(date)s, %(dep_airport)s, %(arr_airport)s, %(flight_number)s, %(airline)s, %(seat_number)s, %(flight_class)s, %(source)s)
    ON CONFLICT (date, dep_airport, arr_airport, flight_number) DO NOTHING
    RETURNING id
"""


@router.post("/ingest")
async def ingest_flight(
    flight: FlightIngest,
    conn=Depends(get_conn),
    _=Depends(_check_pipeline_auth),
):
    """Ingest a flight record from the pipeline."""
    params = flight.model_dump()
    params["flight_class"] = _CABIN_CLASS_MAP.get((params.pop("cabin_class") or "").lower())
    cur = conn.cursor()
    cur.execute(INSERT_SQL, params)
    row = cur.fetchone()
    conn.commit()
    cur.close()

    if row:
        return {"status": "created", "id": row[0]}
    return {"status": "duplicate"}


# --- List ---

LIST_SQL = """
    SELECT id, date, dep_airport, arr_airport, dep_airport_name, arr_airport_name,
           flight_number, airline, aircraft_type, registration, duration,
           distance_km, flight_class, seat_number, notes,
           dep_lat, dep_lon, arr_lat, arr_lon
    FROM flights
    ORDER BY date DESC, dep_time ASC NULLS LAST
    LIMIT %s OFFSET %s
"""

COUNT_SQL = "SELECT count(*) FROM flights"


def _format_duration(interval) -> str | None:
    """Convert a psycopg2 timedelta (from INTERVAL) to HH:MM string."""
    if interval is None:
        return None
    total_seconds = int(interval.total_seconds())
    hours, remainder = divmod(abs(total_seconds), 3600)
    minutes = remainder // 60
    return f"{hours}h{minutes:02d}m"


@router.get("/", response_model=FlightListResponse)
def list_flights(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    conn=Depends(get_conn),
):
    cur = conn.cursor()

    cur.execute(COUNT_SQL)
    total_count = cur.fetchone()[0]
    total_pages = max(1, math.ceil(total_count / per_page))

    offset = (page - 1) * per_page
    cur.execute(LIST_SQL, (per_page, offset))
    rows = cur.fetchall()
    cur.close()

    items = []
    prefetch_batch = []
    for r in rows:
        fid = r[0]
        dep_apt, arr_apt = r[2], r[3]
        reg = r[9]
        flight_dict = {
            "id": fid, "dep_airport": dep_apt, "arr_airport": arr_apt,
            "dep_lat": r[15], "dep_lon": r[16],
            "arr_lat": r[17], "arr_lon": r[18], "registration": reg,
        }
        prefetch_batch.append(flight_dict)

        items.append(FlightSummary(
            id=fid,
            date=r[1],
            dep_airport=dep_apt,
            arr_airport=arr_apt,
            dep_airport_name=r[4],
            arr_airport_name=r[5],
            flight_number=r[6],
            airline=r[7],
            aircraft_type=r[8],
            registration=reg,
            duration=_format_duration(r[10]),
            distance_km=r[11],
            flight_class=r[12],
            seat_number=r[13],
            notes=r[14],
            has_route_image=has_route_image(dep_apt, arr_apt),
            has_aircraft_image=has_aircraft_image(reg),
        ))

    # Trigger background prefetch for missing images
    schedule_prefetch(prefetch_batch)

    return FlightListResponse(
        items=items,
        total_count=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


# --- Detail ---

DETAIL_SQL = """
    SELECT id, date, flight_number, dep_airport, dep_airport_name, dep_icao,
           arr_airport, arr_airport_name, arr_icao,
           dep_time, arr_time, duration,
           airline, airline_code, aircraft_type, aircraft_code, registration,
           gate_origin, gate_destination, terminal_origin, terminal_destination, baggage_claim,
           departure_delay, arrival_delay,
           route_distance, runway_origin, runway_destination, codeshares,
           seat_number, seat_type, flight_class, flight_reason,
           notes, source, gps_matched,
           dep_lat, dep_lon, arr_lat, arr_lon, distance_km
    FROM flights WHERE id = %s
"""


def _format_time(t) -> str | None:
    if t is None:
        return None
    return t.strftime("%H:%M")


@router.get("/{flight_id}", response_model=FlightDetail)
def get_flight(flight_id: int, conn=Depends(get_conn)):
    cur = conn.cursor()
    cur.execute(DETAIL_SQL, (flight_id,))
    r = cur.fetchone()
    cur.close()

    if not r:
        raise HTTPException(404, "Flight not found")

    return FlightDetail(
        id=r[0], date=r[1], flight_number=r[2],
        dep_airport=r[3], dep_airport_name=r[4], dep_icao=r[5],
        arr_airport=r[6], arr_airport_name=r[7], arr_icao=r[8],
        dep_time=_format_time(r[9]), arr_time=_format_time(r[10]),
        duration=_format_duration(r[11]),
        airline=r[12], airline_code=r[13], aircraft_type=r[14],
        aircraft_code=r[15], registration=r[16],
        gate_origin=r[17], gate_destination=r[18],
        terminal_origin=r[19], terminal_destination=r[20],
        baggage_claim=r[21],
        departure_delay=r[22], arrival_delay=r[23],
        route_distance=r[24], runway_origin=r[25],
        runway_destination=r[26], codeshares=r[27],
        seat_number=r[28], seat_type=r[29], flight_class=r[30],
        flight_reason=r[31],
        notes=r[32], source=r[33], gps_matched=r[34],
        dep_lat=r[35], dep_lon=r[36], arr_lat=r[37], arr_lon=r[38],
        distance_km=r[39],
        has_route_image=has_route_image(r[3], r[6]),
        has_aircraft_image=has_aircraft_image(r[16]),
    )


# --- Update ---

UPDATABLE_FIELDS = {
    "notes", "seat_number", "seat_type", "flight_class", "flight_reason",
    "registration", "aircraft_type", "flight_number", "airline",
}


@router.patch("/{flight_id}", response_model=FlightDetail)
def update_flight(flight_id: int, update: FlightUpdate, conn=Depends(get_conn)):
    changes = {k: v for k, v in update.model_dump(exclude_unset=True).items() if k in UPDATABLE_FIELDS}
    if not changes:
        raise HTTPException(400, "No valid fields to update")

    set_clause = ", ".join(f"{k} = %({k})s" for k in changes)
    changes["id"] = flight_id

    cur = conn.cursor()
    cur.execute(f"UPDATE flights SET {set_clause} WHERE id = %(id)s RETURNING id", changes)
    row = cur.fetchone()
    conn.commit()
    cur.close()

    if not row:
        raise HTTPException(404, "Flight not found")

    return get_flight(flight_id, conn)


# --- Images ---


@router.get("/{flight_id}/images/{image_type}/{size}")
def get_flight_image(
    flight_id: int,
    image_type: str,
    size: str,
    conn=Depends(get_conn),
):
    if image_type not in ("route", "aircraft"):
        raise HTTPException(400, "image_type must be 'route' or 'aircraft'")
    if size not in ("thumb", "full"):
        raise HTTPException(400, "size must be 'thumb' or 'full'")

    # Look up flight for airport pair / registration
    cur = conn.cursor()
    cur.execute("SELECT dep_airport, arr_airport, registration FROM flights WHERE id = %s", (flight_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        raise HTTPException(404, "Flight not found")

    if image_type == "route":
        path = route_image_path(row[0], row[1], size)
        media_type = "image/png"
    else:
        if not row[2]:
            raise HTTPException(404, "No registration for this flight")
        path = aircraft_image_path(row[2], size)
        media_type = "image/jpeg"

    if not path.exists():
        raise HTTPException(404, "Image not yet available")

    return FileResponse(path, media_type=media_type)


# --- Bulk prefetch ---


@router.post("/images/prefetch-all")
def prefetch_all_images(conn=Depends(get_conn)):
    """Trigger background prefetch for all flights missing images."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, dep_airport, arr_airport, dep_lat, dep_lon, arr_lat, arr_lon, registration FROM flights"
    )
    rows = cur.fetchall()
    cur.close()

    batch = [
        {"id": r[0], "dep_airport": r[1], "arr_airport": r[2],
         "dep_lat": r[3], "dep_lon": r[4], "arr_lat": r[5], "arr_lon": r[6], "registration": r[7]}
        for r in rows
    ]
    schedule_prefetch(batch)
    return {"status": "prefetch_scheduled", "count": len(batch)}
