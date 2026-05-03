#!/usr/bin/env python3
"""Weekly KML archiver for OwnTracks gps_points.

Writes one KML per ISO week (Mon 00:00 UTC -> next Mon 00:00 UTC) into the
configured output dir, named ``YYYYMMDD-OwnTracks.kml`` after the Sunday end
of the ISO week (matches the FollowMee archive naming).

Each ``<Placemark>`` carries:
  * ``<TimeStamp><when>`` ISO8601 UTC
  * ``<Point><coordinates>`` lon,lat,alt
  * ``<description>`` HTML matching FollowMee regex anchors so the legacy
    ``gps/kml_loader.py`` keeps working
  * ``<ExtendedData>`` with every gps_points column (raw_payload as compact
    JSON) so the archive can losslessly rehydrate the row.

Idempotent: re-running the same week overwrites the file via atomic rename.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import xml.sax.saxutils as saxutils
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras

import config


DEFAULT_OUT_DIR = "/data/source-data/owntracks"

OWNTRACKS_COLUMNS = [
    "device_id", "device_name", "ts", "lat", "lon",
    "altitude_m", "altitude_ft", "speed_mph", "speed_kmh",
    "direction", "accuracy_m", "battery_pct",
    "battery_status", "connection_type", "wifi_ssid", "wifi_bssid",
    "vertical_accuracy_m", "trigger_type", "monitoring_mode", "topic",
    "in_regions", "pressure_kpa", "poi", "created_at", "raw_payload",
]


def iso_week_bounds(any_day: date) -> tuple[datetime, datetime, date]:
    """Return (start_utc, end_utc_exclusive, sunday_date) for the ISO week of any_day."""
    monday = any_day - timedelta(days=any_day.isoweekday() - 1)
    sunday = monday + timedelta(days=6)
    start = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    return start, end, sunday


def fetch_week(conn, start: datetime, end: datetime) -> list[dict]:
    sql = f"""
        SELECT {", ".join(OWNTRACKS_COLUMNS)}
        FROM gps_points
        WHERE source_type = 'owntracks' AND ts >= %s AND ts < %s
        ORDER BY ts, device_id
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, (start, end))
    rows = cur.fetchall()
    cur.close()
    return rows


def fetch_data_bounds(conn) -> tuple[datetime | None, datetime | None]:
    cur = conn.cursor()
    cur.execute(
        "SELECT MIN(ts), MAX(ts) FROM gps_points WHERE source_type = 'owntracks'"
    )
    row = cur.fetchone()
    cur.close()
    return row[0], row[1]


def _xmlsafe(value) -> str:
    return saxutils.escape(str(value), {'"': "&quot;"})


def _format_extended_value(name: str, value) -> str | None:
    if value is None:
        return None
    if name == "raw_payload":
        if isinstance(value, (dict, list)):
            return json.dumps(value, separators=(",", ":"), default=str, ensure_ascii=False)
        return str(value)
    if name == "in_regions" and isinstance(value, list):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    if name == "ts" or name == "created_at":
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        return str(value)
    return str(value)


def _description_html(row: dict) -> str:
    """FollowMee-shaped HTML so kml_loader's regex extractors keep working."""
    ts = row["ts"]
    if isinstance(ts, datetime):
        ts_str = ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        ts_str = str(ts)
    parts = [f"{ts_str}"]
    parts.append(f"GPS {row['lat']:.5f},{row['lon']:.5f}")
    speed_mph = row.get("speed_mph")
    speed_kmh = row.get("speed_kmh")
    if speed_mph is not None and speed_kmh is not None:
        parts.append(f"Speed: {speed_mph} mph, {speed_kmh} km/h")
    altitude_ft = row.get("altitude_ft")
    altitude_m = row.get("altitude_m")
    if altitude_ft is not None and altitude_m is not None:
        parts.append(f"Altitude: {altitude_ft} ft, {altitude_m} meters")
    accuracy_m = row.get("accuracy_m")
    if accuracy_m is not None:
        parts.append(f"Accuracy: {accuracy_m} meters")
    battery = row.get("battery_pct")
    if battery is not None:
        parts.append(f"Battery: {battery}%")
    inner = "<br>".join(_xmlsafe(p) for p in parts)
    return f"<div>{inner}</div>"


def _coordinates(row: dict) -> str:
    alt = row.get("altitude_m")
    if alt is None:
        return f"{row['lon']},{row['lat']},0"
    return f"{row['lon']},{row['lat']},{alt}"


