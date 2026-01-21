# MyLocation - GPS Location History System

Personal GPS location tracking data pipeline and analysis tools.

## Overview

This system:
1. Imports historical GPS data from FollowMee KML exports
2. Syncs new data daily from the FollowMee API
3. Stores everything in a PostGIS-enabled PostgreSQL database
4. Generates location history reports

## Database

- **Host:** 10.8.0.8 (via WireGuard route through VM host)
- **Database:** mylocation
- **User:** mylocation
- **Table:** `gps_points` (~116k points, 2014-present)

### Schema

```sql
gps_points (
    id              BIGINT PRIMARY KEY,
    device_id       TEXT NOT NULL,
    device_name     TEXT,
    ts              TIMESTAMPTZ NOT NULL,
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    altitude_m      DOUBLE PRECISION,
    altitude_ft     DOUBLE PRECISION,
    speed_mph       DOUBLE PRECISION,
    speed_kmh       DOUBLE PRECISION,
    direction       INTEGER,
    accuracy_m      DOUBLE PRECISION,
    battery_pct     DOUBLE PRECISION,
    source_type     TEXT,           -- 'kml' or 'followmee-api'
    geom            GEOGRAPHY        -- PostGIS point
)

-- Indexes
UNIQUE (device_id, ts)              -- Deduplication
INDEX ON ts
INDEX ON device_id
GIST INDEX ON geom                  -- Spatial queries
```

## Files

```
~/code/mylocation/
├── venv/                   # Python virtual environment
├── config.py               # Credentials (gitignored)
├── db.py                   # Database connection helper
├── kml_loader.py           # One-time KML import script
├── followmee_sync.py       # Daily API sync script
├── location_report.py      # Generate location history reports
├── airport_matcher.py      # Match flight coordinates to airports
├── run_daily_sync.sh       # Cron wrapper with healthchecks
├── requirements.txt        # psycopg2-binary, requests, geopy, ftfy
└── README.md               # This file
```

## Configuration

`config.py` contains:
```python
# Database
DB_HOST = "10.8.0.8"
DB_PORT = 5432
DB_NAME = "mylocation"
DB_USER = "mylocation"
DB_PASSWORD = "..."

# FollowMee API
FOLLOWMEE_USERNAME = "lalabert"
FOLLOWMEE_API_KEY = "..."
FOLLOWMEE_DEVICE_ID = "11843940"

# Import settings
DEVICE_ID = "followmee"
KML_DIR = "/home/stu/kml"
```

## Daily Sync

**Cron job** (5am daily):
```
0 5 * * * /home/stu/code/mylocation/run_daily_sync.sh
```

**What it does:**
1. Fetches last 48 hours from FollowMee API
2. Checks for gaps in last 7 days
3. Attempts to fill any missing days
4. Pings healthchecks.io on success/failure

**Healthchecks:** https://hc.mees.st/ping/32960f21-f84a-4635-9de5-94dfbca6e16c

## Scripts

### Import historical KML files (one-time)
```bash
cd ~/code/mylocation
./venv/bin/python3 kml_loader.py
```

### Manual sync
```bash
# Daily sync (last 48 hours + gap check)
./venv/bin/python3 followmee_sync.py --daily

# Backfill N days
./venv/bin/python3 followmee_sync.py --backfill 45
```

### Generate location reports
```bash
./venv/bin/python3 location_report.py
# Outputs: location_report.html, ~/location_report.html, ~/location_report.md
```

### Generate flight/journey reports
```bash
./venv/bin/python3 airport_matcher.py
# Outputs: ~/all_flights.md
```

## Airport Matcher

The `airport_matcher.py` script analyses GPS data to identify flights and long-distance journeys (>200km), then matches start/end coordinates to the nearest airport or train station within 10km.

**Data sources:**
- OpenFlights airport database (6,000+ airports with IATA codes)
- Built-in train station database (Eurostar, TGV, major European stations)

**Included train stations:**
- UK: St Pancras International, Ebbsfleet International, Ashford International
- France: Gare du Nord, Gare de Lyon, Gare de l'Est, Lille Europe, Lyon Part-Dieu, Avignon TGV, Strasbourg, Bordeaux, Poitiers, Rennes
- Belgium: Brussels Midi
- Switzerland: Zurich HB, Basel SBB
- Germany: Cologne, Dusseldorf, Hamburg, Berlin, Munich
- Netherlands: Amsterdam Centraal

