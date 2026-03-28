"""OwnTracks HTTP endpoint — receives location publishes from the OwnTracks app."""

import base64
import json
import logging
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from psycopg2.extras import execute_values, Json

from src.api.deps import get_conn
from src.api.settings import settings

router = APIRouter()
logger = logging.getLogger("owntracks")

M_TO_FT = 3.28084
KMH_TO_MPH = 0.621371


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP, preferring Cloudflare headers."""
    return (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or request.client.host
    )


def _check_auth(request: Request, authorization: str | None = Header(None), p: str | None = Query(None)):
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

    # Fallback: query params ?p=...
    if p and secrets.compare_digest(p, expected):
        return

    client_ip = _get_client_ip(request)
    logger.warning("owntracks auth failure from %s", client_ip)
    raise HTTPException(403, "Invalid credentials")


# ---------------------------------------------------------------------------
# Location points → gps_points
# ---------------------------------------------------------------------------

def _location_to_point(payload: dict) -> dict | None:
    """Convert an OwnTracks location payload to a gps_points dict."""
    lat = payload.get("lat")
    lon = payload.get("lon")
    tst = payload.get("tst")
    if lat is None or lon is None or tst is None:
        return None

    alt = payload.get("alt")
    vel = payload.get("vel")
    created = payload.get("created_at")

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
        # New OwnTracks-specific fields
        "battery_status": payload.get("bs"),
        "connection_type": payload.get("conn"),
        "wifi_ssid": payload.get("SSID") or payload.get("wifi"),
        "wifi_bssid": payload.get("BSSID"),
        "vertical_accuracy_m": payload.get("vac"),
        "trigger_type": payload.get("t"),
        "monitoring_mode": payload.get("m"),
        "topic": payload.get("topic"),
        "in_regions": payload.get("inregions"),
        "pressure_kpa": payload.get("p") if isinstance(payload.get("p"), (int, float)) else None,
        "poi": payload.get("poi"),
        "created_at": datetime.fromtimestamp(created, tz=UTC) if created else None,
        "raw_payload": Json(payload),
    }


LOCATION_INSERT_SQL = """
    INSERT INTO gps_points (
        device_id, device_name, ts, lat, lon, altitude_m, altitude_ft,
        speed_mph, speed_kmh, direction, accuracy_m, battery_pct, source_type,
        battery_status, connection_type, wifi_ssid, wifi_bssid,
        vertical_accuracy_m, trigger_type, monitoring_mode, topic,
        in_regions, pressure_kpa, poi, created_at, raw_payload, geom
    ) VALUES %s
    ON CONFLICT (device_id, ts) DO NOTHING
"""

LOCATION_INSERT_TEMPLATE = """(
    %(device_id)s, %(device_name)s, %(ts)s, %(lat)s, %(lon)s,
    %(altitude_m)s, %(altitude_ft)s, %(speed_mph)s, %(speed_kmh)s,
    %(direction)s, %(accuracy_m)s, %(battery_pct)s, %(source_type)s,
    %(battery_status)s, %(connection_type)s, %(wifi_ssid)s, %(wifi_bssid)s,
    %(vertical_accuracy_m)s, %(trigger_type)s, %(monitoring_mode)s, %(topic)s,
    %(in_regions)s, %(pressure_kpa)s, %(poi)s, %(created_at)s, %(raw_payload)s,
    ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
)"""


def _handle_location(payload: dict, conn) -> None:
    point = _location_to_point(payload)
    if not point:
        return
    cur = conn.cursor()
    execute_values(cur, LOCATION_INSERT_SQL, [point], template=LOCATION_INSERT_TEMPLATE)
    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Transition events → owntracks_transitions
# ---------------------------------------------------------------------------

TRANSITION_INSERT_SQL = """
    INSERT INTO owntracks_transitions (device_id, ts, event, region_name, region_id, lat, lon, accuracy_m, raw_payload)
    VALUES %s
    ON CONFLICT (device_id, ts, region_name) DO NOTHING
