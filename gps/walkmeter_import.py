#!/usr/bin/env python3
"""Import Walkmeter GPS tracks from SQLite backups into gps_points.

Reads Walkmeter app backup databases (SQLite), extracts GPS coordinates
from walking/running activities, and inserts into gps_points with
source_type='walkmeter'.

Usage:
    python gps/walkmeter_import.py [--dir /path/to/walkmeter] [--dry-run]
"""

import argparse
import bisect
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Add parent to path so we can import db
sys.path.insert(0, str(Path(__file__).parent.parent))
import db


def device_id_for_file(filename):
    """Return device_id based on the database filename."""
    lower = filename.lower()
    if lower.startswith("mees"):
        return "walkmeter-mees"
    if "bertram" in lower:
        return "walkmeter-bertram"
    return "walkmeter-stu"


def get_nearest_altitude(time_offset, alt_times, alt_values, max_gap=60.0):
    """Find the nearest altitude value by timeOffset using bisect."""
    if not alt_times:
        return None
    idx = bisect.bisect_left(alt_times, time_offset)
    candidates = []
    if idx < len(alt_times):
        candidates.append(idx)
    if idx > 0:
        candidates.append(idx - 1)
    best = min(candidates, key=lambda i: abs(alt_times[i] - time_offset))
    if abs(alt_times[best] - time_offset) <= max_gap:
        return alt_values[best]
    return None


def process_db(db_path):
    """Process a single Walkmeter SQLite database, returning a list of point dicts."""
    device_id = device_id_for_file(db_path.name)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Check if run table exists
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "run" not in tables or "coordinate" not in tables:
        conn.close()
        return [], 0

    # Get all runs
    runs = conn.execute(
        "SELECT runID, startTime, startTimeZone FROM run ORDER BY startTime"
    ).fetchall()

    points = []
    for run in runs:
        run_id = run["runID"]
        start_time_str = run["startTime"]
        tz_name = run["startTimeZone"]

        # Parse local start time and make timezone-aware
        # Handle both with and without fractional seconds
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                local_start = datetime.strptime(start_time_str, fmt)
                break
            except ValueError:
                continue
        else:
            print(f"  WARNING: Cannot parse startTime '{start_time_str}', skipping run {run_id}")
            continue

        tz = ZoneInfo(tz_name)
        aware_start = local_start.replace(tzinfo=tz)

        # Load altitude data for bisect join
        alt_rows = conn.execute(
            "SELECT timeOffset, altitude FROM altitude WHERE runID = ? ORDER BY timeOffset",
            (run_id,),
        ).fetchall()
        alt_times = [r["timeOffset"] for r in alt_rows]
        alt_values = [r["altitude"] for r in alt_rows]

        # Load coordinates
        coords = conn.execute(
            "SELECT timeOffset, latitude, longitude, speed FROM coordinate WHERE runID = ? ORDER BY sequenceID",
            (run_id,),
        ).fetchall()

        for coord in coords:
            ts = aware_start + timedelta(seconds=coord["timeOffset"])
            speed_ms = coord["speed"]
            altitude = get_nearest_altitude(coord["timeOffset"], alt_times, alt_values)

            points.append({
                "device_id": device_id,
                "device_name": "Walkmeter",
                "ts": ts.isoformat(),
                "lat": coord["latitude"],
                "lon": coord["longitude"],
                "altitude_m": altitude,
                "altitude_ft": None,
                "speed_mph": None,
                "speed_kmh": speed_ms * 3.6 if speed_ms and speed_ms > 0 else None,
                "direction": None,
                "accuracy_m": None,
                "battery_pct": None,
                "source_type": "walkmeter",
            })

    conn.close()
    return points, len(runs)


def main():
    parser = argparse.ArgumentParser(description="Import Walkmeter GPS data")
    parser.add_argument(
        "--dir",
        default="/zfs/tank/home/stu/walkmeter",
        help="Path to Walkmeter backup directory",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no DB writes")
    args = parser.parse_args()

    walkmeter_dir = Path(args.dir)
    if not walkmeter_dir.is_dir():
        print(f"Error: directory not found: {walkmeter_dir}")
        sys.exit(1)

    db_files = sorted(walkmeter_dir.glob("*.db"))
    print(f"Found {len(db_files)} database files in {walkmeter_dir}")

    all_points = []
    for db_path in db_files:
        points, run_count = process_db(db_path)
        all_points.extend(points)
        print(f"  {db_path.name}: {run_count} runs, {len(points)} coordinates")

    print(f"\nTotal points parsed: {len(all_points)}")

    # Deduplicate in-memory by (device_id, ts)
    seen = set()
    unique_points = []
    for p in all_points:
        key = (p["device_id"], p["ts"])
        if key not in seen:
            seen.add(key)
            unique_points.append(p)
    dupes = len(all_points) - len(unique_points)
    all_points = unique_points
    print(f"After dedup: {len(all_points)} unique points ({dupes} duplicates removed)")

    if all_points:
        timestamps = [p["ts"] for p in all_points]
        print(f"Date range: {min(timestamps)} to {max(timestamps)}")

        # Count by device
        by_device = {}
        for p in all_points:
            by_device.setdefault(p["device_id"], 0)
            by_device[p["device_id"]] += 1
        for did, count in sorted(by_device.items()):
            print(f"  {did}: {count} points")

    if args.dry_run:
        print("\n[DRY RUN] Skipping database insert.")
        print("\nSample points (first 5):")
        for p in all_points[:5]:
            print(f"  {p['ts']}  {p['lat']:.6f},{p['lon']:.6f}  alt={p['altitude_m']}  spd={p['speed_kmh']}")
        return

    print("\nEnsuring unique constraint...")
    db.ensure_unique_constraint()

    print(f"Inserting {len(all_points)} points...")
    inserted, skipped = db.insert_points(all_points)
    print(f"Done: {inserted} inserted, {skipped} skipped (duplicates)")


if __name__ == "__main__":
    main()
