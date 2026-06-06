import pytest

from adapters.mock_question import MockQuestionService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# MockQuestionService 回傳的題目應符合 QuestionPayload 必要欄位。
@pytest.mark.anyio
async def test_get_random_question_returns_required_contract_keys():
    service = MockQuestionService()

    question = await service.get_random_question()

    assert set(question.keys()) == {
        "id",
        "title",
        "description",
        "examples",
        "constraints",
        "starter_code",
    }
    assert isinstance(question["examples"], list)
    assert isinstance(question["constraints"], list)
    assert isinstance(question["starter_code"], dict)


# MockQuestionService 應從注入的題庫中隨機選題。
@pytest.mark.anyio
async def test_get_random_question_comes_from_seed_bank():
    custom_bank = [
        {
            "id": 101,
            "title": "Two Sum",
            "description": "Return indices of two numbers that add up to target.",
            "examples": [
                {
                    "input": 'nums = [2,7,11,15], target = 9',
                    "output": "[0,1]",
                    "explanation": "nums[0] + nums[1] == 9",
                }
            ],
            "constraints": ["2 <= len(nums) <= 10^4"],
            "starter_code": {
                "python": "def solve(nums, target):\n    pass",
                "js": "function solve(nums, target) {\n  return [];\n}",
            },
        },
        {
            "id": 102,
            "title": "Valid Parentheses",
            "description": "Validate bracket sequence.",
            "examples": [
                {"input": 's = "()"', "output": "true", "explanation": None}
            ],
            "constraints": ["1 <= len(s) <= 10^4"],
            "starter_code": {
                "python": "def solve(s):\n    pass",
                "js": "function solve(s) {\n  return true;\n}",
            },
        },
    ]
    service = MockQuestionService(questions=custom_bank, seed=7)

    question = await service.get_random_question()

    assert question in custom_bank


# 空題庫應在初始化時拋錯。
def test_empty_question_bank_raises_error():
    with pytest.raises(ValueError, match="questions must not be empty"):
        MockQuestionService(questions=[])
