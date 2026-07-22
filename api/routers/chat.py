import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from api.dependencies import get_chat_service
from api.schemas import (
    ChatRequest,
    ChatResponse,
)
from service.chat_service import ChatService


logger = logging.getLogger(__name__)


router = APIRouter(
    tags=["chat"],
)


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(
        get_chat_service
    ),
) -> ChatResponse:
    """接收问题并返回Agent回答。"""

    try:
        result=chat_service.chat(
            session_id=request.session_id,
            question=request.question
        )
        return ChatResponse(
            session_id=result["session_id"],
            answer=result["answer"],
            sources=result.get("sources", []),
            tool_calls=result.get(
                "tool_calls",
                [],
            ),
            iteration_count=result.get(
                "iteration_count",
                0,
            ),
        )

    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        logger.exception("聊天请求处理失败")

        raise HTTPException(
            status_code=500,
            detail="回答生成失败，请稍后重试",
        ) from error