"""

TRANSITION_INSERT_TEMPLATE = """(
    %(device_id)s, %(ts)s, %(event)s, %(region_name)s, %(region_id)s,
    %(lat)s, %(lon)s, %(accuracy_m)s, %(raw_payload)s
)"""


def _handle_transition(payload: dict, conn) -> None:
    tst = payload.get("tst")
    if tst is None:
        return
    row = {
        "device_id": f"owntracks-{payload.get('tid', 'unknown')}".lower(),
        "ts": datetime.fromtimestamp(tst, tz=UTC),
        "event": payload.get("event"),
        "region_name": payload.get("desc"),
        "region_id": payload.get("rid"),
        "lat": payload.get("lat"),
        "lon": payload.get("lon"),
        "accuracy_m": payload.get("acc"),
        "raw_payload": Json(payload),
    }
    cur = conn.cursor()
    execute_values(cur, TRANSITION_INSERT_SQL, [row], template=TRANSITION_INSERT_TEMPLATE)
    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Waypoints → owntracks_waypoints
# ---------------------------------------------------------------------------

WAYPOINT_INSERT_SQL = """
    INSERT INTO owntracks_waypoints (device_id, ts, region_name, lat, lon, radius_m, raw_payload)
    VALUES %s
    ON CONFLICT (device_id, region_name) DO UPDATE SET
        ts = EXCLUDED.ts, lat = EXCLUDED.lat, lon = EXCLUDED.lon,
        radius_m = EXCLUDED.radius_m, raw_payload = EXCLUDED.raw_payload
"""

WAYPOINT_INSERT_TEMPLATE = """(
    %(device_id)s, %(ts)s, %(region_name)s, %(lat)s, %(lon)s, %(radius_m)s, %(raw_payload)s
)"""


def _handle_waypoint(payload: dict, conn) -> None:
    lat = payload.get("lat")
    lon = payload.get("lon")
    tst = payload.get("tst")
    if lat is None or lon is None or tst is None:
        return
    row = {
        "device_id": f"owntracks-{payload.get('tid', 'unknown')}".lower(),
        "ts": datetime.fromtimestamp(tst, tz=UTC),
        "region_name": payload.get("desc"),
        "lat": lat,
        "lon": lon,
        "radius_m": payload.get("rad"),
        "raw_payload": Json(payload),
    }
    cur = conn.cursor()
    execute_values(cur, WAYPOINT_INSERT_SQL, [row], template=WAYPOINT_INSERT_TEMPLATE)
    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Catch-all for other message types → owntracks_events
# ---------------------------------------------------------------------------

EVENT_INSERT_SQL = """
    INSERT INTO owntracks_events (device_id, message_type, ts, raw_payload)
    VALUES %s
    ON CONFLICT (device_id, ts, message_type) DO NOTHING
"""

EVENT_INSERT_TEMPLATE = """(%(device_id)s, %(message_type)s, %(ts)s, %(raw_payload)s)"""


def _handle_other(payload: dict, conn) -> None:
    msg_type = payload.get("_type", "unknown")
    tst = payload.get("tst")
    if tst is None:
        return
    row = {
        "device_id": f"owntracks-{payload.get('tid', 'unknown')}".lower(),
        "message_type": msg_type,
        "ts": datetime.fromtimestamp(tst, tz=UTC),
        "raw_payload": Json(payload),
    }
    cur = conn.cursor()
    execute_values(cur, EVENT_INSERT_SQL, [row], template=EVENT_INSERT_TEMPLATE)
    conn.commit()
    cur.close()


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@router.post("/pub")
async def publish(request: Request, conn=Depends(get_conn), _=Depends(_check_auth)):
    """Receive an OwnTracks publish and store it."""
    body = await request.body()
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return []

    msg_type = payload.get("_type")
    if msg_type == "location":
        _handle_location(payload, conn)
    elif msg_type == "transition":
        _handle_transition(payload, conn)
    elif msg_type == "waypoint":
        _handle_waypoint(payload, conn)
    elif msg_type is not None:
        _handle_other(payload, conn)

    return []
