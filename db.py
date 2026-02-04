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

def insert_points(points):
    """
    Insert GPS points with deduplication.

    points: list of dicts with keys matching gps_points columns
    Returns: (inserted_count, skipped_count)
    """
    if not points:
        return 0, 0

    conn = get_connection()
    cur = conn.cursor()

    # Build insert with ON CONFLICT DO NOTHING
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
