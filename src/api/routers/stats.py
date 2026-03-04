"""Overview statistics endpoint."""

from fastapi import APIRouter, Depends

from src.api.deps import get_conn
from src.api.models import OverviewStats

router = APIRouter(prefix="/stats")


@router.get("/overview", response_model=OverviewStats)
def overview(conn=Depends(get_conn)):
    cur = conn.cursor()

    counts = {}
    for table, key in [
        ("gps_points", "gps_points"),
        ("flights", "flights"),
        ("skiing_days", "skiing_days"),
        ("ga_flights", "ga_flights"),
    ]:
        cur.execute(f"SELECT count(*) FROM {table}")  # noqa: S608
        counts[key] = cur.fetchone()[0]

    cur.close()
    return OverviewStats(**counts)