def _placemark(row: dict) -> str:
    ts = row["ts"]
    if isinstance(ts, datetime):
        when = ts.astimezone(timezone.utc).isoformat()
    else:
        when = str(ts)
    lines = [
        "  <Placemark>",
        f"    <TimeStamp><when>{_xmlsafe(when)}</when></TimeStamp>",
        f"    <Point><coordinates>{_xmlsafe(_coordinates(row))}</coordinates></Point>",
        f"    <description><![CDATA[{_description_html(row)}]]></description>",
        "    <ExtendedData>",
    ]
    for col in OWNTRACKS_COLUMNS:
        formatted = _format_extended_value(col, row.get(col))
        if formatted is None:
            continue
        lines.append(
            f'      <Data name="{col}"><value>{_xmlsafe(formatted)}</value></Data>'
        )
    lines.append("    </ExtendedData>")
    lines.append("  </Placemark>")
    return "\n".join(lines)


def render_kml(rows: list[dict], start: datetime, end: datetime) -> str:
    header = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://earth.google.com/kml/2.2">\n'
        "<Document>\n"
        f"  <name>OwnTracks {start.date().isoformat()} to {(end - timedelta(days=1)).date().isoformat()}</name>\n"
    )
    body = "\n".join(_placemark(r) for r in rows)
    footer = "\n</Document>\n</kml>\n"
    return header + body + footer


def write_atomic(path: Path, content: str) -> None:
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.chmod(tmp, 0o640)
    os.replace(tmp, path)


def export_one_week(conn, any_day: date, out_dir: Path, dry_run: bool) -> tuple[Path, int]:
    start, end, sunday = iso_week_bounds(any_day)
    rows = fetch_week(conn, start, end)
    filename = f"{sunday.strftime('%Y%m%d')}-OwnTracks.kml"
    path = out_dir / filename
    if not rows:
        return path, 0
    if dry_run:
        return path, len(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(path, render_kml(rows, start, end))
    return path, len(rows)


def all_weeks(start: date, end_exclusive: date):
    """Yield Mondays from the ISO week containing start up to (not including) the ISO week containing end_exclusive."""
    monday = start - timedelta(days=start.isoweekday() - 1)
    end_monday = end_exclusive - timedelta(days=end_exclusive.isoweekday() - 1)
    while monday < end_monday:
        yield monday
        monday += timedelta(days=7)


def main() -> int:
    p = argparse.ArgumentParser(description="Export OwnTracks gps_points to weekly KML archives")
    p.add_argument("--week", help="Any date (YYYY-MM-DD) in the target ISO week. Default: previous ISO week.")
    p.add_argument("--backfill", action="store_true",
                   help="Iterate every ISO week with OwnTracks data, up to (not including) the current ISO week.")
    p.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help=f"Output directory (default: {DEFAULT_OUT_DIR})")
    p.add_argument("--dry-run", action="store_true", help="Report what would be written, write nothing.")
    args = p.parse_args()

    if args.week and args.backfill:
        print("error: --week and --backfill are mutually exclusive", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    conn = psycopg2.connect(
        host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
        user=config.DB_USER, password=config.DB_PASSWORD, sslmode="require",
    )
    try:
        if args.backfill:
            earliest, latest = fetch_data_bounds(conn)
            if earliest is None:
                print("No OwnTracks data found.")
                return 0
            today_utc = datetime.now(timezone.utc).date()
            total_rows = 0
            written = 0
            for monday in all_weeks(earliest.date(), today_utc):
                path, n = export_one_week(conn, monday, out_dir, args.dry_run)
                total_rows += n
                if n:
                    written += 1
                    verb = "would write" if args.dry_run else "wrote"
                    print(f"  {verb} {path.name}: {n} points")
                else:
                    print(f"  skip {path.name}: 0 points")
            print(f"Backfill complete: {written} files, {total_rows} total points "
                  f"({'dry-run' if args.dry_run else 'written'})")
        else:
            target = (
                date.fromisoformat(args.week)
                if args.week
                else (datetime.now(timezone.utc).date() - timedelta(days=7))
            )
            path, n = export_one_week(conn, target, out_dir, args.dry_run)
            verb = "would write" if args.dry_run else ("wrote" if n else "skipped")
            print(f"{verb} {path.name}: {n} points")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
