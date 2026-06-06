from pathlib import Path

import pytest
from sqlalchemy import text

from config import Settings
from db import create_engine, create_session_factory, get_session, init_db

IN_MEMORY_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# get_session 應能在 in-memory SQLite 上執行查詢。
@pytest.mark.anyio
async def test_get_session_executes_query_on_in_memory_db():
    engine = create_engine(IN_MEMORY_URL)
    session_factory = create_session_factory(engine)
    try:
        async with get_session(session_factory) as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await engine.dispose()


# init_db 在尚無 ORM models 時仍應可安全執行 create_all。
@pytest.mark.anyio
async def test_init_db_runs_without_error_on_empty_metadata():
    engine = create_engine(IN_MEMORY_URL)
    try:
        await init_db(engine)
    finally:
        await engine.dispose()


# 應支援 temp file SQLite（重開 engine 後仍可連線）。
@pytest.mark.anyio
async def test_temp_file_database_url_opens_session(tmp_path: Path):
    db_path = tmp_path / "test.db"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = create_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        await init_db(engine)
        async with get_session(session_factory) as session:
            await session.execute(text("SELECT 1"))
    finally:
        await engine.dispose()

    assert db_path.exists()

    engine2 = create_engine(database_url)
    session_factory2 = create_session_factory(engine2)
    try:
        async with get_session(session_factory2) as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await engine2.dispose()


# create_engine 應接受 Settings.database_url（含檔案路徑格式）。
def test_create_engine_accepts_settings_database_url():
    settings = Settings(database_url=IN_MEMORY_URL)
    engine = create_engine(settings.database_url)
    assert str(engine.url) == IN_MEMORY_URL
