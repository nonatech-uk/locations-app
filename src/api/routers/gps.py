"""GPS points endpoints."""

import math
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from src.api.deps import get_conn
from src.api.models import (
    DailySummaryResponse,
    DayEndpoint,
    GpsBoundsResponse,
    GpsPoint,
    GpsPointsResponse,
)

router = APIRouter(prefix="/gps")

MAX_POINTS = 5000
MAX_SVG_POINTS = 500


@router.get("/points", response_model=GpsPointsResponse)
def get_points(
    start: date = Query(..., description="Start date (inclusive)"),
    end: date = Query(..., description="End date (inclusive)"),
    conn=Depends(get_conn),
):
    cur = conn.cursor()

    # End date is inclusive — query up to start of next day
    end_exclusive = end + timedelta(days=1)

    # Exclude pet trackers (Tractive) by default
    source_filter = "AND source_type != 'tractive'"

    # Get total count for the range
    cur.execute(
        f"SELECT count(*) FROM gps_points WHERE ts >= %s AND ts < %s {source_filter}",
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
            f"""
            SELECT lat, lon, ts, speed_mph, altitude_m
            FROM (
                SELECT lat, lon, ts, speed_mph, altitude_m,
                       row_number() OVER (ORDER BY ts) AS rn
                FROM gps_points
                WHERE ts >= %s AND ts < %s {source_filter}
            ) sub
            WHERE rn %% %s = 1
            ORDER BY ts
            """,
            (start, end_exclusive, nth),
        )
    else:
        cur.execute(
            f"""
            SELECT lat, lon, ts, speed_mph, altitude_m
            FROM gps_points
            WHERE ts >= %s AND ts < %s {source_filter}
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
    cur.execute("SELECT min(ts)::date, max(ts)::date, count(*) FROM gps_points WHERE source_type != 'tractive'")
    row = cur.fetchone()
    cur.close()

    return GpsBoundsResponse(
        earliest=row[0],
        latest=row[1],
        total_points=row[2],
    )


# ---------------------------------------------------------------------------
# Track SVG thumbnail
# ---------------------------------------------------------------------------

SOURCE_FILTER = "AND source_type != 'tractive'"


def _build_track_svg(
    rows: list[tuple[float, float]],
    width: int = 200,
    height: int = 150,
    color: str = "#4f46e5",
    bg: str = "#f8fafc",
) -> str:
    """Build an SVG string from a list of (lat, lon) tuples."""
    if len(rows) == 1:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"'
            f' viewBox="0 0 {width} {height}">'
            f'<rect width="{width}" height="{height}" rx="8" fill="{bg}"/>'
            f'<circle cx="{width // 2}" cy="{height // 2}" r="4" fill="{color}"/>'
            f"</svg>"
        )

    lats = [r[0] for r in rows]
    lons = [r[1] for r in rows]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # Aspect correction using cosine of center latitude
    center_lat_rad = math.radians((min_lat + max_lat) / 2)
    cos_lat = math.cos(center_lat_rad)

    # Convert to projected coordinates (lon scaled by cos_lat)
    proj = [(lon * cos_lat, lat) for lat, lon in rows]
    px = [p[0] for p in proj]
    py = [p[1] for p in proj]
    pmin_x, pmax_x = min(px), max(px)
    pmin_y, pmax_y = min(py), max(py)

    # Handle degenerate bbox (all points at same location)
    span_x = pmax_x - pmin_x
    span_y = pmax_y - pmin_y
    if span_x < 1e-6 and span_y < 1e-6:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"'
            f' viewBox="0 0 {width} {height}">'
            f'<rect width="{width}" height="{height}" rx="8" fill="{bg}"/>'
            f'<circle cx="{width // 2}" cy="{height // 2}" r="4" fill="{color}"/>'
            f"</svg>"
        )

    # Add 10% padding
    pad_x = span_x * 0.1 or 0.0001
    pad_y = span_y * 0.1 or 0.0001
    pmin_x -= pad_x
    pmax_x += pad_x
    pmin_y -= pad_y
    pmax_y += pad_y
    span_x = pmax_x - pmin_x
    span_y = pmax_y - pmin_y

    # Scale to viewport
    scale_x = (width - 1) / span_x
    scale_y = (height - 1) / span_y

    def to_svg(px_val: float, py_val: float) -> tuple[float, float]:
        sx = (px_val - pmin_x) * scale_x
        sy = (pmax_y - py_val) * scale_y  # flip Y
        return round(sx, 1), round(sy, 1)

    pts = [to_svg(p[0], p[1]) for p in proj]
    points_str = " ".join(f"{x},{y}" for x, y in pts)

    sx, sy = pts[0]
    ex, ey = pts[-1]

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
        f'<rect width="{width}" height="{height}" rx="8" fill="{bg}"/>'
        f'<polyline points="{points_str}" fill="none" stroke="{color}"'
        f' stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{sx}" cy="{sy}" r="3" fill="#22c55e"/>'
        f'<circle cx="{ex}" cy="{ey}" r="3" fill="#ef4444"/>'
        f"</svg>"
    )


@router.get("/track-svg")
def get_track_svg(
    date: date = Query(..., description="Date for track"),
    width: int = Query(200, ge=50, le=800),
    height: int = Query(150, ge=50, le=600),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    end_exclusive = date + timedelta(days=1)

    cur.execute(
        f"SELECT count(*) FROM gps_points WHERE ts >= %s AND ts < %s {SOURCE_FILTER}",
        (date, end_exclusive),
    )
    total = cur.fetchone()[0]

    if total == 0:
        cur.close()
        return Response(status_code=204)

    # Simplify if too many points
    if total > MAX_SVG_POINTS:
        nth = total // MAX_SVG_POINTS + 1
        cur.execute(
            f"""SELECT lat, lon FROM (
                    SELECT lat, lon, row_number() OVER (ORDER BY ts) AS rn
                    FROM gps_points
                    WHERE ts >= %s AND ts < %s {SOURCE_FILTER}
                ) sub WHERE rn %% %s = 1
                ORDER BY rn""",
            (date, end_exclusive, nth),
        )
    else:
        cur.execute(
            f"SELECT lat, lon FROM gps_points WHERE ts >= %s AND ts < %s {SOURCE_FILTER} ORDER BY ts",
            (date, end_exclusive),
        )

    rows = cur.fetchall()
    cur.close()

    svg = _build_track_svg(rows, width, height)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


def _decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google encoded polyline into list of (lat, lon) tuples."""
    points = []
    index = 0
    lat = 0
    lon = 0
    while index < len(encoded):
        for attr in ("lat", "lon"):
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if attr == "lat":
                lat += delta
            else:
                lon += delta
        points.append((lat / 1e5, lon / 1e5))
    return points


@router.get("/activity-track-svg")
def get_activity_track_svg(
    strava_id: int = Query(..., description="Strava activity ID"),
    width: int = Query(200, ge=50, le=800),
    height: int = Query(150, ge=50, le=600),
    conn=Depends(get_conn),
):
    """Render an SVG track for a Strava activity from its stored polyline."""
    cur = conn.cursor()
    cur.execute(
        "SELECT map_polyline FROM strava_activities WHERE id = %s",
        (strava_id,),
    )
    row = cur.fetchone()
    cur.close()

    if not row or not row[0]:
        return Response(status_code=204)

    points = _decode_polyline(row[0])
    if not points:
        return Response(status_code=204)

    svg = _build_track_svg(points, width, height, color="#fc4c02")  # Strava orange
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=604800"},
    )


