"""Async SQLite session infrastructure for repositories."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """ORM declarative base; models register tables on this metadata."""


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# session_factory() 呼叫後回傳一個 AsyncSession
# AsyncSession 本身就是 context manager
# 所以可以直接 async with
@asynccontextmanager
async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def init_db(engine: AsyncEngine) -> None:
    """Apply Alembic migrations to the database behind ``engine``."""
    from db.migrate import upgrade_head

    database_url = engine.url.render_as_string(hide_password=False)
    await asyncio.to_thread(upgrade_head, database_url)
