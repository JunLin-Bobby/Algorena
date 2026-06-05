"""Core room aggregate for state-driven game flow."""

import asyncio

from core.ports import IJudgeService, INotifyService, IQuestionService
from core.states import JudgingState, LobbyState, PlayingState, ReadyState, ResultState


class Room:
    """Game room aggregate.

    Room owns player membership, current phase, and outbound notifications.
    It does not read environment variables directly; runtime settings are
    injected by the composition root (later in `main.py`).
    """

    # ─────────────────────────────
    # 初始化
    # ─────────────────────────────
    def __init__(
        self,
        room_code: str,
        judge_service: IJudgeService,
        notify_service: INotifyService,
        question_service: IQuestionService,
        *,
        # 以下為遊戲規則；正式環境由 main.py 從 config.py / .env 讀取後傳入（見 get_settings）
        max_players: int = 2,  # 對應 MAX_PLAYERS；預設 2 僅供 pytest 不載入 .env 時使用
        game_duration_seconds: int = 300,  # 對應 GAME_DURATION_SECONDS；Step 2 計時用
        violation_penalty: int = 5,  # 對應 VIOLATION_PENALTY；評分時違規扣分
    ):
        self.room_code = room_code
        self.judge_service = judge_service
        self.notify_service = notify_service
        self.question_service = question_service
        self.max_players = max_players
        self.game_duration_seconds = game_duration_seconds
        self.violation_penalty = violation_penalty

        self.state = LobbyState()
        self.players: list[str] = []
        self.question: dict | None = None
        self.submissions: dict[str, str] = {}
        self.violations: dict[str, int] = {}
        self.timer_task = None

    # ─────────────────────────────
    # 事件入口（WebSocket 訊息進來都走這裡）
    # ─────────────────────────────
    async def handle(self, event: str, **kwargs):
        """Single event entrypoint for websocket messages.

        Delegates event validation/execution to the active room state.
        """
        await self.state.handle(self, event, **kwargs)

    # ─────────────────────────────
    # 狀態切換
    # ─────────────────────────────
    async def transition_to(self, new_state):
        """Switch phase and broadcast unified `state:changed` event."""
        self.state = new_state
        await self._notify({
            "type": "state:changed",
            "state": type(new_state).__name__,
        })

    # ─────────────────────────────
    # 公開方法
    # ─────────────────────────────
    async def add_player(self, player: str):
        """Add player to room and transition to ready when full.

        Emits:
        - `error` with `DUPLICATE_PLAYER` / `ROOM_FULL` when rejected
        - `player:joined` when accepted
        - `state:changed` to `ReadyState` when room reaches max_players
        """
        if player in self.players:
            await self._notify({
                "type": "error",
                "code": "DUPLICATE_PLAYER",
                "message": f"{player} 已在房間內",
            })
            return

        if len(self.players) >= self.max_players:
            await self._notify({
                "type": "error",
                "code": "ROOM_FULL",
                "message": "房間已滿",
            })
            return

        self.players.append(player)
        self.violations[player] = 0
        await self._notify({
            "type": "player:joined",
            "player": player,
            "players": list(self.players),
        })

        if len(self.players) >= self.max_players:
            await self.transition_to(ReadyState())

    async def start_game(self):
        self.submissions = {}
        # question contract (暫定): {"id": int, "title": str, "description": str, "starter_code": str}
        self.question = await self.question_service.get_random_question()
        self._validate_question_contract(self.question)
        
        await self.transition_to(PlayingState())
        await self._notify({
            "type": "game:started",
            "question": self.question,
            "duration_seconds": self.game_duration_seconds,
        })
        await self._start_timer(self.game_duration_seconds)

    async def end_game(self):
        if isinstance(self.state, (JudgingState, ResultState)):
            # 防重入：submit 與 timer 可能同時觸發 end_game，避免重複評分/重複送結果
            return

        current_task = asyncio.current_task()
        # 若 end_game 是由「玩家提早交卷」觸發，就要取消仍在跑的計時器，避免 timer 再次觸發 end_game。
        # 若當前就是 timer task 自己觸發 end_game，則不能 cancel 自己（`is not current_task`）。
        if self.timer_task and not self.timer_task.done() and self.timer_task is not current_task:
            self.timer_task.cancel()

        await self.transition_to(JudgingState())
        results = await self._judge_all_submissions()
        await self.transition_to(ResultState())
        await self._notify({
            "type": "game:result",
            "results": results,
        })

    async def submit_code(self, player: str, code: str):
        self.submissions[player] = code
        await self._notify({
            "type": "submission:received",
            "player": player,
        })
        if len(self.submissions) >= len(self.players) and self.players:
            await self.end_game()

    async def record_violation(self, player: str):
        self.violations[player] = self.violations.get(player, 0) + 1
        await self._notify({
            "type": "violation:recorded",
            "player": player,
            "count": self.violations[player],
        })

    # ─────────────────────────────
    # 私有方法
    # ─────────────────────────────
    async def _notify(self, event: dict):
        """Broadcast one protocol event to all connections in this room."""
        await self.notify_service.notify_room(self.room_code, event)

    def _has_submissions(self) -> bool:
        return len(self.submissions) > 0

    async def _judge_all_submissions(self) -> dict:
        if not isinstance(self.question, dict):
            raise ValueError("question must be initialized before judging")
        question_text = self.question["description"]
        results: dict[str, dict] = {}
        for player in self.players:
            code = self.submissions.get(player, "")
            raw = await self.judge_service.judge(question_text, code)
            score = int(raw.get("score", 0))
            penalty = self.violations.get(player, 0) * self.violation_penalty
            final_score = max(score - penalty, 0)
            results[player] = {
                "score": score,
                "penalty": penalty,
                "final_score": final_score,
                "feedback": raw.get("feedback", ""),
            }
        return results

    async def _start_timer(self, duration: int):
        # 重啟計時前先取消舊 task，避免同時存在多個 timer 導致重複結算。
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        async def _timer():
            await asyncio.sleep(duration)
            await self.end_game()

        self.timer_task = asyncio.create_task(_timer())

    def _validate_question_contract(self, question: dict) -> None:
        if not isinstance(question, dict):
            raise ValueError("question must be a dict")
        required_keys = {"id", "title", "description", "starter_code"}
        missing = required_keys - question.keys()
        if missing:
            raise ValueError(f"question missing required keys: {sorted(missing)}")
