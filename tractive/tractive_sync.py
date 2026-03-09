#!/usr/bin/env python3
"""Sync GPS points from Tractive API to the database."""

import argparse
import sys
from datetime import datetime, timedelta, timezone

import requests

import config
import db

API_BASE = "https://graph.tractive.com/4"
CLIENT_ID = "625e533dc3c3b41c28a669f0"

DEVICE_ID = "tractive-frida"
DEVICE_NAME = "Frida"
SOURCE_TYPE = "tractive"


def authenticate(email, password):
    """Authenticate with Tractive and return access token."""
    resp = requests.post(
        f"{API_BASE}/auth/token",
        json={
            "platform_email": email,
            "platform_token": password,
            "grant_type": "tractive",
        },
        headers={"x-tractive-client": CLIENT_ID},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_positions(session, token, tracker_id, time_from, time_to):
    """Fetch positions for a tracker in a time range (unix timestamps)."""
    resp = session.get(
        f"{API_BASE}/tracker/{tracker_id}/positions",
        params={
            "time_from": int(time_from),
            "time_to": int(time_to),
            "format": "json_segments",
        },
        headers={
            "x-tractive-client": CLIENT_ID,
            "authorization": f"Bearer {token}",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def flatten_positions(raw):
    """Flatten segment format into a flat list of position dicts.

    API returns [[{point}, ...], ...] — a list of segments,
    where each segment is a list of position dicts.
    """
    if not raw:
        return []
    points = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, list):
                # Segment: list of position dicts
                points.extend(item)
            elif isinstance(item, dict):
                if "positions" in item:
                    # Alternative format: [{"positions": [...]}]
                    points.extend(item["positions"])
                else:
                    # Flat position dict
                    points.append(item)
    return points


def position_to_db(pos):
    """Convert a Tractive position dict to database format."""
    latlong = pos.get("latlong", [None, None])
    speed_ms = pos.get("speed")  # m/s

    ts = pos.get("time")
    if ts is not None:
        ts = datetime.fromtimestamp(ts, tz=timezone.utc)

    return {
        "device_id": DEVICE_ID,
        "device_name": DEVICE_NAME,
        "ts": ts,
        "lat": latlong[0] if len(latlong) > 0 else None,
        "lon": latlong[1] if len(latlong) > 1 else None,
        "altitude_m": pos.get("alt"),
        "altitude_ft": round(pos["alt"] * 3.28084, 2) if pos.get("alt") is not None else None,
        "speed_mph": round(speed_ms * 2.237, 2) if speed_ms is not None else None,
        "speed_kmh": round(speed_ms * 3.6, 2) if speed_ms is not None else None,
        "direction": pos.get("course"),
        "accuracy_m": pos.get("pos_uncertainty"),
        "battery_pct": None,
        "source_type": SOURCE_TYPE,
    }


def get_tracker_ids():
    """Return list of tracker IDs from config."""
    return [t.strip() for t in config.TRACTIVE_TRACKER_IDS.split(",") if t.strip()]


def daily_sync():
    """Sync the last 48 hours of data for all trackers."""
    if not config.TRACTIVE_EMAIL or not config.TRACTIVE_PASSWORD:
        print("Tractive credentials not configured, skipping")
        return

    db.ensure_unique_constraint()

    now = datetime.now(timezone.utc)
    time_from = (now - timedelta(hours=48)).timestamp()
    time_to = now.timestamp()

    tracker_ids = get_tracker_ids()
    print(f"Authenticating with Tractive...", end=" ", flush=True)
    token = authenticate(config.TRACTIVE_EMAIL, config.TRACTIVE_PASSWORD)
    print("OK")

    session = requests.Session()
    total_inserted = 0
    total_skipped = 0

    for tracker_id in tracker_ids:
        print(f"Fetching last 48h for tracker {tracker_id}...", end=" ", flush=True)
        try:
            raw = fetch_positions(session, token, tracker_id, time_from, time_to)
            points = flatten_positions(raw)
            if points:
                db_points = [position_to_db(p) for p in points]
                inserted, skipped = db.insert_points(db_points)
                total_inserted += inserted
                total_skipped += skipped
                print(f"{len(points)} points, {inserted} new, {skipped} existing")
            else:
                print("no points")
        except Exception as e:
            print(f"error: {e}")

    print(f"Tractive daily sync complete: {total_inserted} inserted, {total_skipped} duplicates")


def backfill(days):
    """Backfill the last N days in 7-day chunks for all trackers."""
    if not config.TRACTIVE_EMAIL or not config.TRACTIVE_PASSWORD:
        print("Tractive credentials not configured, skipping")
        return

    db.ensure_unique_constraint()

    now = datetime.now(timezone.utc)
    tracker_ids = get_tracker_ids()

    print(f"Authenticating with Tractive...", end=" ", flush=True)
    token = authenticate(config.TRACTIVE_EMAIL, config.TRACTIVE_PASSWORD)
    print("OK")

    session = requests.Session()
    total_inserted = 0
    total_skipped = 0

    for tracker_id in tracker_ids:
        print(f"\nBackfilling tracker {tracker_id} ({days} days)...")

        end = now
        earliest = now - timedelta(days=days)

        while end > earliest:
            start = max(end - timedelta(days=7), earliest)
            date_label = f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"
            print(f"  {date_label}...", end=" ", flush=True)

            try:
                raw = fetch_positions(session, token, tracker_id, start.timestamp(), end.timestamp())
                points = flatten_positions(raw)
                if points:
                    db_points = [position_to_db(p) for p in points]
                    inserted, skipped = db.insert_points(db_points)
                    total_inserted += inserted
                    total_skipped += skipped
                    print(f"{len(points)} points, {inserted} inserted, {skipped} duplicates")
                else:
                    print("no points")
            except Exception as e:
                print(f"error: {e}")

            end = start

    print(f"\nBackfill complete: {total_inserted} inserted, {total_skipped} duplicates")


def main():
    parser = argparse.ArgumentParser(description="Sync Tractive GPS data")
    parser.add_argument("--backfill", type=int, metavar="DAYS",
                        help="Backfill the last N days")
    parser.add_argument("--daily", action="store_true",
                        help="Run daily sync (last 48 hours)")

    args = parser.parse_args()

    if args.backfill:
        backfill(days=args.backfill)
    elif args.daily:
        daily_sync()
    else:
        daily_sync()


if __name__ == "__main__":
    main()
