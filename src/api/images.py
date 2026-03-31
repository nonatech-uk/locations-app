"""Image prefetch and cache manager for flight route maps and aircraft photos."""

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image
from staticmap import CircleMarker, Line, StaticMap

from src.api.settings import settings

log = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)

ROUTE_THUMB = (200, 120)
ROUTE_FULL = (800, 500)
AIRCRAFT_THUMB = (200, 150)
AIRCRAFT_FULL = (800, 600)

LIGHT_TILES = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
PLANESPOTTERS_API = "https://api.planespotters.net/pub/photos/reg"


def _cache_dir() -> Path:
    return Path(settings.image_cache_dir)


def _routes_dir() -> Path:
    d = _cache_dir() / "routes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _aircraft_dir() -> Path:
    d = _cache_dir() / "aircraft"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _route_key(dep_airport: str, arr_airport: str) -> str:
    """Canonical key for a route — always uppercase, sorted alphabetically does NOT apply (direction matters)."""
    return f"{dep_airport.upper()}_{arr_airport.upper()}"


def route_image_path(dep_airport: str, arr_airport: str, size: str) -> Path:
    return _routes_dir() / f"{_route_key(dep_airport, arr_airport)}_{size}.png"


def aircraft_image_path(registration: str, size: str) -> Path:
    reg = registration.replace("-", "").upper()
    return _aircraft_dir() / f"{reg}_{size}.jpg"


def has_route_image(dep_airport: str | None, arr_airport: str | None) -> bool:
    if not dep_airport or not arr_airport:
        return False
    return route_image_path(dep_airport, arr_airport, "thumb").exists()


def has_aircraft_image(registration: str | None) -> bool:
    if not registration:
        return False
    return aircraft_image_path(registration, "thumb").exists()


def _intermediate_points(lat1: float, lon1: float, lat2: float, lon2: float, n: int = 50) -> list[tuple[float, float]]:
    """Compute intermediate points along a great circle arc."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    d = 2 * math.asin(
        math.sqrt(
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
    )
    if d < 1e-10:
        return [(math.degrees(lat1), math.degrees(lon1))]

    points = []
    for i in range(n + 1):
        f = i / n
        a = math.sin((1 - f) * d) / math.sin(d)
        b = math.sin(f * d) / math.sin(d)
        x = a * math.cos(lat1) * math.cos(lon1) + b * math.cos(lat2) * math.cos(lon2)
        y = a * math.cos(lat1) * math.sin(lon1) + b * math.cos(lat2) * math.sin(lon2)
        z = a * math.sin(lat1) + b * math.sin(lat2)
        lat = math.atan2(z, math.sqrt(x ** 2 + y ** 2))
        lon = math.atan2(y, x)
        points.append((math.degrees(lat), math.degrees(lon)))
    return points


def _render_route_map(
    dep_lat: float, dep_lon: float, arr_lat: float, arr_lon: float, width: int, height: int
) -> bytes:
    """Render a static map with a great circle arc between two airports."""
    m = StaticMap(width, height, url_template=LIGHT_TILES)

    # Great circle intermediate points
    gc_points = _intermediate_points(dep_lat, dep_lon, arr_lat, arr_lon)
    coords = [(lon, lat) for lat, lon in gc_points]

    line = Line(coords, "#4f46e5", 3)
    m.add_line(line)

    # Airport markers
    m.add_marker(CircleMarker((dep_lon, dep_lat), "#4f46e5", 6))
    m.add_marker(CircleMarker((arr_lon, arr_lat), "#4f46e5", 6))

    img = m.render()
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _render_local_map(lat: float, lon: float, width: int, height: int) -> bytes:
    """Render a static map centred on a single airport (for local flights)."""
    m = StaticMap(width, height, url_template=LIGHT_TILES)
    m.add_marker(CircleMarker((lon, lat), "#4f46e5", 8))
    img = m.render(zoom=12)
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def prefetch_route_image(dep_airport: str, arr_airport: str, dep_lat: float, dep_lon: float, arr_lat: float, arr_lon: float) -> bool:
    """Generate and cache route map images. Returns True if created."""
    thumb_path = route_image_path(dep_airport, arr_airport, "thumb")
    if thumb_path.exists():
        return False

    try:
        is_local = dep_airport.upper() == arr_airport.upper()
        if is_local:
            full_data = _render_local_map(dep_lat, dep_lon, ROUTE_FULL[0], ROUTE_FULL[1])
        else:
            full_data = _render_route_map(dep_lat, dep_lon, arr_lat, arr_lon, ROUTE_FULL[0], ROUTE_FULL[1])

        full_path = route_image_path(dep_airport, arr_airport, "full")
        full_path.write_bytes(full_data)

        img = Image.open(BytesIO(full_data))
        img.thumbnail(ROUTE_THUMB, Image.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        thumb_path.write_bytes(buf.getvalue())

        log.info("Route images cached for %s→%s", dep_airport, arr_airport)
        return True
    except Exception:
        log.exception("Failed to generate route image for %s→%s", dep_airport, arr_airport)
        return False


def prefetch_aircraft_image(registration: str) -> bool:
    """Fetch and cache aircraft photo from Planespotters.net. Returns True if created."""
    thumb_path = aircraft_image_path(registration, "thumb")
    if thumb_path.exists():
        return False

    try:
        resp = httpx.get(f"{PLANESPOTTERS_API}/{registration}", timeout=15)
        if resp.status_code != 200:
            log.warning("Planespotters returned %d for %s", resp.status_code, registration)
            return False

        data = resp.json()
        photos = data.get("photos", [])
        if not photos:
            log.info("No photos found for registration %s", registration)
            return False

        photo_url = photos[0].get("thumbnail_large", {}).get("src") or photos[0].get("thumbnail", {}).get("src")
        if not photo_url:
            return False

        img_resp = httpx.get(photo_url, timeout=30)
        if img_resp.status_code != 200:
            return False

        img = Image.open(BytesIO(img_resp.content))
        if img.mode != "RGB":
            img = img.convert("RGB")

        full_img = img.copy()
        full_img.thumbnail(AIRCRAFT_FULL, Image.Resampling.LANCZOS)
        full_path = aircraft_image_path(registration, "full")
        full_img.save(full_path, format="JPEG", quality=85)

        thumb_img = img.copy()
        thumb_img.thumbnail(AIRCRAFT_THUMB, Image.Resampling.LANCZOS)
        thumb_img.save(thumb_path, format="JPEG", quality=80)

        log.info("Aircraft images cached for %s", registration)
        return True
    except Exception:
        log.exception("Failed to fetch aircraft image for %s", registration)
        return False


def schedule_prefetch(flights: list[dict]) -> None:
    """Schedule background image prefetch for a list of flights."""
    seen_routes: set[str] = set()
    seen_reg: set[str] = set()

    for f in flights:
        dep = f.get("dep_airport")
        arr = f.get("arr_airport")
        dep_lat, dep_lon = f.get("dep_lat"), f.get("dep_lon")
        arr_lat, arr_lon = f.get("arr_lat"), f.get("arr_lon")
        reg = f.get("registration")

        if dep and arr and dep_lat and dep_lon and arr_lat and arr_lon:
            key = _route_key(dep, arr)
            if key not in seen_routes and not has_route_image(dep, arr):
                seen_routes.add(key)
                _executor.submit(prefetch_route_image, dep, arr, dep_lat, dep_lon, arr_lat, arr_lon)

        if reg and reg not in seen_reg and not has_aircraft_image(reg):
            seen_reg.add(reg)
            _executor.submit(prefetch_aircraft_image, reg)
