"""Overview statistics endpoint."""

from fastapi import APIRouter, Depends

from src.api.deps import CurrentUser, get_conn, get_current_user
from src.api.models import OverviewStats

router = APIRouter(prefix="/stats")


@router.get("/overview", response_model=OverviewStats)
def overview(_user: CurrentUser = Depends(get_current_user), conn=Depends(get_conn)):
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM gps_points")
    gps_points = cur.fetchone()[0]

    cur.close()
    return OverviewStats(gps_points=gps_points, skiing_days=0)
