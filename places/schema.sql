-- Places: named locations with types and spatial matching

CREATE TABLE IF NOT EXISTS place_type (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

INSERT INTO place_type (name) VALUES
    ('Home'), ('Office'), ('Airport'), ('Restaurant'), ('Hotel'), ('Pub')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS place (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    place_type_id INTEGER NOT NULL REFERENCES place_type(id),
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    geom GEOGRAPHY(POINT, 4326) GENERATED ALWAYS AS
        (ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography) STORED,
    distance_m INTEGER NOT NULL DEFAULT 200,
    date_from DATE,
    date_to DATE,
    notes TEXT,
    wifi_ssids TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_place_geom ON place USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_place_type_id ON place (place_type_id);

-- App user access
GRANT SELECT, INSERT, UPDATE, DELETE ON place, place_type TO mylocation;
GRANT USAGE, SELECT ON SEQUENCE place_id_seq, place_type_id_seq TO mylocation;

-- Read-only access for MCP
GRANT SELECT ON place_type TO mcp_readonly;
GRANT SELECT ON place TO mcp_readonly;

-- Migration: add wifi_ssids to existing tables
ALTER TABLE place ADD COLUMN IF NOT EXISTS wifi_ssids TEXT[];
