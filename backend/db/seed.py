"""Load and sync question bank from YAML into SQLite."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.ports import QuestionPayload
from db.models import Question
from db.session import get_session

logger = logging.getLogger(__name__)

DEFAULT_QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "questions.yaml"


class ExampleCaseSeed(BaseModel):
    input: str
    output: str
    explanation: str | None = None


class QuestionSeed(BaseModel):
    id: int = Field(gt=0)
    title: str
    difficulty: Literal["easy", "medium", "hard"]
    description: str
    examples: list[ExampleCaseSeed]
    constraints: list[str]
    starter_code: dict[str, str]


class QuestionsFile(BaseModel):
    questions: list[QuestionSeed]


def load_questions_from_yaml(path: Path) -> list[QuestionPayload]:
    """Parse YAML, validate, and return QuestionPayload-compatible dicts."""
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    file_model = QuestionsFile.model_validate(data)
    seen_ids: set[int] = set()
    duplicate_ids: list[int] = []

    for question in file_model.questions:
        if question.id in seen_ids:
            duplicate_ids.append(question.id)
        seen_ids.add(question.id)

    if duplicate_ids:
        dupes = ", ".join(str(question_id) for question_id in sorted(set(duplicate_ids)))
        raise ValueError(f"duplicate question ids in {path}: {dupes}")

    return [question.model_dump() for question in file_model.questions]


def _apply_question_fields(existing: Question, payload: QuestionPayload) -> None:
    existing.title = payload["title"]
    existing.difficulty = payload["difficulty"]
    existing.description = payload["description"]
    existing.examples = payload["examples"]
    existing.constraints = payload["constraints"]
    existing.starter_code = payload["starter_code"]


async def seed_questions(
    session_factory: async_sessionmaker[AsyncSession],
    yaml_path: Path | None = None,
) -> None:
    """Upsert YAML questions by id, then prune rows absent from the file."""
    path = yaml_path or DEFAULT_QUESTIONS_PATH
    questions = load_questions_from_yaml(path)
    yaml_ids = {question["id"] for question in questions}

    async with get_session(session_factory) as session:
        async with session.begin():
            for payload in questions:
                existing = await session.get(Question, payload["id"])
                if existing is None:
                    session.add(Question(**payload))
                else:
                    _apply_question_fields(existing, payload)

            if yaml_ids:
                await session.execute(
                    delete(Question).where(Question.id.not_in(yaml_ids))
                )
            else:
                logger.warning(
                    "%s has no questions; skipping prune to avoid wiping the bank",
                    path,
                )
