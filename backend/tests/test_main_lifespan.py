from pathlib import Path

import pytest
from sqlalchemy import inspect, text

from config import get_settings
from db.migrate import file_database_url, to_sync_database_url
from db.repositories.question_repository import QuestionRepository
from db import seed as seed_module
from main import app, lifespan

SAMPLE_YAML = """\
questions:
  - id: 1
    title: Two Sum
    difficulty: easy
    description: |
      Return indices of two numbers that add up to target.
    examples:
      - input: "nums = [2,7,11,15], target = 9"
        output: "[0,1]"
        explanation: null
    constraints:
      - "2 <= len(nums) <= 10^4"
    starter_code:
      python: |
        def solve(nums, target):
            pass
"""


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _column_names(database_url: str, table: str) -> set[str]:
    from sqlalchemy import create_engine as create_sync_engine

    engine = create_sync_engine(to_sync_database_url(database_url))
    try:
        with engine.connect() as conn:
            return {column["name"] for column in inspect(conn).get_columns(table)}
    finally:
        engine.dispose()


# lifespan 應執行 init_db，並掛 engine / session_factory 到 app.state。
@pytest.mark.anyio
async def test_lifespan_runs_init_db_and_exposes_session_factory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    database_url = file_database_url(tmp_path / "lifespan.db")
    monkeypatch.setenv("DATABASE_URL", database_url)

    async with lifespan(app):
        assert app.state.engine is not None
        assert app.state.session_factory is not None
        assert app.state.deps is not None

        async with app.state.session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1

    assert "difficulty" in _column_names(database_url, "questions")


# lifespan 應在 init_db 後 seed YAML 題目進 DB。
@pytest.mark.anyio
async def test_lifespan_seeds_questions_from_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    database_url = file_database_url(tmp_path / "lifespan_seed.db")
    yaml_path = tmp_path / "questions.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setattr(seed_module, "DEFAULT_QUESTIONS_PATH", yaml_path)

    async with lifespan(app):
        async with app.state.session_factory() as session:
            repo = QuestionRepository(session)
            questions = await repo.list_all()

    assert len(questions) == 1
    assert questions[0].id == 1
    assert questions[0].title == "Two Sum"
