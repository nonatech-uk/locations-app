CREATE TABLE rail_journeys (
    id              SERIAL PRIMARY KEY,
    date            DATE NOT NULL,
    time            TIME,
    from_station    TEXT NOT NULL,
    from_code       TEXT,
    to_station      TEXT NOT NULL,
    to_code         TEXT,
    operator        TEXT,
    ticket_type     TEXT,
    direction       TEXT,
    reference       TEXT,
    train           TEXT,
    via             TEXT,
    price           NUMERIC(8,2),
    currency        TEXT,
    from_lat        DOUBLE PRECISION,
    from_lon        DOUBLE PRECISION,
    to_lat          DOUBLE PRECISION,
    to_lon          DOUBLE PRECISION,
    source          TEXT NOT NULL,
    UNIQUE(date, time, from_station, to_station)
);

CREATE INDEX idx_rail_journeys_date ON rail_journeys(date);
CREATE INDEX idx_rail_journeys_operator ON rail_journeys(operator);

GRANT SELECT ON rail_journeys TO mcp_readonly;
