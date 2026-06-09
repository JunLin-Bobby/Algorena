from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db import create_engine, create_session_factory, get_session, init_db
from db.migrate import file_database_url
from db.models import Question
from db.repositories.question_repository import QuestionRepository

QUESTION_ONE = {
    "id": 1,
    "title": "Two Sum",
    "difficulty": "easy",
    "description": "Return indices of two numbers that add up to target.",
    "examples": [
        {
            "input": "nums = [2,7,11,15], target = 9",
            "output": "[0,1]",
            "explanation": "Because nums[0] + nums[1] == 9.",
        }
    ],
    "constraints": ["2 <= len(nums) <= 10^4"],
    "starter_code": {"python": "def solve(nums, target):\n    pass"},
}

QUESTION_TWO = {
    "id": 2,
    "title": "Valid Parentheses",
    "difficulty": "medium",
    "description": "Determine whether the input string has valid brackets.",
    "examples": [{"input": 's = "()[]{}"', "output": "true", "explanation": None}],
    "constraints": ["1 <= len(s) <= 10^4"],
    "starter_code": {"python": "def solve(s):\n    pass"},
}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def migrated_session_factory(
    tmp_path: Path,
) -> async_sessionmaker[AsyncSession]:
    engine = create_engine(file_database_url(tmp_path / "repo.db"))
    session_factory = create_session_factory(engine)
    await init_db(engine)
    yield session_factory
    await engine.dispose()


async def _seed_questions(
    session_factory: async_sessionmaker[AsyncSession],
    *questions: dict,
) -> None:
    async with get_session(session_factory) as session:
        for question in questions:
            session.add(Question(**question))
        await session.commit()


# get_by_id 應回傳對應的 Question。
@pytest.mark.anyio
async def test_get_by_id_returns_question_when_present(
    migrated_session_factory: async_sessionmaker[AsyncSession],
):
    await _seed_questions(migrated_session_factory, QUESTION_ONE)

    async with get_session(migrated_session_factory) as session:
        repo = QuestionRepository(session)
        question = await repo.get_by_id(1)

    assert question is not None
    assert question.id == QUESTION_ONE["id"]
    assert question.title == QUESTION_ONE["title"]


# get_by_id 在 id 不存在時應回傳 None。
@pytest.mark.anyio
async def test_get_by_id_returns_none_when_missing(
    migrated_session_factory: async_sessionmaker[AsyncSession],
):
    await _seed_questions(migrated_session_factory, QUESTION_ONE)

    async with get_session(migrated_session_factory) as session:
        repo = QuestionRepository(session)
        question = await repo.get_by_id(999)

    assert question is None


# list_all 應回傳全部題目（依 id 排序）。
@pytest.mark.anyio
async def test_list_all_returns_all_questions_sorted_by_id(
    migrated_session_factory: async_sessionmaker[AsyncSession],
):
    await _seed_questions(migrated_session_factory, QUESTION_TWO, QUESTION_ONE)

    async with get_session(migrated_session_factory) as session:
        repo = QuestionRepository(session)
        questions = await repo.list_all()

    assert [question.id for question in questions] == [1, 2]


# get_random 應從題庫中回傳一筆題目。
@pytest.mark.anyio
async def test_get_random_returns_one_question_from_bank(
    migrated_session_factory: async_sessionmaker[AsyncSession],
):
    await _seed_questions(migrated_session_factory, QUESTION_ONE, QUESTION_TWO)

    async with get_session(migrated_session_factory) as session:
        repo = QuestionRepository(session)
        question = await repo.get_random()

    assert question is not None
    assert question.id in {QUESTION_ONE["id"], QUESTION_TWO["id"]}


# get_random 在題庫為空時應回傳 None。
@pytest.mark.anyio
async def test_get_random_returns_none_when_bank_empty(
    migrated_session_factory: async_sessionmaker[AsyncSession],
):
    async with get_session(migrated_session_factory) as session:
        repo = QuestionRepository(session)
        question = await repo.get_random()

    assert question is None
