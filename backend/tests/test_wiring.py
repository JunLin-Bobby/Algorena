import pytest

from adapters.llm_judge import LLMJudgeService
from adapters.mock_judge import MockJudgeService
from adapters.mock_question import MockQuestionService
from adapters.websocket_notify import WebSocketNotifyService
from config import Settings
from wiring import build_app_dependencies, build_judge_service, build_room


def test_build_judge_service_uses_mock_when_mode_is_mock():
    settings = Settings(judge_mode="mock", llm_api_key=None)

    judge = build_judge_service(settings)

    assert isinstance(judge, MockJudgeService)


def test_build_judge_service_uses_llm_when_mode_is_llm_and_key_present():
    settings = Settings(
        judge_mode="llm",
        llm_api_key="test-key",
        llm_model="gpt-4o-mini",
    )

    judge = build_judge_service(settings)

    assert isinstance(judge, LLMJudgeService)


def test_build_judge_service_rejects_llm_mode_without_api_key():
    settings = Settings(judge_mode="llm", llm_api_key=None)

    with pytest.raises(ValueError, match="LLM_API_KEY"):
        build_judge_service(settings)


def test_build_app_dependencies_wires_notify_and_question_services():
    settings = Settings(judge_mode="mock")

    deps = build_app_dependencies(settings)

    assert isinstance(deps.judge_service, MockJudgeService)
    assert isinstance(deps.question_service, MockQuestionService)
    assert isinstance(deps.notify_service, WebSocketNotifyService)
    assert deps.connection_manager is not None


def test_build_room_injects_dependencies_from_settings():
    settings = Settings(
        judge_mode="mock",
        game_duration_seconds=120,
        max_players=2,
        violation_penalty=3,
    )
    deps = build_app_dependencies(settings)

    room = build_room("ROOM42", deps)

    assert room.room_code == "ROOM42"
    assert room.judge_service is deps.judge_service
    assert room.notify_service is deps.notify_service
    assert room.question_service is deps.question_service
    assert room.game_duration_seconds == 120
    assert room.violation_penalty == 3
