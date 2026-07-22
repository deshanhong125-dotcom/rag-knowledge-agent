import operator
from typing import Annotated

from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    LangGraph Agent中所有节点共享的状态。
    """
    messages:Annotated[
        list[BaseMessage],
        add_messages
    ]
    #这里加上annotated是为了说明这里的message不仅是list还可以继续追加消息

    sources: Annotated[
        list[dict],
        operator.add,
    ]

    tool_calls: Annotated[
        list[dict],
        operator.add,
    ]

    iteration_count: int

