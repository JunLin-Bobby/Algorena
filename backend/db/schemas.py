"""Pydantic schemas for DB/API boundaries (ORM separate from wire formats)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ExampleCaseRead(BaseModel):
    input: str
    output: str
    explanation: str | None = None


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    difficulty: Literal["easy", "medium", "hard"]
    description: str
    examples: list[ExampleCaseRead]
    constraints: list[str]
    starter_code: dict[str, str]
