import pytest
from pydantic import ValidationError

from api.schemas import ChatRequest


def test_chat_request_trims_question() -> None:
    request = ChatRequest(
        session_id=None,
        question="  现在几点？  ",
    )

    assert request.question == "现在几点？"


def test_chat_request_rejects_blank_question() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            session_id=None,
            question="   ",
        )
