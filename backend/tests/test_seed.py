from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db import create_engine, create_session_factory, init_db
from db.migrate import file_database_url
from db.repositories.question_repository import QuestionRepository
from db.seed import DEFAULT_QUESTIONS_PATH, load_questions_from_yaml, seed_questions

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


@pytest.fixture
async def migrated_session_factory(
    tmp_path: Path,
) -> async_sessionmaker[AsyncSession]:
    engine = create_engine(file_database_url(tmp_path / "seed.db"))
    session_factory = create_session_factory(engine)
    await init_db(engine)
    yield session_factory
    await engine.dispose()


def _write_yaml(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


# load_questions_from_yaml 應能解析並驗證 YAML。
def test_load_questions_from_yaml_parses_valid_file(tmp_path: Path):
    yaml_path = _write_yaml(tmp_path, "questions.yaml", SAMPLE_YAML)

    questions = load_questions_from_yaml(yaml_path)

    assert len(questions) == 2
    assert questions[0]["id"] == 1
    assert questions[0]["difficulty"] == "easy"
    assert questions[1]["title"] == "Valid Parentheses"


# 專案預設 questions.yaml 應可載入。
def test_load_default_questions_yaml():
    questions = load_questions_from_yaml(DEFAULT_QUESTIONS_PATH)

    assert len(questions) >= 3
    assert all(question["id"] > 0 for question in questions)


# 重複 id 應在載入時 fail fast。
def test_load_questions_from_yaml_rejects_duplicate_ids(tmp_path: Path):
    yaml_path = _write_yaml(
        tmp_path,
        "dup.yaml",
        SAMPLE_YAML
        + """
  - id: 1
    title: Duplicate
    difficulty: easy
    description: dup
    examples:
      - input: x
        output: y
    constraints:
      - n >= 1
    starter_code:
      python: pass
""",
    )

    with pytest.raises(ValueError, match="duplicate question ids"):
        load_questions_from_yaml(yaml_path)


# seed 應將 YAML 題目 INSERT 進空 DB。
@pytest.mark.anyio
async def test_seed_inserts_new_questions(
    migrated_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
):
    yaml_path = _write_yaml(tmp_path, "seed.yaml", SAMPLE_YAML)

    await seed_questions(migrated_session_factory, yaml_path)

    async with migrated_session_factory() as session:
        repo = QuestionRepository(session)
        questions = await repo.list_all()

    assert len(questions) == 2
    assert {question.id for question in questions} == {1, 2}


# seed 應依 id UPDATE 既有題目。
@pytest.mark.anyio
async def test_seed_updates_existing_by_id(
    migrated_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
):
    yaml_path = _write_yaml(tmp_path, "seed.yaml", SAMPLE_YAML)
    await seed_questions(migrated_session_factory, yaml_path)

    updated_yaml = SAMPLE_YAML.replace("Two Sum", "Two Sum (Updated)")
    updated_path = _write_yaml(tmp_path, "updated.yaml", updated_yaml)
    await seed_questions(migrated_session_factory, updated_path)

    async with migrated_session_factory() as session:
        repo = QuestionRepository(session)
        question = await repo.get_by_id(1)
        count = len(await repo.list_all())

    assert question is not None
    assert question.title == "Two Sum (Updated)"
    assert count == 2


# seed 應 prune YAML 未列出的 id。
@pytest.mark.anyio
async def test_seed_prunes_removed_ids(
    migrated_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
):
    yaml_path = _write_yaml(tmp_path, "seed.yaml", SAMPLE_YAML)
    await seed_questions(migrated_session_factory, yaml_path)

    single_question_yaml = SAMPLE_YAML.split("  - id: 2")[0]
    pruned_path = _write_yaml(tmp_path, "pruned.yaml", single_question_yaml)
    await seed_questions(migrated_session_factory, pruned_path)

    async with migrated_session_factory() as session:
        repo = QuestionRepository(session)
        questions = await repo.list_all()

    assert len(questions) == 1
    assert questions[0].id == 1


# 相同 YAML 跑兩次應冪等。
@pytest.mark.anyio
async def test_seed_idempotent(
    migrated_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
):
    yaml_path = _write_yaml(tmp_path, "seed.yaml", SAMPLE_YAML)

    await seed_questions(migrated_session_factory, yaml_path)
    await seed_questions(migrated_session_factory, yaml_path)

    async with migrated_session_factory() as session:
        repo = QuestionRepository(session)
        first_run = await repo.list_all()

    assert len(first_run) == 2
    assert first_run[0].title == "Two Sum"


# 空 YAML 不應 prune 既有題目。
@pytest.mark.anyio
async def test_seed_empty_yaml_skips_prune(
    migrated_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
):
    yaml_path = _write_yaml(tmp_path, "seed.yaml", SAMPLE_YAML)
    await seed_questions(migrated_session_factory, yaml_path)

    empty_path = _write_yaml(tmp_path, "empty.yaml", "questions: []\n")
    await seed_questions(migrated_session_factory, empty_path)

    async with migrated_session_factory() as session:
        repo = QuestionRepository(session)
        questions = await repo.list_all()

    assert len(questions) == 2
