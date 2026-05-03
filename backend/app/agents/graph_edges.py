from app.agents.graph_state import FactoryAgentState


def route_after_intent(state: FactoryAgentState) -> str:
    """意图识别后的路由。"""
    intent = state.get("intent", "unknown")
    if intent == "knowledge_qa":
        return "retrieve_knowledge"
    if intent in {"meeting_to_tasks", "maintenance_ticket", "quality_issue", "purchase_request", "weekly_report"}:
        return "select_tools"
    return "final_answer"


def route_after_retrieval(_: FactoryAgentState) -> str:
    """知识库检索后的路由。"""
    return "select_tools"


def route_after_tool_selection(state: FactoryAgentState) -> str:
    """工具选择后的路由。"""
    if state.get("requires_approval", False):
        return "approval_gate"
    return "final_answer"


def route_after_approval_gate(_: FactoryAgentState) -> str:
    """审批判断后的路由。"""
    return "final_answer"
