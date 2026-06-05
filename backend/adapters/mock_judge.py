"""Mock judge adapter for local development and tests."""

from core.ports import IJudgeService, JudgeResult


class MockJudgeService(IJudgeService):
    def __init__(
        self,
        *,
        score: float = 8.0,
        feedback: str = "Mock judge: code evaluated successfully.",
    ) -> None:
        self._score = score
        self._feedback = feedback

    async def judge(self, question: str, code: str) -> JudgeResult:
        return {
            "score": self._score,
            "feedback": self._feedback,
        }
