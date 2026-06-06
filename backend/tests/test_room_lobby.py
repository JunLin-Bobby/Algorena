import pytest

from core.room import Room
from core.states import LobbyState, PlayingState, ReadyState
from core.states import ResultState
from tests.fakes import RecordingNotify, StubJudge, StubQuestion


class BadQuestionService:
    async def get_random_question(self) -> dict:
        return {"id": 1, "title": "broken"}


@pytest.fixture
def anyio_backend() -> str:
    """Force pytest-anyio to use asyncio backend."""
    return "asyncio"


@pytest.fixture
def room_factory():
    def _make_room(
        max_players: int = 2,
        game_duration_seconds: int = 1,
        violation_penalty: int = 5,
    ) -> tuple[Room, RecordingNotify]:
        notify = RecordingNotify()
        room = Room(
            room_code="TEST",
            judge_service=StubJudge(),
            notify_service=notify,
            question_service=StubQuestion(),
            max_players=max_players,
            game_duration_seconds=game_duration_seconds,
            violation_penalty=violation_penalty,
        )
        return room, notify

    return _make_room


@pytest.fixture
def room_with_refs(room_factory):
    judge = StubJudge()
    notify = RecordingNotify()
    room = Room(
        room_code="TEST",
        judge_service=judge,
        notify_service=notify,
        question_service=StubQuestion(),
        max_players=2,
        game_duration_seconds=60,
        violation_penalty=5,
    )
    return room, judge, notify


# 新建 Room 應從 LobbyState 開始。
def test_room_starts_in_lobby_state(room_factory):
    room, _ = room_factory()
    assert isinstance(room.state, LobbyState)


# Room 應保存注入的遊戲規則設定。
def test_room_stores_injected_game_rules(room_factory):
    room, _ = room_factory(
        max_players=2,
        game_duration_seconds=60,
        violation_penalty=10,
    )
    assert room.max_players == 2
    assert room.game_duration_seconds == 60
    assert room.violation_penalty == 10


# 第一位玩家 join 應加入名單並廣播 player:joined。
@pytest.mark.anyio
async def test_first_join_adds_player_and_notifies(room_factory):
    room, notify = room_factory()
    await room.handle("join", player="alice")

    assert room.players == ["alice"]
    assert isinstance(room.state, LobbyState)
    assert room.violations["alice"] == 0
    assert any(e["type"] == "player:joined" for e in notify.events)


# 第二位玩家 join 後人數滿員應切換到 ReadyState。
@pytest.mark.anyio
async def test_second_join_transitions_to_ready(room_factory):
    room, notify = room_factory()
    await room.handle("join", player="alice")
    await room.handle("join", player="bob")

    assert room.players == ["alice", "bob"]
    assert isinstance(room.state, ReadyState)
    assert any(
        e["type"] == "state:changed" and e["state"] == "ReadyState"
        for e in notify.events
    )


# 重複 join 應回傳 DUPLICATE_PLAYER 錯誤。
@pytest.mark.anyio
async def test_duplicate_join_returns_error(room_factory):
    room, notify = room_factory()
    await room.handle("join", player="alice")
    await room.handle("join", player="alice")

    assert len(room.players) == 1
    assert any(
        e.get("code") == "DUPLICATE_PLAYER"
        for e in notify.events
        if e["type"] == "error"
    )


# 房間滿員後再加入應回傳 ROOM_FULL 錯誤。
@pytest.mark.anyio
async def test_room_full_returns_error(room_factory):
    room, notify = room_factory()
    await room.handle("join", player="alice")
    await room.handle("join", player="bob")
    await room.add_player("charlie")

    assert room.players == ["alice", "bob"]
    assert any(
        e.get("code") == "ROOM_FULL"
        for e in notify.events
        if e["type"] == "error"
    )


# 房主 start 應切換到 PlayingState 並廣播 game:started。
@pytest.mark.anyio
async def test_host_start_transitions_to_playing_and_emits_game_started(room_factory):
    room, notify = room_factory(game_duration_seconds=60)
    await room.handle("join", player="alice")
    await room.handle("join", player="bob")

    await room.handle("start", player="alice")

    assert isinstance(room.state, PlayingState)
    assert room.question is not None
    for key in ("id", "title", "description", "examples", "constraints", "starter_code"):
        assert key in room.question
    assert any(e["type"] == "game:started" for e in notify.events)


# 題目 contract 不完整時 start_game 應拋 ValueError 且維持 ReadyState。
@pytest.mark.anyio
async def test_start_game_rejects_invalid_question_contract():
    notify = RecordingNotify()
    room = Room(
        room_code="TEST",
        judge_service=StubJudge(),
        notify_service=notify,
        question_service=BadQuestionService(),
        max_players=2,
        game_duration_seconds=60,
        violation_penalty=5,
    )
    await room.handle("join", player="alice")
    await room.handle("join", player="bob")

    with pytest.raises(ValueError, match="question missing required keys"):
        await room.handle("start", player="alice")

    assert isinstance(room.state, ReadyState)


# submit 應把玩家程式碼存入 submissions。
@pytest.mark.anyio
async def test_submit_stores_player_code(room_factory):
    room, _ = room_factory(game_duration_seconds=60)
    await room.handle("join", player="alice")
    await room.handle("join", player="bob")
    await room.handle("start", player="alice")

    await room.handle("submit", player="alice", code="print('hi')")

    assert room.submissions["alice"] == "print('hi')"


# violation 應累加該玩家的違規次數。
@pytest.mark.anyio
async def test_violation_increments_player_count(room_factory):
    room, _ = room_factory(game_duration_seconds=60)
    await room.handle("join", player="alice")
    await room.handle("join", player="bob")
    await room.handle("start", player="alice")

    await room.handle("violation", player="alice")

    assert room.violations["alice"] == 1


# 雙方皆提交後應結算遊戲、呼叫 judge 並廣播 game:result。
@pytest.mark.anyio
async def test_both_submissions_finalize_game_and_emit_result(room_with_refs):
    room, judge, notify = room_with_refs
    await room.handle("join", player="alice")
    await room.handle("join", player="bob")
    await room.handle("start", player="alice")

    await room.handle("submit", player="alice", code="print('a')")
    await room.handle("submit", player="bob", code="print('b')")

    assert isinstance(room.state, ResultState)
    assert len(judge.calls) == 2
    assert any(e["type"] == "game:result" for e in notify.events)
