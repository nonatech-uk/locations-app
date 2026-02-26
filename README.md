# MyLocation - Personal Location History System

Personal location tracking data pipeline and analysis tools. Aggregates GPS tracks, commercial flights, ski days, and GA flying into a unified PostgreSQL database with reports.

## Overview

This system aggregates personal location data from multiple sources:

| Module | Source | Data |
|--------|--------|------|
| **GPS** | FollowMee app | Continuous location tracking (2014-present) |
| **Flights** | FlightDiary export | Commercial airline flights |
| **Skiing** | Ski Tracks app | Ski days, runs, vertical, speed |
| **GA** | Excel logbook | General Aviation pilot logbook |

## Database

- **Database:** mylocation
- **User:** mylocation

### Tables

| Table | Description | Records |
|-------|-------------|---------|
| `gps_points` | GPS location history | ~116k points |
| `flights` | Commercial airline flights | - |
| `skiing_days` | Ski day statistics | - |
| `ga_flights` | GA flying logbook | 592 flights |

## Project Structure

```
~/code/mylocation/
├── config.py               # Database credentials (gitignored)
├── db.py                   # Database connection helper
├── sync.sh                 # GPS sync entrypoint (invoked by Cronicle)
├── Dockerfile              # Docker container build
├── .dockerignore            # Docker build exclusions
├── requirements.txt        # psycopg2-binary, requests, openpyxl
│
├── gps/                    # GPS location tracking module
│   ├── kml_loader.py       # One-time KML import script
│   ├── followmee_sync.py   # Daily API sync script
│   ├── location_report.py  # Location history reports
│   ├── airport_matcher.py  # Match GPS points to airports
│   └── visualize.py        # Interactive map generator
│
├── flights/                # Commercial flights module
│   ├── schema.sql          # Database table definition
│   ├── flight_import.py    # Import from FlightDiary CSV
│   ├── flight_matcher.py   # Match flights with GPS data
│   └── flight_report.py    # Flight statistics reports
│
├── skiing/                 # Skiing module
│   ├── schema.sql          # Database table definition
│   ├── parse_skitracks.py  # Parse Ski Tracks app exports
│   ├── resort_matcher.py   # Match to ski resort database
│   ├── skiing_import.py    # Import ski days to database
│   └── skiing_report.py    # Skiing statistics reports
│
├── ga/                     # General Aviation logbook module
│   ├── README.md           # Detailed module documentation
│   ├── schema.sql          # Database table definition
│   ├── ga_import.py        # Import from Excel logbook
│   └── ga_report.py        # Pilot logbook reports
│
├── data/                   # Source data files (gitignored)
│   ├── flights/            # FlightDiary exports
│   ├── skiing/             # Ski Tracks exports
│   └── ga/                 # Excel logbook
│
├── reports/                # Generated reports
└── venv/                   # Python virtual environment
```

## Configuration

`config.py` contains database credentials and FollowMee API keys (gitignored).

## GPS Module

### Daily Sync (Automated)

Scheduled via **Cronicle** (5am daily), which runs `sync.sh` inside the container and handles healthcheck pings.

**What it does:**
1. Fetches last 48 hours from FollowMee API
2. Checks for gaps in last 7 days
3. Attempts to fill any missing days

### GPS Scripts

```bash
# Import historical KML files (one-time)
./venv/bin/python3 gps/kml_loader.py

# Manual sync (last 48 hours + gap check)
./venv/bin/python3 gps/followmee_sync.py --daily

# Backfill N days
./venv/bin/python3 gps/followmee_sync.py --backfill 45

# Generate location reports
./venv/bin/python3 gps/location_report.py
# Outputs: ~/location_report.html, ~/location_report.md

# Match GPS points to airports/stations (detect journeys >200km)
./venv/bin/python3 gps/airport_matcher.py
# Outputs: ~/all_flights.md

# Generate interactive map
./venv/bin/python3 gps/visualize.py
# Outputs: gps_map.html
```

## Flights Module

Commercial airline flights from FlightDiary exports.

```bash
# Import flights
./venv/bin/python3 flights/flight_import.py

# Generate reports
./venv/bin/python3 flights/flight_report.py
```

