from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Home Dash"
    refresh_interval_seconds: int = Field(
        60, description="Default refresh interval for metric polling on the frontend."
    )
    sample_interval_seconds: int = Field(
        5, description="How frequently to snapshot metrics into the database."
    )
    history_points_limit: int = Field(
        120, description="Number of historical samples to return for charting."
    )
    database_url: str = Field(
        "sqlite+aiosqlite:///./data/home_dash.db", description="SQLAlchemy database URL."
    )
    sqlalchemy_echo: bool = Field(False, description="Enable SQL echo logging.")

    @field_validator("database_url")
    def ensure_sqlite_directory(cls, value: str) -> str:
        if value.startswith("sqlite+aiosqlite:///"):
            path = Path(value.replace("sqlite+aiosqlite:///", "", 1))
            path.parent.mkdir(parents=True, exist_ok=True)
        return value

    class Config:
        env_prefix = "HOME_DASH_"


settings = Settings()

