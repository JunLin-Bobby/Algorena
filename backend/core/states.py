"""Room state machine — each phase defines allowed WebSocket events."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from core.events import JOIN, START, SUBMIT, VIOLATION, InboundEvent

if TYPE_CHECKING:
    from core.room import Room


class RoomState(ABC):
    """State interface for room phase-specific event handling."""

    @property
    def name(self) -> str:
        return type(self).__name__

    @abstractmethod
    async def handle(self, room: "Room", event: InboundEvent | str, **kwargs) -> None:
        """Handle one inbound event under current phase rules."""
        pass

    async def _error(self, room: "Room", code: str, message: str) -> None:
        """統一錯誤格式：{ type, code, message }"""
        await room._notify({
            "type": "error",
            "code": code,
            "message": message,
        })

    async def _reject(self, room: "Room", event: str) -> None:
        """收到不允許的事件時，通知客戶端"""
        await self._error(
            room,
            "INVALID_EVENT",
            f"{event} 在 {self.name} 階段不允許",
        )


class LobbyState(RoomState):
    """Waiting room. Accepts only `join`."""

    async def handle(self, room: "Room", event: InboundEvent | str, **kwargs) -> None:
        if event != JOIN:
            await self._reject(room, event)
            return

        player = kwargs.get("player")
        if not player:
            await self._error(room, "MISSING_PARAM", "缺少 player 參數")
            return

        await room.add_player(player)


class ReadyState(RoomState):
    """Both players joined. Accepts only host `start`."""

    async def handle(self, room: "Room", event: InboundEvent | str, **kwargs) -> None:
        if event != START:
            await self._reject(room, event)
            return

        player = kwargs.get("player")
        if not player or not room.players:
            await self._error(room, "MISSING_PARAM", "缺少 player 參數")
            return

        if player != room.players[0]:
            await self._error(room, "NOT_HOST", "只有房主可以開始遊戲")
            return

        await room.start_game()


class PlayingState(RoomState):
    """Active match. Accepts `submit` and `violation`."""

    async def handle(self, room: "Room", event: InboundEvent | str, **kwargs) -> None:
        if event == SUBMIT:
            player = kwargs.get("player")
            code = kwargs.get("code")
            if not player or code is None:
                await self._error(room, "MISSING_PARAM", "缺少 player 或 code 參數")
                return
            await room.submit_code(player, code)

        elif event == VIOLATION:
            player = kwargs.get("player")
            if not player:
                # violation 由前端 Page Visibility API 自動觸發，正常情況必有 player；缺則略過
                return
            await room.record_violation(player)

        else:
            await self._reject(room, event)


class JudgingState(RoomState):
    """AI 評審中，拒絕所有事件"""

    async def handle(self, room: "Room", event: InboundEvent | str, **kwargs) -> None:
        await self._reject(room, event)


class ResultState(RoomState):
    """遊戲結束，拒絕所有事件"""

    async def handle(self, room: "Room", event: InboundEvent | str, **kwargs) -> None:
        await self._reject(room, event)
