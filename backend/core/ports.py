# core/ports.py
from abc import ABC, abstractmethod

class IJudgeService(ABC):
    @abstractmethod
    async def judge(self, question: str, code: str) -> dict:
        pass

class INotifyService(ABC):
    @abstractmethod
    async def notify_room(self, room_code: str, event: dict) -> None:
        pass

class IQuestionService(ABC):
    @abstractmethod
    async def get_random_question(self) -> dict:
        pass