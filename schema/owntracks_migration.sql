-- OwnTracks schema expansion: capture every field OwnTracks offers
-- All new columns are nullable with no defaults → instant ALTER, no table rewrite

BEGIN;

-- New columns on gps_points for OwnTracks-specific data
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS battery_status SMALLINT;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS connection_type TEXT;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS wifi_ssid TEXT;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS wifi_bssid TEXT;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS vertical_accuracy_m DOUBLE PRECISION;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS trigger_type CHAR(1);
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS monitoring_mode SMALLINT;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS topic TEXT;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS in_regions TEXT[];
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS pressure_kpa DOUBLE PRECISION;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS poi TEXT;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS raw_payload JSONB;

-- Region enter/leave events
CREATE TABLE IF NOT EXISTS owntracks_transitions (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    event TEXT NOT NULL,
    region_name TEXT,
    region_id TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    accuracy_m DOUBLE PRECISION,
    raw_payload JSONB,
    UNIQUE (device_id, ts, region_name)
);

-- Geofence/waypoint definitions synced from device
CREATE TABLE IF NOT EXISTS owntracks_waypoints (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    region_name TEXT,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    radius_m INTEGER,
    raw_payload JSONB,
    UNIQUE (device_id, region_name)
);

-- Catch-all for lwt, status, and other message types
CREATE TABLE IF NOT EXISTS owntracks_events (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    message_type TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    raw_payload JSONB,
    UNIQUE (device_id, ts, message_type)
);

COMMIT;
