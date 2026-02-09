#!/usr/bin/env python3
"""Import Placeme location history from HTML exports into gps_points.

Parses HTML files exported from the Placeme app (Nov 2013 - Feb 2014),
forward-geocodes addresses via Nominatim, and inserts into gps_points
with device_id='Placeme', source_type='placeme'.

Usage:
    python gps/placeme_import.py [--dir /path/to/Placeme] [--dry-run]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# Add parent to path so we can import db
sys.path.insert(0, str(Path(__file__).parent.parent))
import db

FORWARD_CACHE_FILE = Path(__file__).parent.parent / "data" / "forward_geocode_cache.json"


def load_forward_cache():
    if FORWARD_CACHE_FILE.exists():
        with open(FORWARD_CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_forward_cache(cache):
    FORWARD_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FORWARD_CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, sort_keys=True)


# Geocoder setup
geolocator = Nominatim(user_agent='mylocation-placeme-import')
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)


def forward_geocode_cached(address, cache):
    """Forward geocode an address with cache and progressive fallback.

    If the full address fails, progressively drop leading components
    (e.g. "4 Summerhouse Road, Godalming, Surrey" -> "Godalming, Surrey").
    Returns (lat, lon) or None.
    """
    if address in cache:
        entry = cache[address]
        if entry is None:
            return None
        return entry['lat'], entry['lon']

    parts = [p.strip() for p in address.split(',')]
    # Try full address first, then progressively drop leading parts
    for i in range(len(parts)):
        query = ', '.join(parts[i:])
        try:
            location = geocode(query)
            if location:
                cache[address] = {'lat': location.latitude, 'lon': location.longitude,
                                  'query_used': query, 'display': location.address}
                return location.latitude, location.longitude
        except Exception as e:
            print(f"  Geocode error for '{query}': {e}")

    # All attempts failed
    print(f"  FAILED to geocode: {address}")
    cache[address] = None
    return None


def extract_address_from_url(href):
    """Extract address from Google Maps URL like http://maps.google.com/?q=..."""
    parsed = urlparse(href)
    params = parse_qs(parsed.query)
    if 'q' in params:
        return unquote(params['q'][0]).replace('+', ' ')
    return None


def parse_file_date(filename):
    """Extract date from filename like 'Placeme for December 03, 2013.html'."""
    basename = os.path.basename(filename)
    name = basename.replace('.html', '')
    return datetime.strptime(name, 'Placeme for %B %d, %Y')


def parse_time_cell(time_cell, file_date):
    """Parse time cell, returning a datetime.

    Time cell contains HH:MM AM/PM, optionally followed by <br/>Month DD, YYYY
    for entries that started on the previous day.
    """
    span = time_cell.find('span')
    if not span:
        return None

    # Check for <br/> indicating an explicit date
    br = span.find('br')
    if br:
        # Text before <br/> is the time, text after is the date
        time_str = br.previous_sibling
        if time_str:
            time_str = str(time_str).strip()
        date_str = br.next_sibling
        if date_str:
            date_str = str(date_str).strip()
        if time_str and date_str:
            return datetime.strptime(f"{date_str} {time_str}", '%B %d, %Y %I:%M %p')
    else:
        # Just a time - use the file date
        time_str = span.get_text(strip=True)
        if time_str:
            t = datetime.strptime(time_str, '%I:%M %p')
            return file_date.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)

    return None


