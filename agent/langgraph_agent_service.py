from typing import Any, Literal

from langchain_core.language_models.chat_models import (
    BaseChatModel,
)
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from agent.graph_state import AgentState
from rag.chain import convert_chat_history


class LangGraphAgentService:
    """
    使用LangGraph管理Agent执行流程。
    """

    def __init__(
            self,
            model: BaseChatModel,
            tools: list[BaseTool],
            max_iterations: int = 5,
    ):
        if not isinstance(tools, list):
            raise TypeError("tools 必须是列表")

        if not tools:
            raise ValueError("tools 不能为空")

        self.model = model
        self.tools = tools
        self.max_iterations = max_iterations

        self.model_with_tools = (
            model.bind_tools(tools)
        )

        self.tools_by_name = {
            tool.name: tool
            for tool in tools
        }
        self.graph = self.build_graph()

    def call_model(
            self,
            state: AgentState,
    ) -> dict:
        """
        将当前消息列表交给绑定工具后的模型,输出AIMessages,其中为绑定工具后的大模型
        """
        response = self.model_with_tools.invoke(

            state["messages"]
        )

        return {
            "messages": [response],
            "iteration_count": (
                    state.get("iteration_count", 0) + 1
            ),
        }

    def route_after_model(
            self,
            state: AgentState,
    ) -> Literal[
        "execute_tools",
        "end",
        "max_iterations",
    ]:
        """
        根据模型回复决定下一步，这里路由函数识别大模型下一步是要干什么，执行工具，还是返回结果等等

        """

        messages = state.get("messages", [])

        if not messages:
            raise ValueError("messages 不能为空")

        last_message = messages[-1]

        tool_calls = getattr(
            last_message,
            "tool_calls",
            [],
        )

        # 模型没有请求工具，说明已经生成最终回答
        if not tool_calls:
            return "end"

        # 模型仍要调用工具，但已经达到次数限制
        if (
                state.get("iteration_count", 0)
                >= self.max_iterations
        ):
            return "max_iterations"

        # 模型请求了工具，继续进入工具节点
        return "execute_tools"

    def normalize_tool_result(
            self,
            result: Any,
    ) -> dict:
        """
        将不同工具的返回值统一为相同格式。
        """
        #首先是知识库返回的结果
        if isinstance(result, dict):
            sources = result.get(
                "sources",
                [],
            )
            #
            if not isinstance(sources, list):
                sources = []

            return {
                "content": str(
                    result.get("content", result)
                ),
                "sources": sources,
                "success": result.get(
                    "success",
                    True,
                ),
            }

        return {
            "content": str(result),
            "sources": [],
            "success": True,
        }

    def execute_tools(
            self,
            state: AgentState,
    ) -> dict:
        """
        执行模型请求的全部工具,这里返回的还是tool_messages
        """

        messages = state.get("messages", [])

        if not messages:
            raise ValueError("messages 不能为空")

        last_message = messages[-1]

        tool_calls = getattr(
            last_message,
            "tool_calls",
            [],
        )

        if not tool_calls:
            raise ValueError(
                "最近一条模型消息中没有工具调用"
            )

        tool_messages = []
        collected_sources = []
        tool_call_records = []

        for tool_call in tool_calls:
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
                    raw_result = selected_tool.invoke(
                        tool_args
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

            tool_messages.append(
                ToolMessage(
                    content=tool_content,
                    tool_call_id=tool_call.get(
                        "id",
                        "",
                    ),
                    name=tool_name,
                )
            )

            collected_sources.extend(
                tool_sources
            )

            tool_call_records.append(
                {
                    "name": tool_name,
                    "args": tool_args,
                    "success": success,
                }
            )

        return {
            "messages": tool_messages,
            "sources": collected_sources,
            "tool_calls": tool_call_records,
        }

    def handle_max_iterations(
            self,
            state: AgentState,
    ) -> dict:
        """
        不用于判断是否达到最大，只管达到最大的时候，Agent达到最大循环次数时结束流程。
        """

        last_message = state["messages"][-1]

        pending_tool_calls = getattr(
            last_message,
            "tool_calls",
            [],
        )

        limit_messages = []
        failed_records = []

        for tool_call in pending_tool_calls:
            tool_name = tool_call["name"]

            limit_messages.append(
                ToolMessage(
                    content=(
                        "工具未执行：Agent已经达到"
                        "最大循环次数"
                    ),
                    tool_call_id=tool_call.get(
                        "id",
                        "",
                    ),
                    name=tool_name,
                )
            )

            failed_records.append(
                {
                    "name": tool_name,
                    "args": tool_call["args"],
                    "success": False,
                }
            )

        limit_messages.append(
            AIMessage(
                content=(
                    f"Agent已经达到最大循环次数"
                    f"（{self.max_iterations}次），"
                    "无法继续执行工具。"
                )
            )
        )

        return {
            "messages": limit_messages,
            "tool_calls": failed_records,
        }

    def build_graph(self):
        """
        创建并编译LangGraph工作流。我们说节点就是接收当前状态，然后执行下一项工作，并且返回更新状态
        """
        #创建节点构造者
        graph_builder=StateGraph(AgentState)
        graph_builder.add_node(
            "call_model",
            self.call_model,
        )
        graph_builder.add_node(
            "execute_tools",
            self.execute_tools,
        )
        graph_builder.add_node(
            "handle_max_iterations",
            self.handle_max_iterations,
        )
        graph_builder.add_edge(
            START,
            "call_model",
        )
        #添加条件边
        graph_builder.add_conditional_edges(
            "call_model",
            self.route_after_model,
            {
                "execute_tools": "execute_tools",
                "end": END,
                "max_iterations": "handle_max_iterations",
            }
        )

        graph_builder.add_edge(
            "execute_tools",
            "call_model",
        )

        graph_builder.add_edge(
            "handle_max_iterations",
            END,
        )

        return graph_builder.compile()

    def run(
            self,
            question: str,
            chat_history: list[dict] | None = None,
    ) -> dict:
        """
        执行完整的LangGraph Agent流程。
        """

        if not isinstance(question, str):
            raise TypeError("question 必须是字符串")

        question = question.strip()

        if not question:
            raise ValueError("question 不能为空")

        if (
                chat_history is not None
                and not isinstance(chat_history, list)
        ):
            raise TypeError(
                "chat_history 必须是列表或None"
            )

        # 1. 把JSON格式的历史消息转换为
        # LangChain消息对象
        messages=convert_chat_history(chat_history or [])
        # 2. 加入当前用户问题
        messages.append(
            HumanMessage(
                content=question
            )
        )

        # 3. 创建LangGraph初始状态
        initial_state: AgentState = {
            "messages": messages,
            "sources": [],
            "tool_calls": [],
            "iteration_count": 0,
        }
        final_state=self.graph.invoke(initial_state)
        # 5. 获取最终消息
        final_messages = final_state.get(
            "messages",
            [],
        )
        if not final_messages:
            raise RuntimeError(
                "Agent没有生成任何消息"
            )

        final_message = final_messages[-1]
        answer = str(
            final_message.content
        ).strip()

        if not answer:
            raise RuntimeError(
                "Agent没有生成有效回答"
            )
        return {
            "answer": answer,
            "sources": final_state.get(
                "sources",
                [],
            ),
            "tool_calls": final_state.get(
                "tool_calls",
                [],
            ),
            "iteration_count": final_state.get(
                "iteration_count",
                0,
            ),
        }













