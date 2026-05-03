import psycopg2
from psycopg2.extras import execute_values
import config

def get_connection():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        sslmode='require'
    )

def ensure_unique_constraint():
    """Ensure unique constraint exists for deduplication."""
    conn = get_connection()
    cur = conn.cursor()

    # Check if constraint exists
    cur.execute("""
        SELECT 1 FROM pg_constraint
        WHERE conname = 'gps_points_device_ts_unique'
    """)

    if not cur.fetchone():
        print("Creating unique constraint on (device_id, ts)...")
        cur.execute("""
            ALTER TABLE gps_points
            ADD CONSTRAINT gps_points_device_ts_unique
            UNIQUE (device_id, ts)
        """)
        conn.commit()
        print("Constraint created.")

    cur.close()
    conn.close()

_OWNTRACKS_EXTRA_COLS = (
    "battery_status", "connection_type", "wifi_ssid", "wifi_bssid",
    "vertical_accuracy_m", "trigger_type", "monitoring_mode", "topic",
    "in_regions", "pressure_kpa", "poi", "created_at", "raw_payload",
)


def insert_points(points):
    """
    Insert GPS points with deduplication.

    points: list of dicts with keys matching gps_points columns
    Returns: (inserted_count, skipped_count)
    """
    if not points:
        return 0, 0

    has_owntracks_extras = any(
        any(p.get(col) is not None for col in _OWNTRACKS_EXTRA_COLS) for p in points
    )

    conn = get_connection()
    cur = conn.cursor()

    if has_owntracks_extras:
        from psycopg2.extras import Json
        for p in points:
            rp = p.get("raw_payload")
            if rp is not None and not isinstance(rp, Json):
                p["raw_payload"] = Json(rp)
            for col in _OWNTRACKS_EXTRA_COLS:
                p.setdefault(col, None)

        sql = """
            INSERT INTO gps_points (
                device_id, device_name, ts, lat, lon, altitude_m, altitude_ft,
                speed_mph, speed_kmh, direction, accuracy_m, battery_pct, source_type,
                battery_status, connection_type, wifi_ssid, wifi_bssid,
                vertical_accuracy_m, trigger_type, monitoring_mode, topic,
                in_regions, pressure_kpa, poi, created_at, raw_payload, geom
            ) VALUES %s
            ON CONFLICT (device_id, ts) DO NOTHING
        """
        template = """(
            %(device_id)s, %(device_name)s, %(ts)s, %(lat)s, %(lon)s,
            %(altitude_m)s, %(altitude_ft)s, %(speed_mph)s, %(speed_kmh)s,
            %(direction)s, %(accuracy_m)s, %(battery_pct)s, %(source_type)s,
            %(battery_status)s, %(connection_type)s, %(wifi_ssid)s, %(wifi_bssid)s,
            %(vertical_accuracy_m)s, %(trigger_type)s, %(monitoring_mode)s, %(topic)s,
            %(in_regions)s, %(pressure_kpa)s, %(poi)s, %(created_at)s, %(raw_payload)s,
            ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
        )"""
    else:
        sql = """
            INSERT INTO gps_points (
                device_id, device_name, ts, lat, lon, altitude_m, altitude_ft,
                speed_mph, speed_kmh, direction, accuracy_m, battery_pct, source_type, geom
            ) VALUES %s
            ON CONFLICT (device_id, ts) DO NOTHING
        """
        template = """(
            %(device_id)s, %(device_name)s, %(ts)s, %(lat)s, %(lon)s,
            %(altitude_m)s, %(altitude_ft)s, %(speed_mph)s, %(speed_kmh)s,
            %(direction)s, %(accuracy_m)s, %(battery_pct)s, %(source_type)s,
            ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
        )"""

    execute_values(cur, sql, points, template=template)
    inserted = cur.rowcount
    skipped = len(points) - inserted

    conn.commit()
    cur.close()
    conn.close()

    return inserted, skipped
