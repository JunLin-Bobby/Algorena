"""WebSocket notify adapter for INotifyService."""

from core.ports import INotifyService, RoomEvent
from manager import ConnectionManager


class WebSocketNotifyService(INotifyService):
    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager

    async def notify_room(self, room_code: str, event: RoomEvent) -> None:
        await self._manager.broadcast(room_code, event)
