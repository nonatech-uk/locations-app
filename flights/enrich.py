#!/usr/bin/env python3
"""Enrich pipeline-ingested flights with AviationStack API and OpenFlights data."""

import os
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
import db
from flights.airports import load_airports, lookup_airport, haversine_km

AVIATIONSTACK_URL = "https://api.aviationstack.com/v1/flights"
HC_URL = os.environ.get("ENRICH_HC_URL", "")


def ping_hc(suffix=""):
    if HC_URL:
        try:
            requests.get(f"{HC_URL}{suffix}", timeout=10)
        except Exception:
            pass


def fetch_flight(api_key, flight_number, flight_date):
    """Look up a flight on AviationStack. Returns response dict or None."""
    resp = requests.get(
        AVIATIONSTACK_URL,
        params={
            "access_key": api_key,
            "flight_iata": flight_number,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("error"):
        print(f"  AviationStack error: {data['error'].get('message', data['error'])}")
        return None

    results = data.get("data", [])
    if not results:
        return None

    # Match by date if possible
    for r in results:
        if r.get("flight_date") == flight_date:
            return r

    # Fall back to first result (same flight number, close enough)
    return results[0]


def extract_time(time_str):
    """Extract HH:MM time from an ISO datetime string."""
    if not time_str:
        return None
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except (ValueError, TypeError):
        return None


def calculate_duration(dep_time, arr_time):
    """Calculate duration string from two HH:MM times."""
    if not dep_time or not arr_time:
        return None
    try:
        dep = datetime.strptime(dep_time, "%H:%M")
        arr = datetime.strptime(arr_time, "%H:%M")
        diff = arr - dep
        if diff.total_seconds() < 0:
            diff += __import__("datetime").timedelta(days=1)
        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes = remainder // 60
        return f"{hours:02d}:{minutes:02d}:00"
    except (ValueError, TypeError):
        return None


def enrich_flight(conn, flight, api_key):
    """Enrich a single flight row with AviationStack + OpenFlights data."""
    flight_id = flight[0]
    flight_date = str(flight[1])
    flight_number = flight[2]
    dep_iata = flight[3]
    arr_iata = flight[4]

    print(f"  Enriching flight {flight_id}: {flight_number} {dep_iata}→{arr_iata} on {flight_date}")

    updates = {}

    # OpenFlights enrichment (always available)
    dep = lookup_airport(dep_iata)
    arr = lookup_airport(arr_iata)

    if dep:
        updates["dep_airport_name"] = dep["name"]
        updates["dep_icao"] = dep["icao"]
        updates["dep_lat"] = dep["lat"]
        updates["dep_lon"] = dep["lon"]

    if arr:
        updates["arr_airport_name"] = arr["name"]
        updates["arr_icao"] = arr["icao"]
        updates["arr_lat"] = arr["lat"]
        updates["arr_lon"] = arr["lon"]

    if dep and arr:
        updates["distance_km"] = haversine_km(dep["lat"], dep["lon"], arr["lat"], arr["lon"])

    # AviationStack enrichment
    if api_key and flight_number:
        try:
            result = fetch_flight(api_key, flight_number, flight_date)
            if result:
                aircraft = result.get("aircraft") or {}
                airline = result.get("airline") or {}
                departure = result.get("departure") or {}
                arrival = result.get("arrival") or {}

                if aircraft.get("iata"):
                    updates["aircraft_code"] = aircraft["iata"]
                if aircraft.get("registration"):
                    updates["registration"] = aircraft["registration"]
                if airline.get("iata"):
                    updates["airline_code"] = airline["iata"]

                dep_time = extract_time(departure.get("actual") or departure.get("scheduled"))
                arr_time = extract_time(arrival.get("actual") or arrival.get("scheduled"))
                if dep_time:
                    updates["dep_time"] = dep_time
                if arr_time:
                    updates["arr_time"] = arr_time
                if dep_time and arr_time:
                    dur = calculate_duration(dep_time, arr_time)
                    if dur:
                        updates["duration"] = dur

                print(f"    AviationStack: aircraft={aircraft.get('iata')}, reg={aircraft.get('registration')}")
            else:
                print(f"    AviationStack: no results")
        except Exception as e:
            print(f"    AviationStack error: {e}")

    if not updates:
        print(f"    No enrichment data found")
        return False

    # Build UPDATE query
    set_clauses = ", ".join(f"{k} = %({k})s" for k in updates)
    updates["id"] = flight_id
    sql = f"UPDATE flights SET {set_clauses} WHERE id = %(id)s"

    cur = conn.cursor()
    cur.execute(sql, updates)
    conn.commit()
    cur.close()

    print(f"    Updated {len(updates) - 1} fields")
    return True


def main():
    api_key = os.environ.get("AVIATIONSTACK_API_KEY", "")
    if not api_key:
        print("Warning: AVIATIONSTACK_API_KEY not set — only OpenFlights enrichment available")

    ping_hc("/start")

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, flight_number, dep_airport, arr_airport
        FROM flights
        WHERE source = 'pipeline'
          AND dep_airport_name IS NULL
          AND date >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY date
    """)
    flights = cur.fetchall()
    cur.close()

    print(f"Found {len(flights)} flight(s) to enrich")

    enriched = 0
    failed = 0
    for flight in flights:
        try:
            if enrich_flight(conn, flight, api_key):
                enriched += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  Error: {e}")
            failed += 1

    conn.close()

    summary = f"Enriched {enriched}, failed {failed} of {len(flights)} flights"
    print(summary)

    if failed > 0:
        ping_hc(f"/fail")
    else:
        ping_hc("")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
