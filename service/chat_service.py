from rag.chat_history_manager import (
    ChatHistoryManager,
)
from agent.langgraph_agent_service import (
    LangGraphAgentService,
)


class ChatService:
    """
    负责协调聊天历史和 RAG 问答流程。在创建这个类对象的时候，需要传入ChatHistoryManager 对象
    """

    def __init__(
            self,
            history_manager: ChatHistoryManager,
            agent_service: LangGraphAgentService,
    ):
        self.history_manager = history_manager
        self.agent_service = agent_service

    def ensure_session( self, session_id: str | None,) -> str:
        """
        确保会话存在。会话不存在时创建新会话。
        """
        # 1. None表示前端还没有会话
        if session_id is None:
            return (self.history_manager.create_session())

        # 2. 非None时必须是字符串
        if not isinstance(session_id, str):
            raise TypeError("session_id必须是字符串或None")

        # 3. 去除前后空格
        session_id = session_id.strip()

        # 4. 空字符串也视为没有会话
        if not session_id:
            return (self.history_manager.create_session())

        # 5. 查询会话是否真实存在
        session = (self.history_manager.get_session( session_id))

        # 6. 不存在时创建新会话
        if session is None:
            return (self.history_manager.create_session())
        # 7. 存在时返回原ID
        return session_id

    def chat(self,session_id: str | None,question: str,) -> dict:
        """我们有session_id我们可以去要历史聊天记录，再加上question我们就可以去组装问题，去回答问题"""
        # 1. 检查question是不是字符串
        if  not isinstance(question, str):
            raise TypeError("请输入字符串问题")

        # 2. 去除question前后空格并检查是否为空
        question = question.strip()
        if  not question:
            raise  KeyError("请输入问题")
        # 3. 调用ensure_session()获得有效session_id
        session_id=self.ensure_session(session_id)
        # 4. 调用get_messages()读取旧历史
        chat_history_data=self.history_manager.get_messages(session_id)
        if chat_history_data is None:
            chat_history_data = []
        # 5. 调用rag_answer()生成回答
        result=self.agent_service.run(question=question,chat_history=chat_history_data)

        # 6. 保存用户消息
        self.history_manager.add_message(session_id,role="user",content=question)
        # 7. 保存助手消息和sources
        self.history_manager.add_message(session_id,role="assistant",content=result["answer"],sources=result.get("sources",[]))

        # 8. 给result补充session_id
        result["session_id"]=session_id

        # 9. 返回result
        return result



