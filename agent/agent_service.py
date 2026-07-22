from typing import Any

from langchain_core.language_models.chat_models import (
    BaseChatModel,
)
from langchain_core.tools import BaseTool
from langchain_core.messages import (
    HumanMessage,
    ToolMessage,
)

from rag.chain import convert_chat_history

class AgentService:
    """
    负责管理大模型、工具，以及Agent调用流程。
    """

    def __init__( self, model: BaseChatModel,tools: list[BaseTool],max_iterations:int=5):
        # 1. 检查工具列表
        if not isinstance(tools, list):
            raise TypeError("tools 必须是列表")

        if not tools:
            raise ValueError("tools 不能为空")

        # 2. 保存原始模型
        self.model = model

        # 3. 保存全部工具
        self.tools = tools

        # 4. 将工具绑定给模型
        self.model_with_tools = (
            model.bind_tools(tools)
        )

        # 5. 创建工具名称到工具对象的映射
        self.tools_by_name={tool.name:tool for tool in self.tools}

        #定义最大循环次数
        self.max_iterations = max_iterations

    def normalize_tool_result(self,result: Any) -> dict:
        if isinstance(result, dict):
            return {
                "content": str(result.get("content", result)),
                "sources": result.get("sources", []),
                "data": result.get("data"),
                "success": result.get("success", True),
                "error": result.get("error"),

            }

        return {
            "content": str(result),
            "sources": [],
            "data": result,
            "success": True,
            "error": None,

        }

    def run(
            self,
            question: str,
            chat_history: list[dict] | None = None,
    ) -> dict:
        """
        执行一次完整的Agent问答。

        返回：
            {
                "answer": 最终回答,
                "sources": 引用来源,
                "tool_calls": 工具调用记录
            }
        """

        # 1. 检查问题
        if not isinstance(question, str):
            raise TypeError("question 必须是字符串")

        question = question.strip()

        if not question:
            raise ValueError("question 不能为空")

        # 2. 转换历史消息
        messages = convert_chat_history(
            chat_history
        )

        # 3. 添加当前用户问题
        messages.append(
            HumanMessage(content=question)
        )

        all_sources = []
        tool_call_records = []

        # 4. Agent循环
        for _ in range(self.max_iterations):
            # 调用模型
            response = self.model_with_tools.invoke(
                messages
            )

            # 保存模型返回的信息
            messages.append(response)

            # 5. 没有工具调用，说明已经生成最终答案，下一次的最终结果里面，如果tool_calls没有内容，那么就可以返回了了
            if not response.tool_calls:
                return {
                    "answer": str(response.content),
                    "sources": all_sources,
                    "tool_calls": tool_call_records,
                }

            # 6. 执行模型请求的全部工具
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                selected_tool = (
                    self.tools_by_name.get(tool_name)
                )

                if selected_tool is None:
                    tool_content = (
                        f"工具不存在：{tool_name}"
                    )
                    tool_sources = []
                    success = False

                else:
                    try:
                        raw_result = (
                            selected_tool.invoke(
                                tool_args
                            )
                        )

                        normalized_result = (
                            self.normalize_tool_result(
                                raw_result
                            )
                        )

                        tool_content = (
                            normalized_result["content"]
                        )
                        tool_sources = (
                            normalized_result["sources"]
                        )
                        success = (
                            normalized_result["success"]
                        )

                    except Exception as error:
                        tool_content = (
                            f"工具执行失败：{error}"
                        )
                        tool_sources = []
                        success = False

                # 7. 收集引用来源
                all_sources.extend(tool_sources)

                # 8. 保存工具调用记录
                tool_call_records.append(
                    {
                        "name": tool_name,
                        "args": tool_args,
                        "success": success,
                    }
                )

                # 9. 将工具结果交还给模型
                tool_message = ToolMessage(
                    content=tool_content,
                    tool_call_id=(
                            tool_call.get("id") or ""
                    ),
                    name=tool_name,
                )

                messages.append(tool_message)

        # 超过最大循环次数
        raise RuntimeError(
            "Agent超过最大工具调用次数"
        )