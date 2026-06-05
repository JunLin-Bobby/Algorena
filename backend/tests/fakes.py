"""In-memory test doubles for core ports."""


class RecordingNotify:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def notify_room(self, room_code: str, event: dict) -> None:
        self.events.append(event)


class StubJudge:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def judge(self, question: str, code: str) -> dict:
        self.calls.append((question, code))
        return {"score": 0, "feedback": ""}


class StubQuestion:
    async def get_random_question(self) -> dict:
        return {"id": 1, "title": "test", "description": "", "starter_code": ""}