## Skiing Module

Ski day statistics from Ski Tracks app exports.

```bash
# Parse Ski Tracks exports
./venv/bin/python3 skiing/parse_skitracks.py data/skiing/

# Import to database
./venv/bin/python3 skiing/skiing_import.py

# Generate reports
./venv/bin/python3 skiing/skiing_report.py
```

## GA Module

General Aviation pilot flying logbook. See `ga/README.md` for detailed documentation.

```bash
# Import from Excel (dry-run first)
./venv/bin/python3 ga/ga_import.py --dry-run
./venv/bin/python3 ga/ga_import.py

# Generate reports
./venv/bin/python3 ga/ga_report.py
# Outputs: reports/ga_report.html, reports/ga_report.md
```

## GPS Airport Matcher

The `gps/airport_matcher.py` script analyses GPS data to identify flights and long-distance journeys (>200km), then matches start/end coordinates to the nearest airport or train station within 10km.

**Data sources:**
- OpenFlights airport database (6,000+ airports with IATA codes)
- Built-in train station database (Eurostar, TGV, major European stations)

**How journeys are detected:**
- Consecutive GPS points >200km apart
- Time gap between 0.5 and 24 hours
- Groups into routes and counts frequency

## Useful SQL Queries

```sql
-- GPS: Points per year
SELECT EXTRACT(YEAR FROM ts) as year, COUNT(*) FROM gps_points GROUP BY year ORDER BY year;

-- GPS: Find data gaps
SELECT d::date as missing_day FROM generate_series('2024-01-01'::date, CURRENT_DATE, '1 day') d
WHERE NOT EXISTS (SELECT 1 FROM gps_points WHERE ts::date = d::date);

-- GPS: Points near a location (1km radius)
SELECT * FROM gps_points WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(-0.497, 51.208), 4326)::geography, 1000);
```

## Database Schemas

### gps_points
```sql
gps_points (
    id              BIGINT PRIMARY KEY,
    device_id       TEXT NOT NULL,
    ts              TIMESTAMPTZ NOT NULL,
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    altitude_m      DOUBLE PRECISION,
    speed_mph       DOUBLE PRECISION,
    source_type     TEXT,           -- 'kml' or 'followmee-api'
    geom            GEOGRAPHY        -- PostGIS point
)
```

### flights
```sql
flights (
    id              SERIAL PRIMARY KEY,
    date            DATE NOT NULL,
    flight_number   TEXT,
    dep_airport     TEXT NOT NULL,   -- IATA code
    arr_airport     TEXT NOT NULL,
    airline         TEXT,
    aircraft_type   TEXT,
    distance_km     INTEGER
)
```

### skiing_days
```sql
skiing_days (
    id              SERIAL PRIMARY KEY,
    date            DATE NOT NULL UNIQUE,
    location        TEXT,
    vertical_down_m INTEGER,
    max_speed_kmh   NUMERIC,
    num_runs        INTEGER,
    season          TEXT
)
```

### ga_flights
See `ga/README.md` for full schema.

## Reports

| Report | Script | Output |
|--------|--------|--------|
| Location history | `gps/location_report.py` | `~/location_report.html`, `~/location_report.md` |
| GPS journeys | `gps/airport_matcher.py` | `~/all_flights.md` |
| GPS map | `gps/visualize.py` | `gps_map.html` |
| Commercial flights | `flights/flight_report.py` | `reports/flight_report.html` |
| Skiing stats | `skiing/skiing_report.py` | `reports/skiing_report.html` |
| GA logbook | `ga/ga_report.py` | `reports/ga_report.html`, `reports/ga_report.md` |

## Docker Deployment

The container provides the sync script as its entrypoint; scheduling is handled externally by Cronicle.

```bash
# Build
docker build -t mylocation .

# Run on-demand (Cronicle triggers this)
docker run --rm mylocation
```

Output goes to stdout/stderr, captured by the scheduler.

## Dependencies

```bash
source ~/code/mylocation/venv/bin/activate
pip install psycopg2-binary requests openpyxl
```

---

*Created: 2026-01-21 | Updated: 2026-02-21*
