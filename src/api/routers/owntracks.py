"""OwnTracks HTTP endpoint — receives location publishes from the OwnTracks app."""

import base64
import json
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from psycopg2.extras import execute_values

from src.api.deps import get_conn
from src.api.settings import settings

router = APIRouter()

M_TO_FT = 3.28084
KMH_TO_MPH = 0.621371


def _check_auth(
    authorization: str | None = Header(None),
    u: str | None = Query(None),
    p: str | None = Query(None),
):
    """Validate shared secret via Basic auth header or query params."""
    expected = settings.owntracks_secret
    if not expected:
        raise HTTPException(503, "OwnTracks endpoint not configured")

    # OwnTracks sends Basic <base64(user:password)> — we only check the password
    if authorization and authorization.startswith("Basic "):
        try:
            decoded = base64.b64decode(authorization[6:]).decode()
            _, _, password = decoded.partition(":")
            if secrets.compare_digest(password, expected):
                return
        except Exception:
            pass

    # Fallback: query params ?u=...&p=...
    if p and secrets.compare_digest(p, expected):
        return

    raise HTTPException(403, "Invalid credentials")


def _location_to_point(payload: dict) -> dict | None:
    """Convert an OwnTracks location payload to a gps_points dict."""
    if payload.get("_type") != "location":
        return None

    lat = payload.get("lat")
    lon = payload.get("lon")
    tst = payload.get("tst")
    if lat is None or lon is None or tst is None:
        return None

    alt = payload.get("alt")
    vel = payload.get("vel")

    return {
        "device_id": f"owntracks-{payload.get('tid', 'unknown')}".lower(),
        "device_name": "OwnTracks",
        "ts": datetime.fromtimestamp(tst, tz=UTC),
        "lat": lat,
        "lon": lon,
        "altitude_m": alt,
        "altitude_ft": round(alt * M_TO_FT, 1) if alt is not None else None,
        "speed_kmh": vel,
        "speed_mph": round(vel * KMH_TO_MPH, 1) if vel is not None else None,
        "direction": payload.get("cog"),
        "accuracy_m": payload.get("acc"),
        "battery_pct": payload.get("batt"),
        "source_type": "owntracks",
    }


INSERT_SQL = """
    INSERT INTO gps_points (
        device_id, device_name, ts, lat, lon, altitude_m, altitude_ft,
        speed_mph, speed_kmh, direction, accuracy_m, battery_pct, source_type, geom
    ) VALUES %s
    ON CONFLICT (device_id, ts) DO NOTHING
"""

INSERT_TEMPLATE = """(
    %(device_id)s, %(device_name)s, %(ts)s, %(lat)s, %(lon)s,
    %(altitude_m)s, %(altitude_ft)s, %(speed_mph)s, %(speed_kmh)s,
    %(direction)s, %(accuracy_m)s, %(battery_pct)s, %(source_type)s,
    ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
)"""


@router.post("/pub")
async def publish(request: Request, conn=Depends(get_conn), _=Depends(_check_auth)):
    """Receive an OwnTracks location publish and store it."""
    body = await request.body()
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return []

    point = _location_to_point(payload)
    if point:
        cur = conn.cursor()
        execute_values(cur, INSERT_SQL, [point], template=INSERT_TEMPLATE)
        conn.commit()
        cur.close()

    return []
