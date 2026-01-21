#!/usr/bin/env python3
"""Match flight coordinates to nearby airports."""

import csv
import math
import requests
from io import StringIO
from collections import defaultdict

AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"

# Major train stations (Eurostar, high-speed rail, etc.)
TRAIN_STATIONS = [
    {'iata': 'STP', 'name': 'St Pancras International', 'city': 'London', 'country': 'UK', 'lat': 51.5308, 'lon': -0.1260},
    {'iata': 'XPG', 'name': 'Gare du Nord', 'city': 'Paris', 'country': 'France', 'lat': 48.8809, 'lon': 2.3553},
    {'iata': 'ZYR', 'name': 'Gare de Lyon', 'city': 'Paris', 'country': 'France', 'lat': 48.8448, 'lon': 2.3735},
    {'iata': 'XED', 'name': 'Gare de lEst', 'city': 'Paris', 'country': 'France', 'lat': 48.8763, 'lon': 2.3592},
    {'iata': 'ZYQ', 'name': 'Brussels Midi', 'city': 'Brussels', 'country': 'Belgium', 'lat': 50.8356, 'lon': 4.3369},
    {'iata': 'ZDH', 'name': 'Basel SBB', 'city': 'Basel', 'country': 'Switzerland', 'lat': 47.5472, 'lon': 7.5897},
    {'iata': 'ZLP', 'name': 'Zurich HB', 'city': 'Zurich', 'country': 'Switzerland', 'lat': 47.3783, 'lon': 8.5403},
    {'iata': 'XZN', 'name': 'Avignon TGV', 'city': 'Avignon', 'country': 'France', 'lat': 43.9217, 'lon': 4.7863},
    {'iata': 'XYG', 'name': 'Lyon Part-Dieu', 'city': 'Lyon', 'country': 'France', 'lat': 45.7606, 'lon': 4.8594},
    {'iata': 'QQS', 'name': 'St Pancras Intl', 'city': 'London', 'country': 'UK', 'lat': 51.5317, 'lon': -0.1261},  # Alternate code
    {'iata': 'XJZ', 'name': 'Amsterdam Centraal', 'city': 'Amsterdam', 'country': 'Netherlands', 'lat': 52.3791, 'lon': 4.9003},
    {'iata': 'ZFJ', 'name': 'Rennes', 'city': 'Rennes', 'country': 'France', 'lat': 48.1052, 'lon': -1.6722},
    {'iata': 'XDB', 'name': 'Lille Europe', 'city': 'Lille', 'country': 'France', 'lat': 50.6392, 'lon': 3.0762},
    {'iata': 'XOP', 'name': 'Poitiers', 'city': 'Poitiers', 'country': 'France', 'lat': 46.5826, 'lon': 0.3333},
    {'iata': 'ZFQ', 'name': 'Bordeaux St-Jean', 'city': 'Bordeaux', 'country': 'France', 'lat': 44.8256, 'lon': -0.5558},
    {'iata': 'XIZ', 'name': 'Strasbourg', 'city': 'Strasbourg', 'country': 'France', 'lat': 48.5850, 'lon': 7.7350},
    {'iata': 'XWG', 'name': 'Koln Hbf', 'city': 'Cologne', 'country': 'Germany', 'lat': 50.9430, 'lon': 6.9589},
    {'iata': 'QDU', 'name': 'Dusseldorf Hbf', 'city': 'Dusseldorf', 'country': 'Germany', 'lat': 51.2200, 'lon': 6.7942},
    {'iata': 'ZMB', 'name': 'Hamburg Hbf', 'city': 'Hamburg', 'country': 'Germany', 'lat': 53.5530, 'lon': 10.0069},
    {'iata': 'QPP', 'name': 'Berlin Hbf', 'city': 'Berlin', 'country': 'Germany', 'lat': 52.5250, 'lon': 13.3694},
    {'iata': 'ZMU', 'name': 'Munich Hbf', 'city': 'Munich', 'country': 'Germany', 'lat': 48.1403, 'lon': 11.5603},
    {'iata': 'XEA', 'name': 'Ashford Intl', 'city': 'Ashford', 'country': 'UK', 'lat': 51.1436, 'lon': 0.8761},
    {'iata': 'XQE', 'name': 'Ebbsfleet Intl', 'city': 'Ebbsfleet', 'country': 'UK', 'lat': 51.4428, 'lon': 0.3208},
]

def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def load_airports():
    """Download and parse OpenFlights airport database."""
    print("Downloading airport database...")
    resp = requests.get(AIRPORTS_URL, timeout=30)
    resp.raise_for_status()

    airports = []
    reader = csv.reader(StringIO(resp.text))
    for row in reader:
        if len(row) >= 8:
            try:
                airport = {
                    'id': row[0],
                    'name': row[1],
                    'city': row[2],
                    'country': row[3],
                    'iata': row[4] if row[4] != '\\N' else None,
                    'icao': row[5] if row[5] != '\\N' else None,
                    'lat': float(row[6]),
                    'lon': float(row[7]),
                }
                # Only include airports with IATA codes (major airports)
                if airport['iata']:
                    airports.append(airport)
            except (ValueError, IndexError):
                continue

    print(f"Loaded {len(airports)} airports with IATA codes")

    # Add train stations
    airports.extend(TRAIN_STATIONS)
    print(f"Added {len(TRAIN_STATIONS)} train stations")

    return airports

