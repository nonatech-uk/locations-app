from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Postgres
    db_host: str = "192.168.128.9"
    db_port: int = 5432
    db_name: str = "mylocation"
    db_user: str = "mylocation"
    db_password: str = ""
    db_sslmode: str = "require"

    # OwnTracks
    owntracks_secret: str = ""

    # Pipeline ingest
    pipeline_secret: str = ""

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8100
    image_cache_dir: str = "/data/images"
    db_pool_min: int = 2
    db_pool_max: int = 10
    cors_origins: list[str] = [
        "https://locations.mees.st",
        "http://localhost:5173",
    ]

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password} sslmode={self.db_sslmode}"
        )


settings = Settings()
