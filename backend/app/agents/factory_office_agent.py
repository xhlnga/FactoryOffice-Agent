from collections.abc import Callable
from typing import Any

from app.agents.graph_edges import (
    route_after_approval_gate,
    route_after_intent,
    route_after_retrieval,
    route_after_tool_selection,
)
from app.agents.graph_nodes import (
    approval_gate_node,
    classify_intent_node,
    final_answer_node,
    retrieve_knowledge_node,
    select_tools_node,
)
from app.agents.graph_state import FactoryAgentState


NodeFn = Callable[[FactoryAgentState], FactoryAgentState]


class FactoryOfficeAgent:
    """制造业知识库与办公流程 Agent 总入口。

    如果运行环境安装了 LangGraph，则使用 LangGraph 编译图。
    如果暂未安装，则使用同样节点函数的本地降级执行器。
    """

    def __init__(self) -> None:
        self._graph = build_langgraph_or_none()

    def run(
        self,
        message: str,
        *,
        user_id: int | None = None,
        db: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> FactoryAgentState:
        """执行一次 Agent 流程。"""
        initial_state: FactoryAgentState = {
            "user_id": user_id,
            "db": db,
            "context": context or {},
            "message": message,
            "effective_message": message,
            "retrieved_chunks": [],
            "tool_calls": [],
            "requires_approval": False,
            "approval_payload": {},
            "trace_steps": [],
            "audit_events": [],
            "error": None,
        }

        if self._graph is not None:
            return self._graph.invoke(initial_state)
        return run_fallback_graph(initial_state)


def build_langgraph_or_none() -> Any | None:
    """尝试构建 LangGraph 图；依赖缺失时返回 None。"""
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return None

    graph = StateGraph(FactoryAgentState)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("retrieve_knowledge", retrieve_knowledge_node)
    graph.add_node("select_tools", select_tools_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("final_answer", final_answer_node)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {
            "retrieve_knowledge": "retrieve_knowledge",
            "select_tools": "select_tools",
            "final_answer": "final_answer",
        },
    )
    graph.add_conditional_edges(
        "retrieve_knowledge",
        route_after_retrieval,
        {"select_tools": "select_tools"},
    )
    graph.add_conditional_edges(
        "select_tools",
        route_after_tool_selection,
        {
            "approval_gate": "approval_gate",
            "final_answer": "final_answer",
        },
    )
    graph.add_conditional_edges(
        "approval_gate",
        route_after_approval_gate,
        {"final_answer": "final_answer"},
    )
    graph.add_edge("final_answer", END)
    return graph.compile()


def run_fallback_graph(state: FactoryAgentState) -> FactoryAgentState:
    """未安装 LangGraph 时的降级执行流程。"""
    state = classify_intent_node(state)
    next_node = route_after_intent(state)

    if next_node == "retrieve_knowledge":
        state = retrieve_knowledge_node(state)
        next_node = route_after_retrieval(state)

    if next_node == "select_tools":
        state = select_tools_node(state)
        next_node = route_after_tool_selection(state)

    if next_node == "approval_gate":
        state = approval_gate_node(state)
        next_node = route_after_approval_gate(state)

    if next_node == "final_answer":
        state = final_answer_node(state)

    return state


def run_factory_office_agent(
    message: str,
    *,
    user_id: int | None = None,
    db: Any | None = None,
    context: dict[str, Any] | None = None,
) -> FactoryAgentState:
    """便捷函数：执行 FactoryOffice-Agent。"""
    return FactoryOfficeAgent().run(message, user_id=user_id, db=db, context=context)
