
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)
from typing import (
    Any,
    Literal,
)
class ChatRequest(BaseModel):
    """规定前端发送给后端的数据格式"""

    session_id: str | None = None
    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("问题不能为空")

        return value
class ChatResponse(BaseModel):
    """规定后端返回给前端的数据格式"""

    session_id: str
    answer: str
    sources: list[dict[str, Any]] = Field(
        default_factory=list
    )
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list
    )
    iteration_count: int = 0

class SessionSummary(BaseModel):
    """会话列表中的单个会话摘要。"""

    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int

class MessageResponse(BaseModel):
    """单条历史消息。"""

    role: Literal["user", "assistant"]
    content: str
    created_at: str | None = None
    sources: list[dict[str, Any]] = Field(
        default_factory=list
    )

class ClearMessagesResponse(BaseModel):
    """清空消息后的响应数据。"""

    session_id: str
    deleted_count: int
    message: str

class DeleteSessionResponse(BaseModel):
    """删除会话后的响应数据。"""

    session_id: str
    message: str

class UploadDocumentResponse(BaseModel):
    """文件加入知识库后的响应。"""

    message: str
    duplicate: bool = False
    file_id: str | None = None
    file_name: str
    document_count: int | None = None
    chunk_count: int = 0

class DocumentSummary(BaseModel):
    """知识库文件摘要。"""

    file_id: str
    file_name: str
    file_type: str
    upload_time: str
    document_count: int = 0
    chunk_count: int = 0
    status: str = "active"

class DeleteDocumentResponse(BaseModel):
    """删除知识库文件后的响应。"""

    message: str
    file_id: str
    file_name: str | None = None
    deleted_chunk_count: int
    original_file_deleted: bool
    rollback_used: bool
    cleanup_warnings: list[str] = Field(
        default_factory=list
    )