"""Connection pool dependency."""

from mees_shared.db import get_conn, init_pool as _init_pool, close_pool  # noqa: F401

from src.api.settings import settings


def init_pool() -> None:
    _init_pool(settings.dsn, settings.db_pool_min, settings.db_pool_max)
