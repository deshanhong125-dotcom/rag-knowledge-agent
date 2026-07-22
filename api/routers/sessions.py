from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from api.dependencies import get_history_manager
from api.schemas import (
    ClearMessagesResponse,
    DeleteSessionResponse,
    MessageResponse,
    SessionSummary,
)
from rag.chat_history_manager import (
    ChatHistoryManager,
)


router = APIRouter(
    tags=["sessions"],
)


@router.get(
    "/sessions",
    response_model=list[SessionSummary],
)
def get_sessions(
    history_manager: ChatHistoryManager = Depends(
        get_history_manager
    ),
) -> list[SessionSummary]:
    """获取全部聊天会话摘要。"""

    sessions = history_manager.list_sessions()

    sessions.sort(
        key=lambda session: session.get(
            "updated_at",
            "",
        ),
        reverse=True,
    )

    return [
        SessionSummary(
            session_id=session["session_id"],
            title=session.get(
                "title",
                "新对话",
            ),
            created_at=session.get(
                "created_at",
                "",
            ),
            updated_at=session.get(
                "updated_at",
                "",
            ),
            message_count=session.get("message_count",0),
        )
        for session in sessions
    ]


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[MessageResponse],
)
def get_session_messages(
    session_id: str,
    history_manager: ChatHistoryManager = Depends(
        get_history_manager
    ),
) -> list[MessageResponse]:
    """获取指定会话的全部历史消息。"""

    messages = history_manager.get_messages(
        session_id
    )

    if messages is None:
        raise HTTPException(
            status_code=404,
            detail=f"会话不存在：{session_id}",
        )

    return [
        MessageResponse(
            role=message["role"],
            content=message["content"],
            created_at=message.get(
                "created_at"
            ),
            sources=message.get(
                "sources",
                [],
            ),

        )
        for message in messages
    ]


@router.delete(
    "/sessions/{session_id}/messages",
    response_model=ClearMessagesResponse,
)
def clear_session_messages(
    session_id: str,
    history_manager: ChatHistoryManager = Depends(
        get_history_manager
    ),
) -> ClearMessagesResponse:
    """清空指定会话中的全部message。"""

    try:
        deleted_count = (
            history_manager.clear_messages(
                session_id
            )
        )

    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=f"会话不存在：{session_id}",
        ) from error

    return ClearMessagesResponse(
        session_id=session_id,
        deleted_count=deleted_count,
        message="会话消息清空成功",
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=DeleteSessionResponse,
)
def delete_session(
    session_id: str,
    history_manager: ChatHistoryManager = Depends(
        get_history_manager
    ),
) -> DeleteSessionResponse:
    """删除指定会话及其全部消息。"""

    session = history_manager.get_session(
        session_id
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"会话不存在：{session_id}",
        )

    history_manager.delete_session(
        session_id
    )

    return DeleteSessionResponse(
        session_id=session_id,
        message="会话删除成功",
    )