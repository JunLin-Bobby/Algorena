"""WebSocket connection registry and room-scoped broadcast."""

from collections import defaultdict
from typing import Any, Protocol


class WebSocketLike(Protocol):
    async def send_json(self, data: Any) -> None: ...


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocketLike]] = defaultdict(set)

    async def connect(self, room_code: str, websocket: WebSocketLike) -> None:
        self._rooms[room_code].add(websocket)

    def disconnect(self, room_code: str, websocket: WebSocketLike) -> None:
        connections = self._rooms.get(room_code)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            del self._rooms[room_code]

    async def broadcast(self, room_code: str, event: dict) -> None:
        for websocket in list(self._rooms.get(room_code, ())):
            await websocket.send_json(event)