# ---------------------------------------------------------------------------
# Daily summary
# ---------------------------------------------------------------------------

def _lookup_place(cur, lat: float, lon: float, dt: date) -> tuple[str | None, str | None]:
    """Find covering place for a point. Returns (place_name, place_type_name)."""
    cur.execute(
        """SELECT p.name, pt.name AS place_type
           FROM place p
           JOIN place_type pt ON pt.id = p.place_type_id
           WHERE ST_DWithin(p.geom,
                 ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography,
                 p.distance_m)
             AND (p.date_from IS NULL OR p.date_from <= %(dt)s)
             AND (p.date_to IS NULL OR p.date_to >= %(dt)s)
           ORDER BY ST_Distance(p.geom,
                 ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography)
           LIMIT 1""",
        {"lon": lon, "lat": lat, "dt": dt},
    )
    row = cur.fetchone()
    if row:
        return row[0], row[1]
    # Fallback: Nominatim reverse geocode
    try:
        import httpx
        resp = httpx.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 16},
            headers={"User-Agent": "my-locations/1.0 (personal use)"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        name = data.get("display_name", "").split(",")[0].strip()
        return name or None, None
    except Exception:
        return None, None


@router.get("/daily-summary", response_model=DailySummaryResponse)
def get_daily_summary(
    date: date = Query(..., description="Date for summary"),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    end_exclusive = date + timedelta(days=1)

    # Point count
    cur.execute(
        f"SELECT count(*) FROM gps_points WHERE ts >= %s AND ts < %s {SOURCE_FILTER}",
        (date, end_exclusive),
    )
    point_count = cur.fetchone()[0]

    if point_count == 0:
        cur.close()
        return DailySummaryResponse(date=date, point_count=0)

    # First point
    cur.execute(
        f"SELECT lat, lon, ts FROM gps_points WHERE ts >= %s AND ts < %s {SOURCE_FILTER} ORDER BY ts ASC LIMIT 1",
        (date, end_exclusive),
    )
    first = cur.fetchone()

    # Last point
    cur.execute(
        f"SELECT lat, lon, ts FROM gps_points WHERE ts >= %s AND ts < %s {SOURCE_FILTER} ORDER BY ts DESC LIMIT 1",
        (date, end_exclusive),
    )
    last = cur.fetchone()

    start_ep = None
    end_ep = None

    if first:
        pname, ptype = _lookup_place(cur, first[0], first[1], date)
        start_ep = DayEndpoint(lat=first[0], lon=first[1], ts=first[2], place_name=pname, place_type=ptype)

    if last:
        pname, ptype = _lookup_place(cur, last[0], last[1], date)
        end_ep = DayEndpoint(lat=last[0], lon=last[1], ts=last[2], place_name=pname, place_type=ptype)

    cur.close()

    date_str = date.isoformat()
    return DailySummaryResponse(
        date=date,
        point_count=point_count,
        start=start_ep,
        end=end_ep,
        track_svg_url=f"/api/v1/gps/track-svg?date={date_str}",
    )
