"""Strava sync — fetches activities, inserts GPS points, posts to journal ingest."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psycopg2
from psycopg2.extras import execute_values

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from strava.client import StravaClient
from strava.models import strava_to_ingest_payload

# State file for incremental sync
STATE_FILE = Path(__file__).resolve().parent.parent / ".strava_last_sync"

# Strava config (from env)
STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID", "")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET", "")
STRAVA_REFRESH_TOKEN = os.environ.get("STRAVA_REFRESH_TOKEN", "")

# Journal ingest config (from env)
JOURNAL_API_URL = os.environ.get("JOURNAL_API_URL", "http://localhost:8000")
JOURNAL_PIPELINE_SECRET = os.environ.get("JOURNAL_PIPELINE_SECRET", "")

# GPS points device identity
DEVICE_ID = "strava"
DEVICE_NAME = "strava"
SOURCE_TYPE = "strava"


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google encoded polyline into list of (lat, lon) tuples."""
    points = []
    index = 0
    lat = 0
    lon = 0
    while index < len(encoded):
        # Decode latitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lat += (~(result >> 1) if result & 1 else result >> 1)

        # Decode longitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lon += (~(result >> 1) if result & 1 else result >> 1)

        points.append((lat / 1e5, lon / 1e5))
    return points


def get_db_connection():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        sslmode="require",
    )


def ensure_strava_table(conn):
    """Create strava_activities table if it doesn't exist."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS strava_activities (
            id bigint PRIMARY KEY,
            map_polyline text,
            start_lat float,
            start_lon float,
            synced_at timestamptz DEFAULT now()
        )
    """)
    conn.commit()
    cur.close()


def insert_gps_points(conn, activity: dict):
    """Decode polyline and insert GPS breadcrumbs into gps_points."""
    polyline = (activity.get("map") or {}).get("summary_polyline")
    if not polyline:
        return 0

    points = decode_polyline(polyline)
    if not points:
        return 0

    # Distribute timestamps evenly across moving_time
    start_date = activity.get("start_date")
    moving_time = activity.get("moving_time", 0)
    if not start_date or not moving_time or len(points) < 2:
        return 0

    start_ts = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    interval = moving_time / (len(points) - 1) if len(points) > 1 else 0

    rows = []
    for i, (lat, lon) in enumerate(points):
        ts = start_ts.timestamp() + (i * interval)
        ts_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        rows.append({
            "device_id": DEVICE_ID,
            "device_name": DEVICE_NAME,
            "ts": ts_dt,
            "lat": lat,
            "lon": lon,
            "altitude_m": None,
            "altitude_ft": None,
            "speed_mph": None,
            "speed_kmh": None,
            "direction": None,
            "accuracy_m": None,
            "battery_pct": None,
            "source_type": SOURCE_TYPE,
        })

    cur = conn.cursor()
    sql = """
        INSERT INTO gps_points (
            device_id, device_name, ts, lat, lon, altitude_m, altitude_ft,
            speed_mph, speed_kmh, direction, accuracy_m, battery_pct, source_type, geom
        ) VALUES %s
        ON CONFLICT (device_id, ts) DO NOTHING
    """
    template = """(
        %(device_id)s, %(device_name)s, %(ts)s, %(lat)s, %(lon)s,
        %(altitude_m)s, %(altitude_ft)s, %(speed_mph)s, %(speed_kmh)s,
        %(direction)s, %(accuracy_m)s, %(battery_pct)s, %(source_type)s,
        ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
    )"""
    execute_values(cur, sql, rows, template=template)
    inserted = cur.rowcount
    cur.close()
    return inserted


def upsert_strava_activity(conn, activity: dict):
    """Store raw polyline + start coords in strava_activities table."""
    polyline = (activity.get("map") or {}).get("summary_polyline")
    start_latlng = activity.get("start_latlng") or [None, None]
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO strava_activities (id, map_polyline, start_lat, start_lon, synced_at)
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (id) DO UPDATE SET
            map_polyline = EXCLUDED.map_polyline,
            start_lat = EXCLUDED.start_lat,
            start_lon = EXCLUDED.start_lon,
            synced_at = now()
    """, (activity["id"], polyline, start_latlng[0], start_latlng[1]))
    cur.close()


def post_to_journal(activities: list[dict]):
    """POST non-GPS activity data to journal ingest endpoint."""
    payloads = []
    for act in activities:
        payload = strava_to_ingest_payload(act)
        if payload is not None:
            payloads.append(payload)

    if not payloads:
        print("  No activities to ingest (all skipped)")
        return

    # Batch in groups of 50
    for i in range(0, len(payloads), 50):
        batch = payloads[i:i + 50]
        resp = httpx.post(
            f"{JOURNAL_API_URL}/api/v1/activities/ingest",
            json={"activities": batch},
            headers={"Authorization": f"Bearer {JOURNAL_PIPELINE_SECRET}"},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        print(f"  Journal ingest: {result['created']} created, {result['updated']} updated")


def read_last_sync() -> int | None:
    """Read last sync timestamp from state file."""
    if STATE_FILE.exists():
        text = STATE_FILE.read_text().strip()
        if text:
            return int(text)
    return None


def write_last_sync(ts: int):
    """Write last sync timestamp to state file."""
    STATE_FILE.write_text(str(ts))


def sync(seed: bool = False):
    """Main sync entry point."""
    if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET or not STRAVA_REFRESH_TOKEN:
        print("ERROR: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, and STRAVA_REFRESH_TOKEN must be set")
        sys.exit(1)
    if not JOURNAL_PIPELINE_SECRET:
        print("ERROR: JOURNAL_PIPELINE_SECRET must be set")
        sys.exit(1)

    client = StravaClient(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN)
    conn = get_db_connection()
    ensure_strava_table(conn)

    try:
        after = None if seed else read_last_sync()
        sync_start = int(time.time())

        if after:
            print(f"Incremental sync: fetching activities after {datetime.fromtimestamp(after, tz=timezone.utc).isoformat()}")
        else:
            print("Full seed: fetching all activities")

        activities = client.get_all_activities(after=after)
        print(f"Fetched {len(activities)} activities from Strava")

        if not activities:
            print("Nothing to sync")
            write_last_sync(sync_start)
            return

        total_gps = 0
        for act in activities:
            gps_count = insert_gps_points(conn, act)
            upsert_strava_activity(conn, act)
            total_gps += gps_count
        conn.commit()
        print(f"GPS: inserted {total_gps} points into gps_points")

        post_to_journal(activities)
        write_last_sync(sync_start)
        print("Sync complete")

    finally:
        conn.close()
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Strava activities")
    parser.add_argument("--seed", action="store_true", help="Full seed (fetch all history)")
    args = parser.parse_args()
    sync(seed=args.seed)
