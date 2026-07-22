from datetime import datetime
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool

from rag.chain import build_sources, format_documents
from rag.knowledge_base import file_registry
from rag.retriever import retriever_documents


@tool
def search_knowledge_base(query: str) -> dict:
    """在知识库中检索与 query 相关的内容。输入：query：需要检索的问题。
    输出：
        {
            "content": 提供给大模型的参考内容,
            "sources": 提供给前端展示的引用来源
        }
    """

    # 1. 检查输入类型
    if not isinstance(query, str):
        raise TypeError("query 必须是字符串")

    # 2. 去除前后空格
    query = query.strip()

    # 3. 检查问题是否为空
    if not query:
        raise ValueError("query 不能为空")

    # 4. 调用原来的 Retriever 检索相关 Chunk
    documents = retriever_documents(query)

    # 5. 没有检索结果
    if not documents:
        return {
            "content": "知识库中没有检索到相关资料。",
            "sources": [],
        }
    # 6. 将 Document 列表整理成大模型可阅读的文本
    content = format_documents(documents)

    # 7. 整理前端需要展示的引用来源
    sources = build_sources(documents)

    # 8. 返回统一结果
    return {
        "content": content,
        "sources": sources,
    }


@tool
def get_current_time() -> str:
    """
    当用户询问当前日期、当前时间或今天是几号时，
    调用此工具获取服务器当前时间。
    """
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )




@tool
def calculator(
    a: float,
    b: float,
    operation: Literal[
        "add",
        "subtract",
        "multiply",
        "divide",
    ],
) -> str:
    """
    当用户需要进行两个数字的加减乘除运算时，
    调用此工具进行准确计算。

    Args:
        a: 第一个数字。
        b: 第二个数字。
        operation: 运算类型：
            add表示加法；
            subtract表示减法；
            multiply表示乘法；
            divide表示除法。
    """

    if operation == "add":
        result = a + b

    elif operation == "subtract":
        result = a - b

    elif operation == "multiply":
        result = a * b

    elif operation == "divide":
        if b == 0:
            return "计算失败：除数不能为0"

        result = a / b

    else:
        return f"不支持的运算类型：{operation}"

    return f"计算结果为：{result:g}"


@tool
def list_knowledge_documents(
    keyword: str | None = None,
    file_type: str | None = None,
) -> dict:
    """查询知识库中的文档列表，可按文件名关键词和文件类型过滤。"""

    if keyword is not None and not isinstance(keyword, str):
        raise TypeError("keyword 必须是字符串或None")

    if file_type is not None and not isinstance(file_type, str):
        raise TypeError("file_type 必须是字符串或None")

    normalized_keyword = (keyword or "").strip().lower()
    normalized_file_type = (file_type or "").strip().lower()

    if normalized_file_type:
        normalized_file_type = Path(
            normalized_file_type
        ).suffix or f".{normalized_file_type.lstrip('.')}"

    documents = []

    for file_info in file_registry.list_files():
        file_name = str(file_info.get("file_name", ""))
        current_file_type = str(
            file_info.get("file_type", "")
        ).lower()

        if (
            normalized_keyword
            and normalized_keyword not in file_name.lower()
        ):
            continue

        if (
            normalized_file_type
            and normalized_file_type != current_file_type
        ):
            continue

        documents.append(
            {
                "file_id": file_info.get("file_id"),
                "file_name": file_name,
                "file_type": current_file_type,
                "upload_time": file_info.get("upload_time"),
                "chunk_count": file_info.get("chunk_count", 0),
                "status": file_info.get("status", "active"),
            }
        )

    if not documents:
        return {
            "content": "知识库中没有符合条件的文档。",
            "data": [],
            "sources": [],
        }

    lines = [f"知识库中共有 {len(documents)} 个符合条件的文档："]

    for index, document in enumerate(documents, start=1):
        lines.append(
            f"{index}. {document['file_name']} "
            f"（{document['file_type']}，"
            f"{document['chunk_count']} 个 Chunk）"
        )

    return {
        "content": "\n".join(lines),
        "data": documents,
        "sources": [],
    }
