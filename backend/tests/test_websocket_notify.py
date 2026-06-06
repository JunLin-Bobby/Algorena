import pytest

from adapters.websocket_notify import WebSocketNotifyService
from manager import ConnectionManager
from tests.fakes import FakeWebSocket


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# broadcast 應把 event 送給同一 room_code 的所有連線，且不影響其他房間。
@pytest.mark.anyio
async def test_connection_manager_broadcasts_to_all_room_connections():
    manager = ConnectionManager()
    room_code = "ABCD"
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()
    other_ws = FakeWebSocket()

    await manager.connect(room_code, ws1)
    await manager.connect(room_code, ws2)
    await manager.connect("WXYZ", other_ws)

    event = {"type": "player:joined", "player": "alice"}
    await manager.broadcast(room_code, event)

    assert ws1.sent == [event]
    assert ws2.sent == [event]
    assert other_ws.sent == []


# 對沒有任何連線的 room_code 廣播時，應安靜略過、不拋錯。
@pytest.mark.anyio
async def test_connection_manager_broadcast_is_noop_for_unknown_room():
    manager = ConnectionManager()

    await manager.broadcast("NONE", {"type": "state:changed", "state": "LobbyState"})


# disconnect 後該連線不應再收到 broadcast（模擬玩家斷線）。
@pytest.mark.anyio
async def test_connection_manager_disconnect_removes_connection():
    manager = ConnectionManager()
    room_code = "ABCD"
    ws = FakeWebSocket()

    await manager.connect(room_code, ws)
    manager.disconnect(room_code, ws)

    await manager.broadcast(room_code, {"type": "game:started"})

    assert ws.sent == []


# WebSocketNotifyService.notify_room 應委派給 ConnectionManager.broadcast，
# 確保 Room 注入的 INotifyService 能真正把 event 推到 WebSocket。
@pytest.mark.anyio
async def test_websocket_notify_delegates_to_connection_manager():
    manager = ConnectionManager()
    notify = WebSocketNotifyService(manager)
    room_code = "ROOM1"
    ws = FakeWebSocket()
    await manager.connect(room_code, ws)

    event = {"type": "submission:received", "player": "bob"}
    await notify.notify_room(room_code, event)

    assert ws.sent == [event]
