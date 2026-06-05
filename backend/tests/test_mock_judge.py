import pytest

from adapters.mock_judge import MockJudgeService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_mock_judge_returns_fixed_score_and_feedback():
    judge = MockJudgeService()

    result = await judge.judge("any question", "print('hello')")

    assert result == {
        "score": 8.0,
        "feedback": "Mock judge: code evaluated successfully.",
    }


@pytest.mark.anyio
async def test_mock_judge_supports_custom_fixed_result():
    judge = MockJudgeService(score=9.5, feedback="Great job from mock judge.")

    result = await judge.judge("another question", "return 42")

    assert result["score"] == 9.5
    assert result["feedback"] == "Great job from mock judge."
