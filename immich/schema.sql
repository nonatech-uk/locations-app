-- Mapping table: tracks which Immich assets have been synced to gps_points.
-- Enables incremental sync with update and delete detection.
-- album_names stores the album(s) each photo belongs to at sync time,
-- queried from Immich via album_asset + album and refreshed on each run.

CREATE TABLE IF NOT EXISTS immich_sync (
    asset_id         UUID PRIMARY KEY,
    gps_point_id     BIGINT NOT NULL REFERENCES gps_points(id) ON DELETE CASCADE,
    album_names      TEXT[],
    synced_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    exif_updated_at  TIMESTAMPTZ,
    asset_updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS immich_sync_gps_point_id_idx ON immich_sync(gps_point_id);
