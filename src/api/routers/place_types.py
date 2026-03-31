"""Place type endpoints — CRUD for location type reference data."""

import psycopg2

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_conn
from src.api.models import PlaceTypeCreate, PlaceTypeListResponse, PlaceTypeResponse

router = APIRouter(prefix="/place-types")


@router.post("/", response_model=PlaceTypeResponse, status_code=201)
def create_place_type(body: PlaceTypeCreate, conn=Depends(get_conn)):
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO place_type (name) VALUES (%s) RETURNING id, name",
            (body.name,),
        )
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(409, f"Place type '{body.name}' already exists")
    row = cur.fetchone()
    conn.commit()
    cur.close()
    return PlaceTypeResponse(id=row[0], name=row[1])


@router.get("/", response_model=PlaceTypeListResponse)
def list_place_types(conn=Depends(get_conn)):
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM place_type ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    return PlaceTypeListResponse(
        items=[PlaceTypeResponse(id=r[0], name=r[1]) for r in rows],
        total_count=len(rows),
    )


@router.get("/{type_id}", response_model=PlaceTypeResponse)
def get_place_type(type_id: int, conn=Depends(get_conn)):
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM place_type WHERE id = %s", (type_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        raise HTTPException(404, "Place type not found")
    return PlaceTypeResponse(id=row[0], name=row[1])


@router.patch("/{type_id}", response_model=PlaceTypeResponse)
def update_place_type(type_id: int, body: PlaceTypeCreate, conn=Depends(get_conn)):
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE place_type SET name = %s WHERE id = %s RETURNING id, name",
            (body.name, type_id),
        )
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(409, f"Place type '{body.name}' already exists")
    row = cur.fetchone()
    conn.commit()
    cur.close()
    if not row:
        raise HTTPException(404, "Place type not found")
    return PlaceTypeResponse(id=row[0], name=row[1])


@router.delete("/{type_id}", status_code=204)
def delete_place_type(type_id: int, conn=Depends(get_conn)):
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM place_type WHERE id = %s RETURNING id", (type_id,))
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        raise HTTPException(409, "Cannot delete: places still reference this type")
    row = cur.fetchone()
    conn.commit()
    cur.close()
    if not row:
        raise HTTPException(404, "Place type not found")
