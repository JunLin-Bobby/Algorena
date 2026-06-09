"""Phase 3 integration: migration → seed → query on a fresh session."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from db import create_engine, create_session_factory, init_db
from db.migrate import file_database_url
from db.models import Question
from db.repositories.question_repository import QuestionRepository
from db.seed import load_questions_from_yaml, seed_questions

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
        explanation: "Because nums[0] + nums[1] == 9."
    constraints:
      - "2 <= len(nums) <= 10^4"
    starter_code:
      python: |
        def solve(nums, target):
            pass

  - id: 2
    title: Valid Parentheses
    difficulty: medium
    description: |
      Determine whether the input string has valid brackets.
    examples:
      - input: 's = "()[]{}"'
        output: "true"
        explanation: null
    constraints:
      - "1 <= len(s) <= 10^4"
    starter_code:
      python: |
        def solve(s):
            pass
"""


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "questions.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def _question_payload(question: Question) -> dict:
    return {
        "id": question.id,
        "title": question.title,
        "difficulty": question.difficulty,
        "description": question.description,
        "examples": question.examples,
        "constraints": question.constraints,
        "starter_code": question.starter_code,
    }


async def _open_fresh_session_factory(
    db_path: Path,
) -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_engine(file_database_url(db_path))
    return create_session_factory(engine), engine


# migration → seed 後，新 session 的 list_all 應與 YAML 一致。
@pytest.mark.anyio
async def test_migration_seed_new_session_list_all_matches_yaml(tmp_path: Path):
    db_path = tmp_path / "phase3.db"
    yaml_path = _write_yaml(tmp_path, SAMPLE_YAML)
    expected = sorted(load_questions_from_yaml(yaml_path), key=lambda q: q["id"])

    engine = create_engine(file_database_url(db_path))
    await init_db(engine)
    session_factory = create_session_factory(engine)
    await seed_questions(session_factory, yaml_path)
    await engine.dispose()

    fresh_factory, fresh_engine = await _open_fresh_session_factory(db_path)
    try:
        async with fresh_factory() as session:
            repo = QuestionRepository(session)
            questions = await repo.list_all()
    finally:
        await fresh_engine.dispose()

    assert [_question_payload(question) for question in questions] == expected


# migration → seed 後，新 session 的 get_random 應能從題庫抽題。
@pytest.mark.anyio
async def test_migration_seed_new_session_get_random_from_bank(tmp_path: Path):
    db_path = tmp_path / "phase3_random.db"
    yaml_path = _write_yaml(tmp_path, SAMPLE_YAML)
    yaml_ids = {question["id"] for question in load_questions_from_yaml(yaml_path)}

    engine = create_engine(file_database_url(db_path))
    await init_db(engine)
    session_factory = create_session_factory(engine)
    await seed_questions(session_factory, yaml_path)
    await engine.dispose()

    fresh_factory, fresh_engine = await _open_fresh_session_factory(db_path)
    try:
        async with fresh_factory() as session:
            repo = QuestionRepository(session)
            question = await repo.get_random()
    finally:
        await fresh_engine.dispose()

    assert question is not None
    assert question.id in yaml_ids


# 模擬重啟：再次 seed 後，新 session 題庫仍與 YAML 一致。
@pytest.mark.anyio
async def test_restart_resyncs_bank_and_new_session_matches_yaml(tmp_path: Path):
    db_path = tmp_path / "phase3_restart.db"
    yaml_path = _write_yaml(tmp_path, SAMPLE_YAML)
    expected = sorted(load_questions_from_yaml(yaml_path), key=lambda q: q["id"])

    for _ in range(2):
        engine = create_engine(file_database_url(db_path))
        await init_db(engine)
        session_factory = create_session_factory(engine)
        await seed_questions(session_factory, yaml_path)
        await engine.dispose()

    fresh_factory, fresh_engine = await _open_fresh_session_factory(db_path)
    try:
        async with fresh_factory() as session:
            repo = QuestionRepository(session)
            questions = await repo.list_all()
            random_question = await repo.get_random()
    finally:
        await fresh_engine.dispose()

    assert [_question_payload(question) for question in questions] == expected
    assert random_question is not None
    assert random_question.id in {question["id"] for question in expected}
