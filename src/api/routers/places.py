"""Places endpoints — CRUD for named locations + spatial lookup."""

import math
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_conn
from src.api.models import (
    PlaceCreate,
    PlaceListResponse,
    PlaceLookupResult,
    PlaceSummary,
    PlaceUpdate,
)

router = APIRouter(prefix="/places")

PLACE_COLS = """
    p.id, p.name, p.place_type_id, pt.name AS place_type_name,
    p.lat, p.lon, p.distance_m, p.date_from, p.date_to, p.notes
"""


def _row_to_summary(r) -> PlaceSummary:
    return PlaceSummary(
        id=r[0], name=r[1], place_type_id=r[2], place_type_name=r[3],
        lat=r[4], lon=r[5], distance_m=r[6],
        date_from=r[7], date_to=r[8], notes=r[9],
    )


# --- Create ---


@router.post("/", response_model=PlaceSummary, status_code=201)
def create_place(body: PlaceCreate, conn=Depends(get_conn)):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO place (name, place_type_id, lat, lon, distance_m, date_from, date_to, notes)
           VALUES (%(name)s, %(place_type_id)s, %(lat)s, %(lon)s, %(distance_m)s,
                   %(date_from)s, %(date_to)s, %(notes)s)
           RETURNING id""",
        body.model_dump(),
    )
    place_id = cur.fetchone()[0]
    conn.commit()

    cur.execute(
        f"SELECT {PLACE_COLS} FROM place p JOIN place_type pt ON pt.id = p.place_type_id WHERE p.id = %s",
        (place_id,),
    )
    row = cur.fetchone()
    cur.close()
    return _row_to_summary(row)


# --- List ---


@router.get("/", response_model=PlaceListResponse)
def list_places(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    place_type_id: int | None = Query(None),
    conn=Depends(get_conn),
):
    cur = conn.cursor()

    where = ""
    params: list = []
    if place_type_id is not None:
        where = "WHERE p.place_type_id = %s"
        params.append(place_type_id)

    cur.execute(f"SELECT count(*) FROM place p {where}", params)
    total_count = cur.fetchone()[0]
    total_pages = max(1, math.ceil(total_count / per_page))

    offset = (page - 1) * per_page
    cur.execute(
        f"""SELECT {PLACE_COLS}
            FROM place p JOIN place_type pt ON pt.id = p.place_type_id
            {where}
            ORDER BY p.name
            LIMIT %s OFFSET %s""",
        params + [per_page, offset],
    )
    rows = cur.fetchall()
    cur.close()

    return PlaceListResponse(
        items=[_row_to_summary(r) for r in rows],
        total_count=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


# --- Lookup ---


@router.get("/lookup", response_model=PlaceLookupResult)
def lookup_place(
    lat: float = Query(...),
    lon: float = Query(...),
    dt: date | None = Query(None),
    conn=Depends(get_conn),
):
    """Find the nearest place whose radius covers the given coordinates."""
    cur = conn.cursor()

    date_filter = ""
    params = {"lat": lat, "lon": lon}
    if dt is not None:
        date_filter = "AND (p.date_from IS NULL OR p.date_from <= %(dt)s) AND (p.date_to IS NULL OR p.date_to >= %(dt)s)"
        params["dt"] = dt

    cur.execute(
        f"""SELECT {PLACE_COLS},
                   ST_Distance(p.geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography) AS dist_m
            FROM place p
            JOIN place_type pt ON pt.id = p.place_type_id
            WHERE ST_DWithin(p.geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography, p.distance_m)
            {date_filter}
            ORDER BY dist_m ASC
            LIMIT 1""",
        params,
    )
    row = cur.fetchone()
    cur.close()

    if row:
        return PlaceLookupResult(
            place=_row_to_summary(row),
            distance_m=round(row[10], 1),
            source="places",
        )
    return PlaceLookupResult(source="nominatim")


# --- Detail ---


@router.get("/{place_id}", response_model=PlaceSummary)
def get_place(place_id: int, conn=Depends(get_conn)):
    cur = conn.cursor()
    cur.execute(
        f"SELECT {PLACE_COLS} FROM place p JOIN place_type pt ON pt.id = p.place_type_id WHERE p.id = %s",
        (place_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        raise HTTPException(404, "Place not found")
    return _row_to_summary(row)


# --- Update ---

UPDATABLE_FIELDS = {"name", "place_type_id", "lat", "lon", "distance_m", "date_from", "date_to", "notes"}


@router.patch("/{place_id}", response_model=PlaceSummary)
def update_place(place_id: int, update: PlaceUpdate, conn=Depends(get_conn)):
    changes = {k: v for k, v in update.model_dump(exclude_unset=True).items() if k in UPDATABLE_FIELDS}
    if not changes:
        raise HTTPException(400, "No valid fields to update")

    set_clause = ", ".join(f"{k} = %({k})s" for k in changes)
    changes["id"] = place_id

    cur = conn.cursor()
    cur.execute(f"UPDATE place SET {set_clause} WHERE id = %(id)s RETURNING id", changes)
    row = cur.fetchone()
    conn.commit()
    cur.close()

    if not row:
        raise HTTPException(404, "Place not found")

    return get_place(place_id, conn)


# --- Delete ---


@router.delete("/{place_id}", status_code=204)
def delete_place(place_id: int, conn=Depends(get_conn)):
    cur = conn.cursor()
    cur.execute("DELETE FROM place WHERE id = %s RETURNING id", (place_id,))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    if not row:
        raise HTTPException(404, "Place not found")
