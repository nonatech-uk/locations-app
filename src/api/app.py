"""My-Locations API — FastAPI application."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.settings import settings
from src.api.deps import close_pool, init_pool
from src.api.routers import gps, owntracks, place_types, places, skiing, stats

STATIC_DIR = Path(_project_root) / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(
    title="My-Locations API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gps.router, prefix="/api/v1", tags=["gps"])
app.include_router(skiing.router, prefix="/api/v1", tags=["skiing"])
app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
app.include_router(place_types.router, prefix="/api/v1", tags=["place_types"])
app.include_router(places.router, prefix="/api/v1", tags=["places"])
app.include_router(owntracks.router, tags=["owntracks"])


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve React SPA
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(
            STATIC_DIR / "index.html",
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
