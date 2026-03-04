"""Connection pool dependency."""

from collections.abc import Generator

from psycopg2.pool import ThreadedConnectionPool

from src.api.settings import settings

pool: ThreadedConnectionPool | None = None


def init_pool() -> None:
    global pool
    pool = ThreadedConnectionPool(
        settings.db_pool_min,
        settings.db_pool_max,
        settings.dsn,
    )


def close_pool() -> None:
    global pool
    if pool:
        pool.closeall()
        pool = None


def get_conn() -> Generator:
    assert pool is not None, "Connection pool not initialised"
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)
