"""Flights endpoints — ingest from pipeline + future queries."""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from src.api.deps import get_conn
from src.api.settings import settings

router = APIRouter(prefix="/flights")


def _check_pipeline_auth(authorization: str = Header(...)):
    expected = settings.pipeline_secret
    if not expected:
        raise HTTPException(503, "Pipeline endpoint not configured")
    if not authorization.startswith("Bearer "):
        raise HTTPException(403, "Invalid credentials")
    if not secrets.compare_digest(authorization[7:], expected):
        raise HTTPException(403, "Invalid credentials")


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
