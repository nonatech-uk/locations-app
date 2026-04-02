-- Filtered view of gps_points: excludes pet trackers and low-accuracy points (>100m)
CREATE OR REPLACE VIEW gps_points_clean AS
SELECT *
FROM gps_points
WHERE source_type != 'tractive'
  AND (accuracy_m IS NULL OR accuracy_m <= 50);
