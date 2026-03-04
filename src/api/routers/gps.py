"""GPS points endpoints."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from src.api.deps import get_conn
from src.api.models import GpsBoundsResponse, GpsPoint, GpsPointsResponse

router = APIRouter(prefix="/gps")

MAX_POINTS = 5000


@router.get("/points", response_model=GpsPointsResponse)
def get_points(
    start: date = Query(..., description="Start date (inclusive)"),
    end: date = Query(..., description="End date (inclusive)"),
    conn=Depends(get_conn),
):
    cur = conn.cursor()

    # End date is inclusive — query up to start of next day
    end_exclusive = end + timedelta(days=1)

    # Get total count for the range
    cur.execute(
        "SELECT count(*) FROM gps_points WHERE ts >= %s AND ts < %s",
        (start, end_exclusive),
    )
    total_count = cur.fetchone()[0]

    if total_count == 0:
        return GpsPointsResponse(
            points=[], total_count=0, returned_count=0, simplified=False
        )

    # Sample every Nth point if over threshold
    simplified = total_count > MAX_POINTS
    if simplified:
        nth = total_count // MAX_POINTS + 1
        cur.execute(
            """
            SELECT lat, lon, ts, speed_mph, altitude_m
            FROM (
                SELECT lat, lon, ts, speed_mph, altitude_m,
                       row_number() OVER (ORDER BY ts) AS rn
                FROM gps_points
                WHERE ts >= %s AND ts < %s
            ) sub
            WHERE rn %% %s = 1
            ORDER BY ts
            """,
            (start, end_exclusive, nth),
        )
    else:
        cur.execute(
            """
            SELECT lat, lon, ts, speed_mph, altitude_m
            FROM gps_points
            WHERE ts >= %s AND ts < %s
            ORDER BY ts
            """,
            (start, end_exclusive),
        )

    points = [
        GpsPoint(lat=r[0], lon=r[1], ts=r[2], speed_mph=r[3], altitude_m=r[4])
        for r in cur.fetchall()
    ]
    cur.close()

    return GpsPointsResponse(
        points=points,
        total_count=total_count,
        returned_count=len(points),
        simplified=simplified,
    )


@router.get("/bounds", response_model=GpsBoundsResponse)
def get_bounds(conn=Depends(get_conn)):
    cur = conn.cursor()
    cur.execute("SELECT min(ts)::date, max(ts)::date, count(*) FROM gps_points")
    row = cur.fetchone()
    cur.close()

    return GpsBoundsResponse(
        earliest=row[0],
        latest=row[1],
        total_points=row[2],
    )
