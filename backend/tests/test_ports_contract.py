import inspect
import typing

from core import events, ports


# QuestionPayload 應包含 Room 驗證所需的核心欄位。
def test_question_contract_requires_core_fields():
    required = ports.QuestionPayload.__required_keys__
    assert {
        "id",
        "title",
        "description",
        "examples",
        "constraints",
        "starter_code",
    } <= required


# ExampleCase 應定義 input、output、explanation 欄位。
def test_example_case_contract_is_defined():
    required = ports.ExampleCase.__required_keys__
    assert {"input", "output", "explanation"} <= required


# JudgeResult 至少需包含 score 欄位。
def test_judge_result_contract_requires_score_only():
    required = ports.JudgeResult.__required_keys__
    assert {"score"} <= required


# IJudgeService.judge 簽名應穩定（question、code → JudgeResult）。
def test_judge_service_signature_is_stable():
    sig = inspect.signature(ports.IJudgeService.judge)
    assert sig.parameters["question"].annotation is str
    assert sig.parameters["code"].annotation is str
    assert sig.return_annotation is ports.JudgeResult


# IQuestionService.get_random_question 簽名應回傳 QuestionPayload。
def test_question_service_signature_is_stable():
    sig = inspect.signature(ports.IQuestionService.get_random_question)
    assert sig.return_annotation is ports.QuestionPayload


# InboundEvent 應鎖定四種 Client → Server 事件名稱。
def test_inbound_events_are_literal_union():
    assert typing.get_args(events.InboundEvent) == ("join", "start", "submit", "violation")
    assert events.JOIN == "join"
    assert events.START == "start"
    assert events.SUBMIT == "submit"
    assert events.VIOLATION == "violation"


# INotifyService.notify_room 簽名應穩定（room_code、RoomEvent → None）。
def test_notify_service_signature_is_stable():
    sig = inspect.signature(ports.INotifyService.notify_room)
    assert sig.parameters["room_code"].annotation is str
    assert sig.parameters["event"].annotation is ports.RoomEvent
    assert sig.return_annotation is None
