#!/usr/bin/env python3
"""Load GPS points from KML files into the database."""

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import config
import db


# Direction mapping from FollowMee style codes
DIRECTION_MAP = {
    'cn': 0, 'cne': 45, 'ce': 90, 'cse': 135,
    'cs': 180, 'csw': 225, 'cw': 270, 'cnw': 315,
    'c': None, 'g': None, 'r': None
}


def detect_namespace(root):
    """Extract namespace URI from root element tag."""
    match = re.match(r'\{(.+?)\}', root.tag)
    return match.group(1) if match else ''


def find_element(parent, local_name, ns):
    """Find element handling namespace properly."""
    elem = parent.find(f'.//{ns}{local_name}')
    if elem is not None:
        return elem
    return parent.find(f'.//{local_name}')


def parse_description(desc):
    """Extract speed, altitude, accuracy from FollowMee description HTML."""
    result = {'speed_mph': None, 'speed_kmh': None, 'altitude_ft': None, 'accuracy_m': None, 'direction': None}

    if not desc:
        return result

    # Speed: "Speed: 28 mph, 45 km/h"
    speed_match = re.search(r'Speed:\s*([\d.]+)\s*mph,\s*([\d.]+)\s*km/h', desc)
    if speed_match:
        result['speed_mph'] = float(speed_match.group(1))
        result['speed_kmh'] = float(speed_match.group(2))

    # Altitude: "Altitude: 328 ft, 100 meters"
    alt_match = re.search(r'Altitude:\s*([\d.-]+)\s*ft,\s*([\d.-]+)\s*meters', desc)
    if alt_match:
        result['altitude_ft'] = float(alt_match.group(1))

    # Accuracy: "Accuracy: 65 meters"
    acc_match = re.search(r'Accuracy:\s*([\d.]+)\s*meters', desc)
    if acc_match:
        result['accuracy_m'] = float(acc_match.group(1))

    return result


def parse_fr24_description(desc):
    """Extract altitude, speed, heading from FlightRadar24 description HTML."""
    result = {'altitude_ft': None, 'speed_mph': None, 'speed_kmh': None, 'direction': None}

    if not desc:
        return result

    # Altitude: various patterns in FR24 HTML
    alt_match = re.search(r'Altitude:.*?(\d+)\s*ft', desc, re.DOTALL)
    if alt_match:
        result['altitude_ft'] = float(alt_match.group(1))

    # Speed in knots — convert to mph and km/h
    speed_match = re.search(r'Speed:.*?(\d+)\s*kt', desc, re.DOTALL)
    if speed_match:
        knots = float(speed_match.group(1))
        result['speed_mph'] = round(knots * 1.15078, 1)
        result['speed_kmh'] = round(knots * 1.852, 1)

    # Heading
    heading_match = re.search(r'Heading:.*?(\d+)', desc, re.DOTALL)
    if heading_match:
        result['direction'] = float(heading_match.group(1))

    return result


def parse_direction(style_url):
    """Convert FollowMee style URL to direction in degrees."""
    if not style_url:
        return None
    style = style_url.lstrip('#')
    return DIRECTION_MAP.get(style)


def is_fr24_kml(root, ns):
    """Check if this is a FlightRadar24 KML by looking for FR24 markers."""
    doc_desc = find_element(root, 'description', ns)
    if doc_desc is not None and doc_desc.text and 'flightradar24' in doc_desc.text.lower():
        return True
    # Also check first placemark description
    for pm in root.iter(f'{ns}Placemark'):
        desc = find_element(pm, 'description', ns)
        if desc is not None and desc.text and 'flightradar24' in desc.text.lower():
            return True
        break
    return False


def parse_kml_file(filepath, device_id=None, source_type='kml'):
    """Parse a KML file and extract GPS points."""
    points = []

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
        return points

    ns_uri = detect_namespace(root)
    ns = f'{{{ns_uri}}}' if ns_uri else ''

    # Auto-detect device_id if not provided
    fr24 = is_fr24_kml(root, ns)
    if device_id is None:
        device_id = 'flightradar24' if fr24 else config.DEVICE_ID

    device_name = 'FlightRadar24' if fr24 else 'FollowMee'

    for pm in root.iter(f'{ns}Placemark'):
        try:
            # Get timestamp
            when_elem = find_element(pm, 'when', ns)
            if when_elem is None or not when_elem.text:
                continue

            ts = when_elem.text.strip()

            # Skip malformed timezone offsets (e.g., -02:-30)
            if re.search(r'[+-]\d{2}:-\d{2}$', ts):
                continue

            # Get coordinates
            coords_elem = find_element(pm, 'coordinates', ns)
            if coords_elem is None or not coords_elem.text:
                continue

            coords = coords_elem.text.strip().split(',')
            if len(coords) < 2:
                continue

            lon = float(coords[0])
            lat = float(coords[1])
            altitude_m = float(coords[2]) if len(coords) > 2 and float(coords[2]) != 0 else None

            # Get description for additional fields
            desc_elem = find_element(pm, 'description', ns)
            desc = desc_elem.text if desc_elem is not None else None

            if fr24:
                parsed_desc = parse_fr24_description(desc)
                direction = parsed_desc['direction']
            else:
                parsed_desc = parse_description(desc)
                # Get direction from style for FollowMee
                style_elem = find_element(pm, 'styleUrl', ns)
                style_url = style_elem.text if style_elem is not None else None
                direction = parse_direction(style_url)

            # Convert FR24 altitude_ft to altitude_m if we have it
            alt_m = altitude_m
            alt_ft = parsed_desc.get('altitude_ft')
            if alt_ft and not alt_m:
                alt_m = round(alt_ft * 0.3048, 1)

            point = {
                'device_id': device_id,
                'device_name': device_name,
                'ts': ts,
                'lat': lat,
                'lon': lon,
                'altitude_m': alt_m,
                'altitude_ft': alt_ft,
                'speed_mph': parsed_desc.get('speed_mph'),
                'speed_kmh': parsed_desc.get('speed_kmh'),
                'direction': direction,
                'accuracy_m': parsed_desc.get('accuracy_m'),
                'battery_pct': None,
                'source_type': source_type
            }
            points.append(point)

        except (ValueError, AttributeError):
            continue

    return points


def load_all_kml_files(kml_dir=None, device_id=None, source_type='kml', dry_run=False):
    """Load all KML files from a directory."""
    kml_dir = Path(kml_dir or config.KML_DIR)

    if not kml_dir.exists():
        print(f"KML directory not found: {kml_dir}")
        return

    if not dry_run:
        db.ensure_unique_constraint()

    kml_files = sorted(kml_dir.glob('*.kml'))
    print(f"Found {len(kml_files)} KML files")

    total_inserted = 0
    total_skipped = 0
    total_points = 0

    for i, kml_file in enumerate(kml_files, 1):
        print(f"[{i}/{len(kml_files)}] Processing {kml_file.name}...", end=' ')

        points = parse_kml_file(kml_file, device_id, source_type)
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
        print(f"\nDry run complete: {total_points} points found across {len(kml_files)} files")
    else:
        print(f"\nComplete: {total_inserted} inserted, {total_skipped} duplicates skipped")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import KML files into gps_points')
    parser.add_argument('--dir', default=None,
                        help='Directory containing KML files (default: config.KML_DIR)')
    parser.add_argument('--device-id', default=None,
                        help='Device ID (default: auto-detect per file)')
    parser.add_argument('--source-type', default='kml')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse files without inserting into database')
    args = parser.parse_args()

    load_all_kml_files(args.dir, args.device_id, args.source_type, args.dry_run)
