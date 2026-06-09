import pytest
from pathlib import Path
from sqlalchemy import select

from db import create_engine, create_session_factory, get_session, init_db
from db.migrate import file_database_url
from db.models import Question
SAMPLE_QUESTION = {
    "id": 1,
    "title": "Two Sum",
    "difficulty": "easy",
    "description": "Return indices of two numbers that add up to target.",
    "examples": [
        {
            "input": "nums = [2,7,11,15], target = 9",
            "output": "[0,1]",
            "explanation": "Because nums[0] + nums[1] = 9.",
        }
    ],
    "constraints": ["2 <= len(nums) <= 10^4", "-10^9 <= nums[i] <= 10^9"],
    "starter_code": {
        "python": "def solve(nums, target):\n    pass",
        "js": "function solve(nums, target) {\n  return [];\n}",
    },
}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# init_db 後應能 insert / select 一筆 Question。
@pytest.mark.anyio
async def test_init_db_creates_questions_table_and_persists_row(tmp_path: Path):
    engine = create_engine(file_database_url(tmp_path / "questions.db"))
    session_factory = create_session_factory(engine)
    try:
        await init_db(engine)
        async with get_session(session_factory) as session:
            session.add(Question(**SAMPLE_QUESTION))
            await session.commit()

        async with get_session(session_factory) as session:
            result = await session.execute(
                select(Question).where(Question.id == 1)
            )
            question = result.scalar_one()

            assert question.title == SAMPLE_QUESTION["title"]
            assert question.difficulty == SAMPLE_QUESTION["difficulty"]
            assert question.description == SAMPLE_QUESTION["description"]
            assert question.examples == SAMPLE_QUESTION["examples"]
            assert question.constraints == SAMPLE_QUESTION["constraints"]
            assert question.starter_code == SAMPLE_QUESTION["starter_code"]
    finally:
        await engine.dispose()


# Question 應對齊 data contract 的表名與欄位。
def test_question_maps_to_questions_table_with_contract_columns():
    assert Question.__tablename__ == "questions"
    column_names = {column.name for column in Question.__table__.columns}
    assert column_names == {
        "id",
        "title",
        "difficulty",
        "description",
        "examples",
        "constraints",
        "starter_code",
    }
