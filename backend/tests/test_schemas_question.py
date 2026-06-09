from db.models import Question

SAMPLE_QUESTION = {
    "id": 1,
    "title": "Two Sum",
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
}


# QuestionRead 應能從 ORM Question instance model_validate。
def test_question_read_model_validate_from_orm():
    from db.schemas import QuestionRead

    orm_question = Question(**SAMPLE_QUESTION)

    read = QuestionRead.model_validate(orm_question)

    assert read.id == SAMPLE_QUESTION["id"]
    assert read.title == SAMPLE_QUESTION["title"]
    assert read.description == SAMPLE_QUESTION["description"]
    assert read.examples[0].model_dump() == SAMPLE_QUESTION["examples"][0]
    assert read.constraints == SAMPLE_QUESTION["constraints"]
    assert read.starter_code == SAMPLE_QUESTION["starter_code"]


# QuestionRead 欄位應與 QuestionPayload 對齊。
def test_question_read_fields_match_question_payload():
    from core.ports import QuestionPayload
    from db.schemas import QuestionRead

    assert set(QuestionRead.model_fields.keys()) == set(
        QuestionPayload.__required_keys__
    )
