"""Overview statistics endpoint."""

from fastapi import APIRouter, Depends

from src.api.deps import get_conn
from src.api.models import OverviewStats

router = APIRouter(prefix="/stats")


@router.get("/overview", response_model=OverviewStats)
def overview(conn=Depends(get_conn)):
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM gps_points")
    gps_points = cur.fetchone()[0]

    cur.close()
    return OverviewStats(gps_points=gps_points, skiing_days=0)
