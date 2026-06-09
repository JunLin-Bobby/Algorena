"""Question persistence queries."""

import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Question


class QuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, question_id: int) -> Question | None:
        return await self._session.get(Question, question_id)

    async def list_all(self) -> list[Question]:
        result = await self._session.execute(select(Question).order_by(Question.id))
        return list(result.scalars().all())

    async def get_random(self) -> Question | None:
        questions = await self.list_all()
        if not questions:
            return None
        return random.choice(questions)
