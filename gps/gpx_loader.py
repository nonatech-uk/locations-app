#!/usr/bin/env python3
"""Load GPS points from GPX files into the database."""

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import config
import db


def detect_namespace(root):
    """Extract namespace URI from root element tag."""
    match = re.match(r'\{(.+?)\}', root.tag)
    return match.group(1) if match else ''


def parse_gpx_file(filepath, device_id='gpx-import', source_type='gpx'):
    """Parse a GPX file and extract GPS points."""
    points = []

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
        return points

    ns_uri = detect_namespace(root)
    ns = f'{{{ns_uri}}}' if ns_uri else ''

    # Get track name for device_name
    trk_name_elem = root.find(f'.//{ns}trk/{ns}name')
    device_name = trk_name_elem.text.strip() if trk_name_elem is not None and trk_name_elem.text else None
    if not device_name:
        device_name = root.get('creator', 'GPX Import')

    # Find all trackpoints
    for trkpt in root.iter(f'{ns}trkpt'):
        try:
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))

            time_elem = trkpt.find(f'{ns}time')
            if time_elem is None or not time_elem.text:
                continue

            ele_elem = trkpt.find(f'{ns}ele')
            altitude_m = float(ele_elem.text) if ele_elem is not None and ele_elem.text else None

            points.append({
                'device_id': device_id,
                'device_name': device_name,
                'ts': time_elem.text.strip(),
                'lat': lat,
                'lon': lon,
                'altitude_m': altitude_m,
                'altitude_ft': None,
                'speed_mph': None,
                'speed_kmh': None,
                'direction': None,
                'accuracy_m': None,
                'battery_pct': None,
                'source_type': source_type,
            })
        except (ValueError, AttributeError):
            continue

    return points


def load_all_gpx_files(gpx_dir, device_id='gpx-import', source_type='gpx', dry_run=False):
    """Load all GPX files from a directory."""
    gpx_dir = Path(gpx_dir)

    if not gpx_dir.exists():
        print(f"GPX directory not found: {gpx_dir}")
        return

    if not dry_run:
        db.ensure_unique_constraint()

    gpx_files = sorted(gpx_dir.glob('*.gpx'))
    print(f"Found {len(gpx_files)} GPX files")

    total_inserted = 0
    total_skipped = 0
    total_points = 0

    for i, gpx_file in enumerate(gpx_files, 1):
        print(f"[{i}/{len(gpx_files)}] Processing {gpx_file.name}...", end=' ')

        points = parse_gpx_file(gpx_file, device_id, source_type)
        total_points += len(points)

        if points:
            if dry_run:
                print(f"{len(points)} points (dry run)")
            else:
                inserted, skipped = db.insert_points(points)
                total_inserted += inserted
                total_skipped += skipped
                print(f"{len(points)} points, {inserted} inserted, {skipped} duplicates")
        else:
            print("no timestamped points found")

    if dry_run:
        print(f"\nDry run complete: {total_points} points found across {len(gpx_files)} files")
    else:
        print(f"\nComplete: {total_inserted} inserted, {total_skipped} duplicates skipped")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import GPX files into gps_points')
    parser.add_argument('--dir', default='/zfs/tank/home/stu/gps-import/',
                        help='Directory containing GPX files')
    parser.add_argument('--device-id', default='gpx-import')
    parser.add_argument('--source-type', default='gpx')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse files without inserting into database')
    args = parser.parse_args()

    load_all_gpx_files(args.dir, args.device_id, args.source_type, args.dry_run)