def parse_html_file(filepath):
    """Parse a single Placeme HTML file, returning a list of visit dicts.

    Returns list of: {'address': str, 'place_name': str, 'ts': datetime}
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    file_date = parse_file_date(filepath)

    # Use only the first table (duplicates may exist)
    table = soup.find('table')
    if not table:
        return []

    visits = []
    seen = set()

    for row in table.find_all('tr'):
        tds = row.find_all('td')
        if len(tds) != 3:
            continue

        info_cell = tds[1]
        time_cell = tds[2]

        # Extract address from Google Maps link
        address = None
        for a in info_cell.find_all('a'):
            href = a.get('href', '')
            if 'maps.google.com' in href:
                address = extract_address_from_url(href)
                break

        if not address:
            continue

        # Extract place name from first div's strong/a
        place_name = None
        divs = info_cell.find_all('div')
        if divs:
            strong = divs[0].find('strong')
            if strong:
                place_name = strong.get_text(strip=True)
            else:
                a_tag = divs[0].find('a')
                if a_tag:
                    place_name = a_tag.get_text(strip=True)

        # Parse timestamp
        ts = parse_time_cell(time_cell, file_date)
        if not ts:
            continue

        # Deduplicate by (address, timestamp)
        key = (address, ts)
        if key in seen:
            continue
        seen.add(key)

        visits.append({
            'address': address,
            'place_name': place_name or address,
            'ts': ts,
        })

    return visits


def main():
    parser = argparse.ArgumentParser(description='Import Placeme location data')
    parser.add_argument('--dir', default=str(Path(__file__).parent.parent.parent / 'Placeme'),
                        help='Path to Placeme HTML directory (default: ../Placeme)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse and geocode only, no DB writes')
    args = parser.parse_args()

    placeme_dir = Path(args.dir)
    if not placeme_dir.is_dir():
        print(f"Error: directory not found: {placeme_dir}")
        sys.exit(1)

    html_files = sorted(placeme_dir.glob('Placeme for *.html'))
    print(f"Found {len(html_files)} HTML files in {placeme_dir}")

    # Parse all files
    all_visits = []
    for filepath in html_files:
        visits = parse_html_file(str(filepath))
        all_visits.extend(visits)
        if visits:
            print(f"  {filepath.name}: {len(visits)} visits")

    # Deduplicate across files by (address, ts)
    seen = set()
    unique_visits = []
    for v in all_visits:
        key = (v['address'], v['ts'])
        if key not in seen:
            seen.add(key)
            unique_visits.append(v)
    all_visits = unique_visits

    print(f"\nTotal visits parsed: {len(all_visits)}")
    if all_visits:
        dates = [v['ts'] for v in all_visits]
        print(f"Date range: {min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}")

    # Unique addresses
    unique_addresses = set(v['address'] for v in all_visits)
    print(f"Unique addresses: {len(unique_addresses)}")

    # Forward geocode
    cache = load_forward_cache()
    print(f"\nLoaded forward geocode cache ({len(cache)} entries)")

    cached_count = 0
    new_count = 0
    failed = []

    for addr in sorted(unique_addresses):
        was_cached = addr in cache
        result = forward_geocode_cached(addr, cache)
        if was_cached:
            cached_count += 1
        else:
            new_count += 1
        if result is None:
            failed.append(addr)

    save_forward_cache(cache)
    print(f"Geocoding: {cached_count} cached, {new_count} new lookups")
    print(f"Cache saved ({len(cache)} entries)")

    if failed:
        print(f"\nFailed to geocode {len(failed)} addresses:")
        for addr in failed:
            print(f"  - {addr}")

    # Build points for DB
    points = []
    skipped_geo = 0
    for v in all_visits:
        entry = cache.get(v['address'])
        if not entry or entry is None:
            skipped_geo += 1
            continue

        points.append({
            'device_id': 'Placeme',
            'device_name': v['place_name'],
            'ts': v['ts'],
            'lat': entry['lat'],
            'lon': entry['lon'],
            'altitude_m': None,
            'altitude_ft': None,
            'speed_mph': None,
            'speed_kmh': None,
            'direction': None,
            'accuracy_m': None,
            'battery_pct': None,
            'source_type': 'placeme',
        })

    print(f"\nPoints ready for insert: {len(points)} ({skipped_geo} skipped due to geocode failure)")

    if args.dry_run:
        print("\n[DRY RUN] Skipping database insert.")
        print("\nSample points:")
        for p in points[:5]:
            print(f"  {p['ts']}  {p['lat']:.4f},{p['lon']:.4f}  {p['device_name']}")
        return

    # Insert into DB
    print("\nEnsuring unique constraint...")
    db.ensure_unique_constraint()

    print(f"Inserting {len(points)} points...")
    inserted, skipped = db.insert_points(points)
    print(f"Done: {inserted} inserted, {skipped} skipped (duplicates)")


if __name__ == '__main__':
    main()
