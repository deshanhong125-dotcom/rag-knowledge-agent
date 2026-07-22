from functools import lru_cache

from langchain_community.chat_models import (
    ChatTongyi,
)



from rag.file_registry import FileRegistry
from rag.knowledge_base import (
    file_registry as knowledge_base_file_registry,
)
from agent.langgraph_agent_service import (
    LangGraphAgentService,
)
from agent.tools import (
    calculator,
    get_current_time,
    list_knowledge_documents,
    search_knowledge_base,
)
from config import CHAT_MODEL_NAME
from rag.chat_history_manager import (
    ChatHistoryManager,
)
from service.chat_service import ChatService

@lru_cache(maxsize=1)
def get_history_manager() -> ChatHistoryManager:
    """创建并复用历史记录管理器。"""

    return ChatHistoryManager()


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    """创建并复用聊天服务。"""

    history_manager = get_history_manager()

    model = ChatTongyi(
        model=CHAT_MODEL_NAME
    )

    tools = [
        search_knowledge_base,
        list_knowledge_documents,
        get_current_time,
        calculator,
    ]

    agent_service = LangGraphAgentService(
        model=model,
        tools=tools,
    )

    return ChatService(
        history_manager=history_manager,
        agent_service=agent_service,
    )


def get_file_registry() -> FileRegistry:
    """获取知识库正在使用的文件注册表。"""

    return knowledge_base_file_registry
