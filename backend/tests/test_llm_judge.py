import pytest

from adapters.llm_judge import LLMJudgeService


class FakeChatCompletionsAPI:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self._text = text
        self._error = error
        self.last_kwargs: dict | None = None

    async def create(self, **kwargs):
        if self._error is not None:
            raise self._error
        self.last_kwargs = kwargs
        message = type("FakeMessage", (), {"content": self._text})()
        choice = type("FakeChoice", (), {"message": message})()
        return type("FakeCompletionResponse", (), {"choices": [choice]})()


class FakeOpenAIClient:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        completions = FakeChatCompletionsAPI(text=text, error=error)
        self.chat = type(
            "FakeChatAPI",
            (),
            {"completions": completions},
        )()
        self.completions_api = completions


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# 有效 JSON 回應應正規化為 score 與 feedback，並使用 json_object 格式。
@pytest.mark.anyio
async def test_llm_judge_returns_normalized_result_from_valid_json():
    client = FakeOpenAIClient(text='{"score": 8.7, "feedback": "Looks good."}')
    service = LLMJudgeService(
        api_key="test-key",
        model="gpt-test",
        client=client,
    )

    result = await service.judge("question text", "print('hello')")

    assert result == {"score": 8.7, "feedback": "Looks good."}
    assert client.completions_api.last_kwargs is not None
    assert client.completions_api.last_kwargs["response_format"] == {"type": "json_object"}
    assert client.completions_api.last_kwargs["max_tokens"] == 1024


# 分數應被限制在 0–10 區間。
@pytest.mark.anyio
async def test_llm_judge_clamps_score_to_0_10():
    client = FakeOpenAIClient(text='{"score": 999, "feedback": "Too high."}')
    service = LLMJudgeService(
        api_key="test-key",
        model="gpt-test",
        client=client,
    )

    result = await service.judge("question text", "print('hello')")

    assert result["score"] == 10.0
    assert result["feedback"] == "Too high."


# 無法解析的回應應回傳 fallback 結果（score 0 + 錯誤說明）。
@pytest.mark.anyio
async def test_llm_judge_returns_fallback_on_malformed_json():
    client = FakeOpenAIClient(text="not-json")
    service = LLMJudgeService(
        api_key="test-key",
        model="gpt-test",
        client=client,
    )

    result = await service.judge("question text", "print('hello')")

    assert result["score"] == 0.0
    assert "failed to parse judge result" in result["feedback"]


# 應能解析 markdown code block 包住的 JSON。
@pytest.mark.anyio
async def test_llm_judge_parses_json_in_markdown_codeblock():
    client = FakeOpenAIClient(
        text='```json\n{"score": 8.5, "feedback": "Solid submission."}\n```'
    )
    service = LLMJudgeService(
        api_key="test-key",
        model="gpt-test",
        client=client,
    )

    result = await service.judge("question text", "print('hello')")

    assert result == {"score": 8.5, "feedback": "Solid submission."}


# API 呼叫失敗時應回傳 fallback 結果，不向外拋錯。
@pytest.mark.anyio
async def test_llm_judge_returns_fallback_on_client_error():
    client = FakeOpenAIClient(error=RuntimeError("network down"))
    service = LLMJudgeService(
        api_key="test-key",
        model="gpt-test",
        client=client,
    )

    result = await service.judge("question text", "print('hello')")

    assert result["score"] == 0.0
    assert "judge provider unavailable" in result["feedback"]
