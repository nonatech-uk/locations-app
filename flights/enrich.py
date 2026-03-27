#!/usr/bin/env python3
"""Enrich pipeline-ingested flights with FlightAware AeroAPI and OpenFlights data."""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
import db
from flights.airports import load_airports, lookup_airport, haversine_km

FLIGHTAWARE_URL = "https://aeroapi.flightaware.com/aeroapi"
HC_URL = os.environ.get("ENRICH_HC_URL", "")


def ping_hc(suffix=""):
    if HC_URL:
        try:
            requests.get(f"{HC_URL}{suffix}", timeout=10)
        except Exception:
            pass


def fetch_flight(api_key, flight_number, flight_date):
    """Look up a flight on FlightAware AeroAPI. Returns response dict or None."""
    date_obj = datetime.strptime(flight_date, "%Y-%m-%d")
    next_day = date_obj + timedelta(days=1)

    resp = requests.get(
        f"{FLIGHTAWARE_URL}/flights/{flight_number}",
        headers={"x-apikey": api_key},
        params={
            "start": f"{flight_date}T00:00:00Z",
            "end": next_day.strftime("%Y-%m-%dT00:00:00Z"),
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    results = data.get("flights", [])
    if not results:
        return None

    # Match by date if possible
    for r in results:
        scheduled = r.get("scheduled_out") or ""
        if scheduled.startswith(flight_date):
            return r

    # Fall back to first result
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
    """Enrich a single flight row with FlightAware + OpenFlights data."""
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

    # FlightAware enrichment
    if api_key and flight_number:
        try:
            time.sleep(6)  # rate limit: 10 req/min
            result = fetch_flight(api_key, flight_number, flight_date)
            if result:
                if result.get("aircraft_type"):
                    updates["aircraft_code"] = result["aircraft_type"]
                if result.get("registration"):
                    updates["registration"] = result["registration"]
                if result.get("operator_iata"):
                    updates["airline_code"] = result["operator_iata"]
                if result.get("operator"):
                    updates["airline"] = result["operator"]

                dep_time = extract_time(result.get("actual_off") or result.get("scheduled_out"))
                arr_time = extract_time(result.get("actual_on") or result.get("scheduled_in"))
                if dep_time:
                    updates["dep_time"] = dep_time
                if arr_time:
                    updates["arr_time"] = arr_time
                if dep_time and arr_time:
                    dur = calculate_duration(dep_time, arr_time)
                    if dur:
                        updates["duration"] = dur

                # Gate, terminal, baggage
                if result.get("gate_origin"):
                    updates["gate_origin"] = result["gate_origin"]
                if result.get("gate_destination"):
                    updates["gate_destination"] = result["gate_destination"]
                if result.get("terminal_origin"):
                    updates["terminal_origin"] = result["terminal_origin"]
                if result.get("terminal_destination"):
                    updates["terminal_destination"] = result["terminal_destination"]
                if result.get("baggage_claim"):
                    updates["baggage_claim"] = result["baggage_claim"]

                # Delays, route distance, runways
                if result.get("departure_delay") is not None:
                    updates["departure_delay"] = result["departure_delay"]
                if result.get("arrival_delay") is not None:
                    updates["arrival_delay"] = result["arrival_delay"]
                if result.get("route_distance"):
                    updates["route_distance"] = result["route_distance"]
                if result.get("actual_runway_off"):
                    updates["runway_origin"] = result["actual_runway_off"]
                if result.get("actual_runway_on"):
                    updates["runway_destination"] = result["actual_runway_on"]

                # Codeshares
                codeshares_iata = result.get("codeshares_iata") or []
                # Exclude the flight's own number
                codeshares_iata = [c for c in codeshares_iata if c != flight_number]
                if codeshares_iata:
                    updates["codeshares"] = ",".join(codeshares_iata)

                print(f"    FlightAware: aircraft={result.get('aircraft_type')}, reg={result.get('registration')}")
            else:
                print(f"    FlightAware: no results")
        except Exception as e:
            print(f"    FlightAware error: {e}")

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
    api_key = os.environ.get("FLIGHTAWARE_API_KEY", "")
    if not api_key:
        print("Warning: FLIGHTAWARE_API_KEY not set — only OpenFlights enrichment available")

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
