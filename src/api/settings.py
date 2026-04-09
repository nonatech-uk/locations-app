from pathlib import Path

from mees_shared.settings import BaseAppSettings


class Settings(BaseAppSettings):
    db_host: str = "192.168.128.9"
    db_name: str = "mylocation"
    db_user: str = "mylocation"
    db_sslmode: str = "require"
    api_port: int = 8100
    auth_enabled: bool = False

    cors_origins: list[str] = [
        "https://locations.mees.st",
        "http://localhost:5173",
    ]

    # OwnTracks
    owntracks_secret: str = ""

    # Pipeline ingest
    pipeline_secret: str = ""

    # Image cache
    image_cache_dir: str = "/data/images"

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
