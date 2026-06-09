"""Mock question adapter for local development and tests."""

import random

from core.ports import IQuestionService, QuestionPayload


DEFAULT_QUESTIONS: list[QuestionPayload] = [
    {
        "id": 1,
        "title": "Two Sum",
        "difficulty": "easy",
        "description": "Return indices of two numbers that add up to target.",
        "examples": [
            {
                "input": "nums = [2,7,11,15], target = 9",
                "output": "[0,1]",
                "explanation": "Because nums[0] + nums[1] = 9.",
            }
        ],
        "constraints": ["2 <= len(nums) <= 10^4", "-10^9 <= nums[i] <= 10^9"],
        "starter_code": {
            "python": "def solve(nums, target):\n    pass",
            "js": "function solve(nums, target) {\n  return [];\n}",
        },
    },
    {
        "id": 2,
        "title": "Valid Parentheses",
        "difficulty": "easy",
        "description": "Determine whether the input string has valid brackets.",
        "examples": [
            {
                "input": 's = "()[]{}"',
                "output": "true",
                "explanation": None,
            }
        ],
        "constraints": ["1 <= len(s) <= 10^4", "s consists only of ()[]{}"],
        "starter_code": {
            "python": "def solve(s):\n    pass",
            "js": "function solve(s) {\n  return true;\n}",
        },
    },
    {
        "id": 3,
        "title": "Longest Common Prefix",
        "difficulty": "medium",
        "description": "Find the longest common prefix among a list of strings.",
        "examples": [
            {
                "input": 'strs = ["flower","flow","flight"]',
                "output": '"fl"',
                "explanation": "fl is the common prefix for all strings.",
            }
        ],
        "constraints": ["1 <= len(strs) <= 200", "0 <= len(strs[i]) <= 200"],
        "starter_code": {
            "python": "def solve(strs):\n    pass",
            "js": "function solve(strs) {\n  return '';\n}",
        },
    },
]


class MockQuestionService(IQuestionService):
    def __init__(
        self,
        questions: list[QuestionPayload] | None = None,
        seed: int | None = None,
    ) -> None:
        bank = questions if questions is not None else DEFAULT_QUESTIONS
        if not bank:
            raise ValueError("questions must not be empty")
        self._questions = [dict(q) for q in bank]
        self._rng = random.Random(seed)

    async def get_random_question(self) -> QuestionPayload:
        question = self._rng.choice(self._questions)
        return dict(question)