**Output format:**
```
| Date | From | To | Distance | Duration |
|------|------|-----|----------|----------|
| 2014-06-13 | EWR (Newark Liberty International Airport) | LHR (London Heathrow Airport) | 5578km | 13.0h |
| 2019-01-12 | QQS (St Pancras Intl) | XPG (Gare du Nord) | 344km | 4.7h |
```

**How journeys are detected:**
- Consecutive GPS points >200km apart
- Time gap between 0.5 and 24 hours
- Groups into routes and counts frequency

## FollowMee API

- **Docs:** https://followmee.com/apidoc.aspx
- **Rate limit:** 1 request/minute
- **History limit:** 45 days via daterangefordevice, 7 days via historyfordevice

Key endpoints:
```
# Device list
GET /api/info.aspx?key=...&username=...&function=devicelist

# Date range history
GET /api/tracks.aspx?key=...&username=...&output=json&function=daterangefordevice&deviceid=...&from=YYYY-MM-DD&to=YYYY-MM-DD

# Hour history (1-168 hours)
GET /api/tracks.aspx?key=...&username=...&output=json&function=historyfordevice&deviceid=...&history=48
```

## Useful Queries

### Count by source
```sql
SELECT source_type, COUNT(*) FROM gps_points GROUP BY source_type;
```

### Date range
```sql
SELECT MIN(ts), MAX(ts) FROM gps_points;
```

### Points per year
```sql
SELECT EXTRACT(YEAR FROM ts) as year, COUNT(*)
FROM gps_points
GROUP BY year ORDER BY year;
```

### Find gaps in data
```sql
SELECT d::date as missing_day
FROM generate_series('2024-01-01'::date, CURRENT_DATE, '1 day') d
WHERE NOT EXISTS (
    SELECT 1 FROM gps_points WHERE ts::date = d::date
);
```

### Cluster locations (stationary points)
```sql
WITH stationary AS (
    SELECT geom::geometry as geom, ts
    FROM gps_points
    WHERE speed_mph IS NULL OR speed_mph <= 5
)
SELECT
    ST_ClusterDBSCAN(geom, eps := 0.005, minpoints := 3) OVER() as cluster_id,
    COUNT(*) as points,
    AVG(ST_Y(geom)) as lat,
    AVG(ST_X(geom)) as lon
FROM stationary
GROUP BY cluster_id
ORDER BY points DESC;
```

### Points near a location
```sql
SELECT * FROM gps_points
WHERE ST_DWithin(
    geom,
    ST_SetSRID(ST_MakePoint(-0.497, 51.208), 4326)::geography,
    1000  -- meters
)
ORDER BY ts DESC LIMIT 100;
```

## Network Setup

This VM reaches the database via WireGuard tunnel through the host:
```bash
# Route added (persistent via netplan)
ip route add 10.8.0.0/24 via 192.168.128.9
```

Netplan config: `/etc/netplan/60-wireguard-route.yaml`

## Dependencies

```bash
# Activate venv
source ~/code/mylocation/venv/bin/activate

# Install
pip install psycopg2-binary requests geopy ftfy
```

## Reports

### Location History Report
Generated by `location_report.py`:
- `~/location_report.html` - Full HTML report
- `~/location_report.md` - Markdown version

Contents:
- All locations ranked by time spent (clustered stationary points)
- Countries by time spent
- Overnight stays (locations with nighttime points 23:00-06:00)
- Yearly travel summary

### Flight/Journey Report
Generated by `airport_matcher.py`:
- `~/all_flights.md` - All journeys >200km with airport matching

Contents:
- Routes by frequency (e.g., "LHR -> JFK: 15 trips")
- All journeys chronologically with IATA codes and full airport/station names
- Match statistics (typically 85-90% of coordinates match to airports)

### Overnight Journeys Report
Generated via SQL query (see location_report.py):
- `~/overnight_journeys.md` - Nights where you ended in one place and woke up >200km away

---

*Created: 2026-01-21*
