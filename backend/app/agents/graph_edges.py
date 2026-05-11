from app.agents.graph_state import FactoryAgentState


def route_after_classify(state: FactoryAgentState) -> str:
    """意图分类后的路由：低置信度或未知意图进入查询改写，否则按意图路由。"""
    intent = state.get("intent", "unknown")
    confidence = state.get("intent_confidence", 0.0)

    if confidence < 0.8 or intent == "unknown":
        return "query_rewrite"
    return route_after_intent(state)


def route_after_rewrite(state: FactoryAgentState) -> str:
    """查询改写后的路由：改写完成后按意图正常路由。"""
    return route_after_intent(state)


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
