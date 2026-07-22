from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
)
from langchain_core.output_parsers import (
    StrOutputParser,
)

from config import CHAT_MODEL_NAME
from rag.prompt import (
    rag_prompt,
    rewrite_prompt,
)
from rag.retriever import retriever_documents
def convert_chat_history(chat_history: list[dict] | None,) -> list[BaseMessage]:
    """
    将前端消息字典转换为 LangChain 消息对象。
    前端格式：
    {
        "role": "user" | "assistant",
        "content": "消息正文"
    }
    后端格式：
    HumanMessage / AIMessage
    """
    if not chat_history:
        return []

    langchain_messages: list[ BaseMessage] = []

    for message in chat_history:
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        content = message.get("content","", )

        if not isinstance(content, str):
            continue

        content = content.strip()

        if not content:
            continue

        if role == "user":
            langchain_messages.append(  HumanMessage( content=content ))

        elif role == "assistant":
            langchain_messages.append(AIMessage( content=content ))

    return langchain_messages


def format_documents( documents,) -> str:
    """
    将检索到的 Document 格式化为 Prompt 文本。
    """

    formatted_documents = []

    for index, document in enumerate( documents, start=1,):
        file_name = document.metadata.get(
            "file_name",
            "未知文件",
        )

        page = document.metadata.get(
            "page"
        )

        if isinstance(page, int):
            display_page = page + 1
        else:
            display_page = "未知"

        formatted_document = (
            f"【参考资料 {index}】\n"
            f"文件名：{file_name}\n"
            f"页码：{display_page}\n"
            f"文件内容：\n"
            f"{document.page_content}"
        )

        formatted_documents.append(
            formatted_document
        )

    return "\n\n".join(
        formatted_documents
    )

def build_sources(documents,) -> list[dict]:
    """
    从检索结果中整理引用来源。
    """
    sources = []
    for document in documents:
        page = document.metadata.get("page" )

        source = {"file_name": ( document.metadata.get("file_name","未知文件", )),"page": (page + 1 if isinstance(page, int)
                else None
            ),
            "index": (document.metadata.get( "chunk_index")),
            "chunk_id": ( document.metadata.get("chunk_id")),
            "chunk_content": document.page_content,
        }

        sources.append(source)

    return sources




def rag_answer( question: str | None, chat_history: list[dict] | None = None,) -> dict:
    """
    执行历史感知 RAG 问答。

    输入：
        question：
            当前用户问题。

        chat_history：
            当前问题之前的历史消息。
    输出：
        {
            "question": 原始问题,
            "rewritten_question": 改写问题,
            "answer": 模型回答,
            "sources": 引用来源
        }
    """

    if question is None:
        raise ValueError(
            "输入问题不能为 None"
        )

    if not isinstance(question, str):
        raise TypeError(
            "question 必须是字符串"
        )

    question = question.strip()

    if not question:
        raise ValueError(
            "输入问题不能为空"
        )

    # 1. 转换历史消息格式
    history = convert_chat_history(
        chat_history
    )

    # 2. 根据历史改写当前问题，这里获取到的是改写后的问题
    rewritten_question = (
        rewrite_question(
            question=question,
            history=history,
        )
    )

    # 3. 使用改写后的问题检索
    documents = retriever_documents(
        rewritten_question
    )

    if not documents:
        return {
            "question": question,
            "rewritten_question": (
                rewritten_question
            ),
            "answer": (
                "知识库中没有检索到相关资料。"
            ),
            "sources": [],
        }

    # 4. 格式化检索资料
    context = format_documents(
        documents
    )

    # 5. 使用原始问题生成最终回答
    answer_chain = create_answer_chain()

    answer = answer_chain.invoke(
        {
            "context": context,
            "history": history,
            "question": question,
        }
    )

    # 6. 整理引用来源
    sources = build_sources(
        documents
    )

    return {
        "question": question,
        "rewritten_question": (
            rewritten_question
        ),
        "answer": answer,
        "sources": sources,
    }


def rewrite_question(question: str, history: list[BaseMessage],) -> str:
    """
    根据历史消息将当前问题改写为完整问题。

    没有历史消息时直接返回原问题，
    避免不必要的大模型调用。
    """
    if not history:
        return question
    model = ChatTongyi(model=CHAT_MODEL_NAME)
    rewrite_chain = (
        rewrite_prompt
        | model
        | StrOutputParser()
    )
    rewritten_question = (
        rewrite_chain.invoke(
            {
                "history": history,
                "question": question,
            }
        )
    )

    if not isinstance(rewritten_question, str, ):
        return question

    rewritten_question = (rewritten_question.strip())

    if not rewritten_question:
        return question

    return rewritten_question


def create_answer_chain():
    """
    创建最终回答链。
    """

    model = ChatTongyi(model=CHAT_MODEL_NAME)

    return (
        rag_prompt
        | model
        | StrOutputParser()
    )