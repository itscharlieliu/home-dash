from __future__ import annotations

from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, declared_attr

from .config import settings


class Base(DeclarativeBase):
    """Base declarative class with naming conventions."""

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[override]
        return cls.__name__.lower()


def _ensure_sqlite_directory(database_url: str) -> None:
    if database_url.startswith("sqlite+aiosqlite:///"):
        path = database_url.replace("sqlite+aiosqlite:///", "", 1)
        db_path = Path(path)
        if not db_path.parent.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_directory(settings.database_url)

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.sqlalchemy_echo,
    future=True,
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    from . import models  # noqa: F401  # ensure models are imported

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

