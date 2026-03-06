#!/usr/bin/env python3
"""Sync GPS-tagged photos from Immich to gps_points."""

import argparse
import sys

import psycopg2
from psycopg2.extras import execute_values

import config


SOURCE_TYPE = "immich"


def get_immich_connection():
    """Read-only connection to Immich postgres."""
    return psycopg2.connect(
        host=config.IMMICH_DB_HOST,
        port=config.IMMICH_DB_PORT,
        dbname=config.IMMICH_DB_NAME,
        user=config.IMMICH_DB_USER,
        password=config.IMMICH_DB_PASSWORD,
        options="-c default_transaction_read_only=on",
    )


def get_app_connection():
    """Connection to the my-locations app database."""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        sslmode="require",
    )


def ensure_schema(app_conn):
    """Create immich_sync table if it doesn't exist."""
    cur = app_conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS immich_sync (
            asset_id         UUID PRIMARY KEY,
            gps_point_id     BIGINT NOT NULL REFERENCES gps_points(id) ON DELETE CASCADE,
            album_names      TEXT[],
            synced_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            exif_updated_at  TIMESTAMPTZ,
            asset_updated_at TIMESTAMPTZ
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS immich_sync_gps_point_id_idx
        ON immich_sync(gps_point_id)
    """)
    app_conn.commit()
    cur.close()


def fetch_gps_assets(immich_conn, since=None):
    """Fetch GPS-tagged assets from Immich.

    Args:
        since: If set, only fetch assets updated after this timestamp.
               Checks both asset.updatedAt and asset_exif.updatedAt.

    Returns list of dicts with asset data.
    """
    cur = immich_conn.cursor()

    where_clause = ""
    params = []
    if since:
        where_clause = """
            AND (a."updatedAt" > %s OR e."updatedAt" > %s)
        """
        params = [since, since]

    cur.execute(f"""
        SELECT
            a.id,
            e.latitude,
            e.longitude,
            e."dateTimeOriginal",
            a."updatedAt" AS asset_updated,
            e."updatedAt" AS exif_updated
        FROM asset a
        JOIN asset_exif e ON a.id = e."assetId"
        WHERE e.latitude IS NOT NULL
          AND a."deletedAt" IS NULL
          AND a.status = 'active'
          {where_clause}
        ORDER BY e."dateTimeOriginal"
    """, params)

    assets = []
    for row in cur.fetchall():
        assets.append({
            "asset_id": row[0],
            "lat": row[1],
            "lon": row[2],
            "ts": row[3],
            "asset_updated": row[4],
            "exif_updated": row[5],
        })

    cur.close()
    return assets


def fetch_album_names(immich_conn, asset_ids):
    """Fetch album names for a set of asset IDs.

    Returns dict mapping asset_id -> list of album names.
    """
    if not asset_ids:
        return {}

    cur = immich_conn.cursor()
    cur.execute("""
        SELECT aa."assetId", array_agg(al."albumName" ORDER BY al."albumName")
        FROM album_asset aa
        JOIN album al ON aa."albumId" = al.id
        WHERE aa."assetId" = ANY(%s::uuid[])
        GROUP BY aa."assetId"
    """, (list(asset_ids),))

    result = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    return result


def fetch_all_active_asset_ids(immich_conn):
    """Fetch all active GPS-tagged asset IDs from Immich."""
    cur = immich_conn.cursor()
    cur.execute("""
        SELECT a.id
        FROM asset a
        JOIN asset_exif e ON a.id = e."assetId"
        WHERE e.latitude IS NOT NULL
          AND a."deletedAt" IS NULL
          AND a.status = 'active'
    """)
    ids = {row[0] for row in cur.fetchall()}
    cur.close()
    return ids


def get_last_sync_time(app_conn):
    """Get the most recent synced_at from immich_sync."""
    cur = app_conn.cursor()
    cur.execute("SELECT max(synced_at) FROM immich_sync")
    result = cur.fetchone()[0]
    cur.close()
    return result


def get_synced_assets(app_conn):
    """Get all synced asset mappings.

    Returns dict mapping asset_id -> (gps_point_id, album_names).
    """
    cur = app_conn.cursor()
    cur.execute("SELECT asset_id, gps_point_id, album_names FROM immich_sync")
    result = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
    cur.close()
    return result


def make_device_id(asset_id):
    """Create a unique device_id from asset UUID prefix."""
    return f"immich-{str(asset_id)[:8]}"


def upsert_point(app_cur, asset, album_names):
    """Insert or update a GPS point and its immich_sync mapping.

    Returns: 'inserted' or 'updated'
    """
    device_id = make_device_id(asset["asset_id"])
    albums = album_names.get(asset["asset_id"])

    # Try insert into gps_points first
    app_cur.execute("""
        INSERT INTO gps_points (
            device_id, device_name, ts, lat, lon,
            altitude_m, altitude_ft, speed_mph, speed_kmh,
            direction, accuracy_m, battery_pct, source_type, geom
        ) VALUES (
            %s, %s, %s, %s, %s,
            NULL, NULL, NULL, NULL,
            NULL, NULL, NULL, %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        ON CONFLICT (device_id, ts) DO UPDATE SET
            lat = EXCLUDED.lat,
            lon = EXCLUDED.lon,
            geom = EXCLUDED.geom
        RETURNING id, (xmax = 0) AS is_insert
    """, (
        device_id, None, asset["ts"], asset["lat"], asset["lon"],
        SOURCE_TYPE,
        asset["lon"], asset["lat"],
    ))

    gps_point_id, is_insert = app_cur.fetchone()

    # Upsert immich_sync mapping
    app_cur.execute("""
        INSERT INTO immich_sync (asset_id, gps_point_id, album_names, exif_updated_at, asset_updated_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (asset_id) DO UPDATE SET
            gps_point_id = EXCLUDED.gps_point_id,
            album_names = EXCLUDED.album_names,
            synced_at = now(),
            exif_updated_at = EXCLUDED.exif_updated_at,
            asset_updated_at = EXCLUDED.asset_updated_at
    """, (
        asset["asset_id"], gps_point_id, albums,
        asset["exif_updated"], asset["asset_updated"],
    ))

    return "inserted" if is_insert else "updated"


def delete_removed(app_conn, immich_conn, dry_run=False):
    """Delete gps_points for assets that no longer exist in Immich.

    Returns count of deleted points.
    """
    active_ids = fetch_all_active_asset_ids(immich_conn)
    synced = get_synced_assets(app_conn)

    to_delete = [
        (asset_id, gps_point_id)
        for asset_id, (gps_point_id, _) in synced.items()
        if asset_id not in active_ids
    ]

    if not to_delete:
        return 0

    if dry_run:
        print(f"  Would delete {len(to_delete)} points for removed assets")
        return len(to_delete)

    cur = app_conn.cursor()
    point_ids = [pid for _, pid in to_delete]
    asset_ids = [aid for aid, _ in to_delete]

    # Delete from immich_sync first (FK), then gps_points
    cur.execute("DELETE FROM immich_sync WHERE asset_id = ANY(%s)", (asset_ids,))
    cur.execute("DELETE FROM gps_points WHERE id = ANY(%s)", (point_ids,))
    app_conn.commit()
    cur.close()

    return len(to_delete)


def refresh_album_names(app_conn, immich_conn, dry_run=False):
    """Refresh album names for all synced assets.

    Album membership changes don't update asset.updatedAt, so we
    re-query all albums on every run.

    Returns count of updated rows.
    """
    synced = get_synced_assets(app_conn)
    if not synced:
        return 0

    all_asset_ids = list(synced.keys())
    album_names = fetch_album_names(immich_conn, all_asset_ids)

    # Find assets where album_names changed
    to_update = []
    for asset_id, (_, current_albums) in synced.items():
        new_albums = album_names.get(asset_id)
        if current_albums != new_albums:
            to_update.append((asset_id, new_albums))

    if not to_update:
        return 0

    if dry_run:
        print(f"  Would update album names for {len(to_update)} assets")
        return len(to_update)

    cur = app_conn.cursor()
    execute_values(
        cur,
        "UPDATE immich_sync SET album_names = data.albums FROM (VALUES %s) AS data(id, albums) WHERE asset_id = data.id::uuid",
        [(str(aid), albums) for aid, albums in to_update],
        template="(%s, %s::text[])",
    )
    app_conn.commit()
    cur.close()

    return len(to_update)


def sync(full=False, dry_run=False):
    """Run Immich GPS sync.

    Args:
        full: If True, sync all assets. Otherwise, only sync changes since last run.
        dry_run: If True, don't make any changes.
    """
    immich_conn = get_immich_connection()
    app_conn = get_app_connection()

    try:
        ensure_schema(app_conn)

        # Determine what to fetch
        since = None
        if not full:
            since = get_last_sync_time(app_conn)
            if since:
                print(f"Incremental sync since {since}")
            else:
                print("No previous sync found, running full sync")
                full = True

        if full:
            print("Full sync: fetching all GPS-tagged assets...")

        assets = fetch_gps_assets(immich_conn, since=since if not full else None)
        print(f"Found {len(assets)} assets to process")

        if not assets and not full:
            # Still need to check deletions and album changes
            deleted = delete_removed(app_conn, immich_conn, dry_run)
            album_updates = refresh_album_names(app_conn, immich_conn, dry_run)
            print(f"No new/updated assets. Deleted: {deleted}, album updates: {album_updates}")
            return

        # Fetch album names for all assets being processed
        asset_ids = [a["asset_id"] for a in assets]
        album_names = fetch_album_names(immich_conn, asset_ids)

        # Upsert points
        inserted = 0
        updated = 0

        if dry_run:
            print(f"  Dry run: would process {len(assets)} assets")
        else:
            cur = app_conn.cursor()
            for asset in assets:
                result = upsert_point(cur, asset, album_names)
                if result == "inserted":
                    inserted += 1
                else:
                    updated += 1

                # Commit in batches of 1000
                if (inserted + updated) % 1000 == 0:
                    app_conn.commit()
                    print(f"  Progress: {inserted + updated}/{len(assets)}...", flush=True)

            app_conn.commit()
            cur.close()

        print(f"Points: {inserted} inserted, {updated} updated")

        # Delete removed assets
        deleted = delete_removed(app_conn, immich_conn, dry_run)
        print(f"Deleted: {deleted}")

        # Refresh album names for all synced assets
        album_updates = refresh_album_names(app_conn, immich_conn, dry_run)
        print(f"Album updates: {album_updates}")

        print("Sync complete")

    finally:
        immich_conn.close()
        app_conn.close()


def main():
    parser = argparse.ArgumentParser(description="Sync Immich photo GPS data")
    parser.add_argument("--full", action="store_true",
                        help="Full sync (all assets, not just changes)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")

    args = parser.parse_args()
    sync(full=args.full, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
