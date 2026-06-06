import pytest

from config import Settings
from core.states import PlayingState, ResultState
from wiring import build_app_dependencies, build_room
from tests.fakes import FakeWebSocket


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def wired_room():
    """Phase 2 stack: wiring + mock adapters + WebSocket notify."""
    settings = Settings(
        judge_mode="mock",
        game_duration_seconds=120,
        max_players=2,
        violation_penalty=5,
    )
    deps = build_app_dependencies(settings)
    room_code = "INT01"
    ws = FakeWebSocket()
    await deps.connection_manager.connect(room_code, ws)
    room = build_room(room_code, deps)
    return room, ws


def _events_of_type(sent: list[dict], event_type: str) -> list[dict]:
    return [event for event in sent if event.get("type") == event_type]


async def _start_two_player_game(room) -> None:
    await room.handle("join", player="alice")
    await room.handle("join", player="bob")
    await room.handle("start", player="alice")


# Phase 2 整合：game:started 應含完整 question contract 與 duration_seconds。
@pytest.mark.anyio
async def test_integration_emits_game_started_with_question_and_duration(wired_room):
    room, ws = wired_room

    await _start_two_player_game(room)

    assert isinstance(room.state, PlayingState)
    started_events = _events_of_type(ws.sent, "game:started")
    assert len(started_events) == 1

    event = started_events[0]
    assert event["duration_seconds"] == 120
    question = event["question"]
    for key in ("id", "title", "description", "examples", "constraints", "starter_code"):
        assert key in question


# Phase 2 整合：submit 後應透過 WebSocket 廣播 submission:received。
@pytest.mark.anyio
async def test_integration_emits_submission_received(wired_room):
    room, ws = wired_room
    await _start_two_player_game(room)

    await room.handle("submit", player="alice", code="print('hi')")

    received_events = _events_of_type(ws.sent, "submission:received")
    assert received_events == [{"type": "submission:received", "player": "alice"}]


# Phase 2 整合：雙方提交後應廣播 game:result 且含各玩家分數。
@pytest.mark.anyio
async def test_integration_emits_game_result_with_scores(wired_room):
    room, ws = wired_room
    await _start_two_player_game(room)

    await room.handle("submit", player="alice", code="print('a')")
    await room.handle("submit", player="bob", code="print('b')")

    assert isinstance(room.state, ResultState)
    result_events = _events_of_type(ws.sent, "game:result")
    assert len(result_events) == 1

    results = result_events[0]["results"]
    assert results["alice"] == {"score": 8.0, "penalty": 0, "final_score": 8.0}
    assert results["bob"] == {"score": 8.0, "penalty": 0, "final_score": 8.0}


# Phase 2 整合：非房主 start 應廣播 error（NOT_HOST）。
@pytest.mark.anyio
async def test_integration_emits_error_for_not_host(wired_room):
    room, ws = wired_room
    await room.handle("join", player="alice")
    await room.handle("join", player="bob")

    await room.handle("start", player="bob")

    error_events = _events_of_type(ws.sent, "error")
    assert any(
        event.get("code") == "NOT_HOST"
        for event in error_events
    )
