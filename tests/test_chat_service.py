from pathlib import Path

from rag.chat_history_manager import ChatHistoryManager
from service.chat_service import ChatService


class FakeAgentService:
    def run(
        self,
        question: str,
        chat_history: list[dict] | None = None,
    ) -> dict:
        return {
            "answer": f"测试回答：{question}",
            "sources": [],
            "tool_calls": [],
            "iteration_count": 1,
        }


def test_chat_creates_session_and_persists_messages(
    tmp_path: Path,
) -> None:
    history_manager = ChatHistoryManager(
        history_path=tmp_path / "chat_history.json"
    )
    service = ChatService(
        history_manager=history_manager,
        agent_service=FakeAgentService(),
    )

    result = service.chat(
        session_id=None,
        question="测试问题",
    )

    messages = history_manager.get_messages(
        result["session_id"]
    )

    assert messages is not None
    assert [message["role"] for message in messages] == [
        "user",
        "assistant",
    ]
    assert messages[0]["content"] == "测试问题"
    assert messages[1]["content"] == "测试回答：测试问题"
