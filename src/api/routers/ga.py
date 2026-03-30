"""GA flying endpoints — logbook list, detail, update, images."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from src.api.deps import get_conn
from src.api.images import (
    aircraft_image_path,
    has_aircraft_image,
    has_route_image,
    route_image_path,
    schedule_prefetch,
)
from src.api.models import GAFlightDetail, GAFlightListResponse, GAFlightSummary, GAFlightUpdate

router = APIRouter(prefix="/ga")


def _format_time(t) -> str | None:
    if t is None:
        return None
    return t.strftime("%H:%M")


def _to_float(v) -> float | None:
    if v is None:
        return None
    return float(v)


# --- List ---

LIST_SQL = """
    SELECT id, date, aircraft_type, registration, captain, operating_capacity,
           dep_airport, arr_airport, dep_time, arr_time, hours_total, exercise
    FROM ga_flights
    ORDER BY date DESC, dep_time ASC NULLS LAST
    LIMIT %s OFFSET %s
"""

COUNT_SQL = "SELECT count(*) FROM ga_flights"

# GA airports use ICAO codes — we need coordinates for images.
# Cache a lookup from the OpenFlights database at module level.
_icao_coords: dict[str, tuple[float, float]] | None = None


def _get_icao_coords(conn) -> dict[str, tuple[float, float]]:
    """Lazy-load ICAO → (lat, lon) from the airports module."""
    global _icao_coords
    if _icao_coords is not None:
        return _icao_coords

    try:
        from flights.airports import load_airports
        airports = load_airports()
        _icao_coords = {}
        for info in airports.values():
            icao = info.get("icao")
            if icao:
                _icao_coords[icao] = (info["lat"], info["lon"])
    except Exception:
        _icao_coords = {}
    return _icao_coords


@router.get("/", response_model=GAFlightListResponse)
def list_ga_flights(
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

    coords = _get_icao_coords(conn)
    items = []
    prefetch_batch = []

    for r in rows:
        dep_apt, arr_apt, reg = r[6], r[7], r[3]
        is_local = dep_apt and arr_apt and dep_apt == arr_apt

        dep_coord = coords.get(dep_apt) if dep_apt else None
        arr_coord = coords.get(arr_apt) if arr_apt else None

        if dep_apt and arr_apt and dep_coord and arr_coord:
            prefetch_batch.append({
                "dep_airport": dep_apt, "arr_airport": arr_apt,
                "dep_lat": dep_coord[0], "dep_lon": dep_coord[1],
                "arr_lat": arr_coord[0], "arr_lon": arr_coord[1],
                "registration": reg,
            })

        items.append(GAFlightSummary(
            id=r[0],
            date=r[1],
            aircraft_type=r[2],
            registration=reg,
            captain=r[4],
            operating_capacity=r[5],
            dep_airport=dep_apt,
            arr_airport=arr_apt,
            dep_time=_format_time(r[8]),
            arr_time=_format_time(r[9]),
            hours_total=_to_float(r[10]),
            exercise=r[11],
            is_local=is_local,
            has_route_image=has_route_image(dep_apt, arr_apt),
            has_aircraft_image=has_aircraft_image(reg),
        ))

    schedule_prefetch(prefetch_batch)

    return GAFlightListResponse(
        items=items,
        total_count=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


# --- Detail ---

DETAIL_SQL = """
    SELECT id, date, aircraft_type, registration, captain, operating_capacity,
           dep_airport, arr_airport, dep_time, arr_time,
           hours_sep_pic, hours_sep_dual, hours_mep_pic, hours_mep_dual,
           hours_pic_3, hours_dual_3, hours_pic_4, hours_dual_4,
           hours_instrument, hours_as_instructor, hours_simulator, hours_total,
           instructor, exercise, comments
    FROM ga_flights WHERE id = %s
"""


@router.get("/{flight_id}", response_model=GAFlightDetail)
def get_ga_flight(flight_id: int, conn=Depends(get_conn)):
    cur = conn.cursor()
    cur.execute(DETAIL_SQL, (flight_id,))
    r = cur.fetchone()
    cur.close()

    if not r:
        raise HTTPException(404, "GA flight not found")

    dep_apt, arr_apt = r[6], r[7]

    return GAFlightDetail(
        id=r[0], date=r[1], aircraft_type=r[2], registration=r[3],
        captain=r[4], operating_capacity=r[5],
        dep_airport=dep_apt, arr_airport=arr_apt,
        dep_time=_format_time(r[8]), arr_time=_format_time(r[9]),
        hours_sep_pic=_to_float(r[10]), hours_sep_dual=_to_float(r[11]),
        hours_mep_pic=_to_float(r[12]), hours_mep_dual=_to_float(r[13]),
        hours_pic_3=_to_float(r[14]), hours_dual_3=_to_float(r[15]),
        hours_pic_4=_to_float(r[16]), hours_dual_4=_to_float(r[17]),
        hours_instrument=_to_float(r[18]), hours_as_instructor=_to_float(r[19]),
        hours_simulator=_to_float(r[20]), hours_total=_to_float(r[21]),
        instructor=r[22], exercise=r[23], comments=r[24],
        is_local=dep_apt and arr_apt and dep_apt == arr_apt,
        has_route_image=has_route_image(dep_apt, arr_apt),
        has_aircraft_image=has_aircraft_image(r[3]),
    )


# --- Update ---

UPDATABLE_FIELDS = {"comments", "exercise", "captain", "operating_capacity"}


@router.patch("/{flight_id}", response_model=GAFlightDetail)
def update_ga_flight(flight_id: int, update: GAFlightUpdate, conn=Depends(get_conn)):
    changes = {k: v for k, v in update.model_dump(exclude_unset=True).items() if k in UPDATABLE_FIELDS}
    if not changes:
        raise HTTPException(400, "No valid fields to update")

    set_clause = ", ".join(f"{k} = %({k})s" for k in changes)
    changes["id"] = flight_id

    cur = conn.cursor()
    cur.execute(f"UPDATE ga_flights SET {set_clause} WHERE id = %(id)s RETURNING id", changes)
    row = cur.fetchone()
    conn.commit()
    cur.close()

    if not row:
        raise HTTPException(404, "GA flight not found")

    return get_ga_flight(flight_id, conn)


# --- Images ---


@router.get("/{flight_id}/images/{image_type}/{size}")
def get_ga_flight_image(
    flight_id: int,
    image_type: str,
    size: str,
    conn=Depends(get_conn),
):
    if image_type not in ("route", "aircraft"):
        raise HTTPException(400, "image_type must be 'route' or 'aircraft'")
    if size not in ("thumb", "full"):
        raise HTTPException(400, "size must be 'thumb' or 'full'")

    cur = conn.cursor()
    cur.execute("SELECT dep_airport, arr_airport, registration FROM ga_flights WHERE id = %s", (flight_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        raise HTTPException(404, "GA flight not found")

    if image_type == "route":
        if not row[0] or not row[1]:
            raise HTTPException(404, "No airports for this flight")
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
