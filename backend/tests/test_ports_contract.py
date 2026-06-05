import inspect
import typing

from core import events, ports


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


def test_example_case_contract_is_defined():
    required = ports.ExampleCase.__required_keys__
    assert {"input", "output", "explanation"} <= required


def test_judge_result_contract_requires_score_only():
    required = ports.JudgeResult.__required_keys__
    assert {"score"} <= required


def test_judge_service_signature_is_stable():
    sig = inspect.signature(ports.IJudgeService.judge)
    assert sig.parameters["question"].annotation is str
    assert sig.parameters["code"].annotation is str
    assert sig.return_annotation is ports.JudgeResult


def test_question_service_signature_is_stable():
    sig = inspect.signature(ports.IQuestionService.get_random_question)
    assert sig.return_annotation is ports.QuestionPayload


def test_inbound_events_are_literal_union():
    assert typing.get_args(events.InboundEvent) == ("join", "start", "submit", "violation")
    assert events.JOIN == "join"
    assert events.START == "start"
    assert events.SUBMIT == "submit"
    assert events.VIOLATION == "violation"


def test_notify_service_signature_is_stable():
    sig = inspect.signature(ports.INotifyService.notify_room)
    assert sig.parameters["room_code"].annotation is str
    assert sig.parameters["event"].annotation is ports.RoomEvent
    assert sig.return_annotation is None
