-- HA Companion (iOS Home Assistant Companion app) ingestion support.
-- Adds motion-classification columns, accepts source_type='ha-companion',
-- and adjusts views so OwnTracks remains canonical for lat/lon while
-- HA Companion fills wifi/motion gaps and provides location fallback.

BEGIN;

-- Motion-activity classification from CMMotionActivityManager (only HA Companion has this).
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS motion_activity TEXT;
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS motion_confidence TEXT;

-- gps_points_clean: existing consumers expect canonical OwnTracks coordinates.
-- HA Companion duplicates the same iPhone GPS, so exclude it from the default
-- view to avoid double-counting on dwell/distance queries.
CREATE OR REPLACE VIEW gps_points_clean AS
SELECT *
FROM gps_points
WHERE source_type NOT IN ('tractive', 'ha-companion')
  AND (accuracy_m IS NULL OR accuracy_m <= 50);

-- gps_points_with_fallback: opt-in view that prefers OwnTracks within ±60s,
-- and falls back to HA Companion when OwnTracks has a gap. Use this for
-- queries that care about completeness over canonicity.
CREATE OR REPLACE VIEW gps_points_with_fallback AS
WITH ranked AS (
    SELECT
        p.*,
        CASE p.source_type WHEN 'owntracks' THEN 0 ELSE 1 END AS src_rank,
        date_trunc('minute', p.ts) AS minute_bucket
    FROM gps_points p
    WHERE p.source_type IN ('owntracks', 'ha-companion')
      AND (p.accuracy_m IS NULL OR p.accuracy_m <= 50)
)
SELECT *
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY minute_bucket
            ORDER BY src_rank, ts
        ) AS rn
    FROM ranked
) sub
WHERE rn = 1;

COMMIT;
