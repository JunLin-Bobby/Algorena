"""Composition root — wire adapters from settings without touching core."""

from dataclasses import dataclass

from adapters.llm_judge import LLMJudgeService
from adapters.mock_judge import MockJudgeService
from adapters.mock_question import MockQuestionService
from adapters.websocket_notify import WebSocketNotifyService
from config import Settings
from core.ports import IJudgeService, INotifyService, IQuestionService
from core.room import Room
from manager import ConnectionManager


@dataclass
class AppDependencies:
    settings: Settings
    connection_manager: ConnectionManager
    judge_service: IJudgeService
    question_service: IQuestionService
    notify_service: INotifyService


def build_judge_service(settings: Settings) -> IJudgeService:
    if settings.judge_mode == "mock":
        return MockJudgeService()

    if not settings.llm_api_key:
        raise ValueError("JUDGE_MODE=llm requires LLM_API_KEY")

    return LLMJudgeService(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout_seconds=settings.llm_timeout_seconds,
        max_tokens=settings.llm_max_tokens,
    )


def build_app_dependencies(settings: Settings) -> AppDependencies:
    connection_manager = ConnectionManager()
    return AppDependencies(
        settings=settings,
        connection_manager=connection_manager,
        judge_service=build_judge_service(settings),
        question_service=MockQuestionService(),
        notify_service=WebSocketNotifyService(connection_manager),
    )


def build_room(room_code: str, deps: AppDependencies) -> Room:
    return Room(
        room_code=room_code,
        judge_service=deps.judge_service,
        notify_service=deps.notify_service,
        question_service=deps.question_service,
        max_players=deps.settings.max_players,
        game_duration_seconds=deps.settings.game_duration_seconds,
        violation_penalty=deps.settings.violation_penalty,
    )
