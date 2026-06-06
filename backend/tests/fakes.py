"""In-memory test doubles for core ports."""


class FakeWebSocket:
    """測試用 WebSocket 替身；send_json 被呼叫時把 payload 記錄到 sent。"""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


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
        return {"score": 0.0}


class StubQuestion:
    async def get_random_question(self) -> dict:
        return {
            "id": 1,
            "title": "test",
            "description": "",
            "examples": [
                {"input": "x = 1", "output": "1", "explanation": None},
            ],
            "constraints": ["x >= 0"],
            "starter_code": {
                "python": "def solve():\n    pass",
                "js": "function solve() {\n  return 0;\n}",
            },
        }