def find_nearest_airport(lat, lon, airports, max_distance_km=10):
    """Find the nearest airport within max_distance_km."""
    nearest = None
    min_dist = float('inf')

    for airport in airports:
        dist = haversine_km(lat, lon, airport['lat'], airport['lon'])
        if dist < min_dist and dist <= max_distance_km:
            min_dist = dist
            nearest = airport

    return nearest, min_dist if nearest else None

def load_flights(filepath='/tmp/all_flights.txt'):
    """Load flight data."""
    flights = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 9:
                flights.append({
                    'start_time': parts[0],
                    'start_lat': float(parts[1]),
                    'start_lon': float(parts[2]),
                    'end_time': parts[3],
                    'end_lat': float(parts[4]),
                    'end_lon': float(parts[5]),
                    'distance_km': int(float(parts[6])),
                    'duration_h': float(parts[7]),
                    'speed_kmh': int(float(parts[8])),
                })
    return flights

def format_airport(airport, dist):
    """Format airport info for display."""
    if airport:
        return f"{airport['iata']} ({airport['city']})"
    return None

def main():
    airports = load_airports()
    flights = load_flights()

    print(f"\nMatching {len(flights)} flights to airports...")

    # Match each flight's start and end to airports
    matched_flights = []
    route_counts = defaultdict(lambda: {'count': 0, 'dates': []})

    for flight in flights:
        start_airport, start_dist = find_nearest_airport(
            flight['start_lat'], flight['start_lon'], airports
        )
        end_airport, end_dist = find_nearest_airport(
            flight['end_lat'], flight['end_lon'], airports
        )

        flight['start_airport'] = start_airport
        flight['start_dist'] = start_dist
        flight['end_airport'] = end_airport
        flight['end_dist'] = end_dist

        # Format for display
        if start_airport:
            flight['start_display'] = f"{start_airport['iata']}"
            flight['start_full'] = f"{start_airport['iata']} ({start_airport['name']})"
        else:
            flight['start_display'] = f"({flight['start_lat']:.1f}, {flight['start_lon']:.1f})"
            flight['start_full'] = flight['start_display']

        if end_airport:
            flight['end_display'] = f"{end_airport['iata']}"
            flight['end_full'] = f"{end_airport['iata']} ({end_airport['name']})"
        else:
            flight['end_display'] = f"({flight['end_lat']:.1f}, {flight['end_lon']:.1f})"
            flight['end_full'] = flight['end_display']

        matched_flights.append(flight)

        # Count routes
        route_key = f"{flight['start_display']} -> {flight['end_display']}"
        route_counts[route_key]['count'] += 1
        date = flight['start_time'][:10]
        route_counts[route_key]['dates'].append(date)
        if not route_counts[route_key].get('distance'):
            route_counts[route_key]['distance'] = flight['distance_km']

    # Sort routes by frequency
    sorted_routes = sorted(route_counts.items(), key=lambda x: -x[1]['count'])

    # Generate report
    output = []
    output.append("# All Flights Report (Airport-Matched)")
    output.append("")
    output.append(f"Journeys >200km with start/end points matched to airports within 10km.")
    output.append("")
    output.append(f"**Total journeys:** {len(matched_flights)}")
    output.append(f"**Unique routes:** {len(sorted_routes)}")

    # Count airport matches
    start_matched = sum(1 for f in matched_flights if f['start_airport'])
    end_matched = sum(1 for f in matched_flights if f['end_airport'])
    output.append(f"**Departures matched to airports:** {start_matched} ({100*start_matched/len(matched_flights):.0f}%)")
    output.append(f"**Arrivals matched to airports:** {end_matched} ({100*end_matched/len(matched_flights):.0f}%)")
    output.append("")

    # Routes by frequency
    output.append("## Routes by Frequency")
    output.append("")
    output.append("| # | Count | Route | Distance | Sample Dates |")
    output.append("|---|-------|-------|----------|--------------|")

    for i, (route, data) in enumerate(sorted_routes[:50], 1):
        dates = data['dates'][:3]
        more = f" (+{len(data['dates'])-3})" if len(data['dates']) > 3 else ""
        output.append(f"| {i} | {data['count']} | {route} | {data['distance']}km | {', '.join(dates)}{more} |")

    output.append("")

    # All journeys chronologically
    output.append("## All Journeys Chronologically")
    output.append("")
    output.append("| Date | From | To | Distance | Duration |")
    output.append("|------|------|-----|----------|----------|")

    for flight in matched_flights:
        date = flight['start_time'][:10]
        output.append(f"| {date} | {flight['start_full']} | {flight['end_full']} | {flight['distance_km']}km | {flight['duration_h']:.1f}h |")

    # Write output
    report = '\n'.join(output)

    with open('/home/stu/all_flights.md', 'w') as f:
        f.write(report)
    print(f"\nReport written to /home/stu/all_flights.md")

    # Also save raw matched data for reference
    with open('/tmp/all_flights_airports.txt', 'w') as f:
        for flight in matched_flights:
            start_code = flight['start_airport']['iata'] if flight['start_airport'] else ''
            end_code = flight['end_airport']['iata'] if flight['end_airport'] else ''
            f.write(f"{flight['start_time']}|{start_code}|{flight['start_lat']}|{flight['start_lon']}|")
            f.write(f"{flight['end_time']}|{end_code}|{flight['end_lat']}|{flight['end_lon']}|")
            f.write(f"{flight['distance_km']}|{flight['duration_h']}\n")

    print(f"Raw data written to /tmp/all_flights_airports.txt")

if __name__ == '__main__':
    main()
