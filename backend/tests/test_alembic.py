from pathlib import Path

import pytest
from sqlalchemy import inspect, text

from db import create_engine, create_session_factory, get_session, init_db
from db.migrate import downgrade, file_database_url, to_sync_database_url, upgrade_head
from db.models import Question

SAMPLE_QUESTION = {
    "id": 1,
    "title": "Two Sum",
    "description": "Return indices of two numbers that add up to target.",
    "examples": [{"input": "x", "output": "y", "explanation": None}],
    "constraints": ["n >= 1"],
    "starter_code": {"python": "pass"},
}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _table_names(database_url: str) -> set[str]:
    from sqlalchemy import create_engine as create_sync_engine

    engine = create_sync_engine(to_sync_database_url(database_url))
    try:
        with engine.connect() as conn:
            return set(inspect(conn).get_table_names())
    finally:
        engine.dispose()


# 空 DB 執行 upgrade head 後應有 questions 表。
def test_upgrade_head_creates_questions_table(tmp_path: Path):
    database_url = file_database_url(tmp_path / "migrate.db")

    upgrade_head(database_url)

    assert "questions" in _table_names(database_url)


# downgrade -1 應移除 questions 表。
def test_downgrade_one_drops_questions_table(tmp_path: Path):
    database_url = file_database_url(tmp_path / "migrate.db")

    upgrade_head(database_url)
    downgrade("-1", database_url)

    assert "questions" not in _table_names(database_url)


# init_db 應透過 Alembic 建表，async session 可寫入 questions。
@pytest.mark.anyio
async def test_init_db_runs_migrations_and_allows_inserts(tmp_path: Path):
    database_url = file_database_url(tmp_path / "app.db")
    engine = create_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        await init_db(engine)
        async with get_session(session_factory) as session:
            session.add(Question(**SAMPLE_QUESTION))
            await session.commit()

        async with get_session(session_factory) as session:
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = {row[0] for row in result}
            assert "questions" in tables
            assert "alembic_version" in tables
    finally:
        await engine.dispose()
