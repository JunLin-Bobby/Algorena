from abc import ABC, abstractmethod
from typing import Literal, TypedDict

Difficulty = Literal["easy", "medium", "hard"]


class ExampleCase(TypedDict):
    input: str
    output: str
    explanation: str | None


class QuestionPayload(TypedDict):
    id: int
    title: str
    difficulty: Difficulty
    description: str
    examples: list[ExampleCase]
    constraints: list[str]
    starter_code: dict[str, str]


class JudgeResult(TypedDict):
    score: float


class RoomEvent(TypedDict, total=False):
    type: str
    code: str
    message: str
    player: str
    players: list[str]
    state: str
    question: QuestionPayload
    duration_seconds: int
    results: dict[str, dict]
    count: int


class IJudgeService(ABC):
    @abstractmethod
    async def judge(self, question: str, code: str) -> JudgeResult:
        pass


class INotifyService(ABC):
    @abstractmethod
    async def notify_room(self, room_code: str, event: RoomEvent) -> None:
        pass


class IQuestionService(ABC):
    @abstractmethod
    async def get_random_question(self) -> QuestionPayload:
        pass