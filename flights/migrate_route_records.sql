-- Add route record support to flights table
-- Run: psql -h 10.8.0.8 -U mylocation -d mylocation -f flights/migrate_route_records.sql

BEGIN;

-- Add is_route column
DO $$ BEGIN
    ALTER TABLE flights ADD COLUMN is_route BOOLEAN DEFAULT FALSE;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- Add times_flown column
DO $$ BEGIN
    ALTER TABLE flights ADD COLUMN times_flown INTEGER DEFAULT NULL;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- Mark known route records (placeholder dates)
UPDATE flights SET is_route = TRUE
WHERE date IN ('1990-01-01', '1970-01-01')
  AND is_route = FALSE;

COMMIT;
