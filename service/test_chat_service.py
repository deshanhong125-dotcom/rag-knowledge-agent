from langchain_community.chat_models import ChatTongyi
from agent.langgraph_agent_service import (
    LangGraphAgentService,
)
from config import CHAT_MODEL_NAME
from rag.chat_history_manager import ChatHistoryManager
from agent.agent_service import AgentService
from agent.tools import (
    search_knowledge_base,
    get_current_time,
    calculator,
)
from service.chat_service import ChatService
def main():
    history_manager = ChatHistoryManager()
    model=ChatTongyi(model=CHAT_MODEL_NAME)
    tools = [
        search_knowledge_base,
        get_current_time,
        calculator,
    ]
    agent_service = LangGraphAgentService(
        model=model,
        tools=tools,
    )
    chat_service=ChatService(history_manager=history_manager,agent_service=agent_service)
    result=chat_service.chat(session_id=None,question="什么是车辆路径规划")
    session_id = result["session_id"]
    print("会话ID：")
    print(session_id)

    print("\n最终回答：")
    print(result["answer"])

    print("\n工具调用：")
    print(result["tool_calls"])

    print("\n保存后的历史消息：")
    messages = history_manager.get_messages(
        session_id
    )

    for message in messages:
        print(message)


if __name__ == "__main__":
    main()


