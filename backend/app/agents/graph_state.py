from typing import Any, Literal, TypedDict

from app.agents.task_state import AgentTaskStatus


AgentIntent = Literal[
    "knowledge_qa",
    "meeting_to_tasks",
    "maintenance_ticket",
    "quality_issue",
    "purchase_request",
    "weekly_report",
    "unknown",
]


class ToolCallDraft(TypedDict, total=False):
    """工具调用草稿，真正执行前通常需要审批。"""

    tool_name: str
    tool_args: dict[str, Any]
    requires_approval: bool
    reason: str


class RetrievedChunk(TypedDict, total=False):
    """检索到的知识库片段。"""

    document_id: int | None
    document_title: str | None
    filename: str | None
    chunk_id: int | None
    chunk_index: int | None
    chunk_text: str
    score: float | None


class AuditEvent(TypedDict, total=False):
    """Agent 内部审计事件。"""

    action: str
    status: str
    detail: dict[str, Any]


class MissingField(TypedDict, total=False):
    """SOP 缺失字段。"""

    name: str
    label: str
    question: str


class TraceStep(TypedDict, total=False):
    """Agent 可解释执行轨迹。"""

    step: str
    status: str
    detail: dict[str, Any]


class FactoryAgentState(TypedDict, total=False):
    """FactoryOffice-Agent 图状态。

    这个状态会在 LangGraph 节点之间传递，也可以被降级执行器直接复用。
    """

    user_id: int | None
    db: Any | None
    context: dict[str, Any]
    message: str
    effective_message: str
    intent: AgentIntent
    intent_confidence: float
    sop_id: str | None
    sop_name: str | None
    task_status: AgentTaskStatus
    slot_values: dict[str, Any]
    missing_fields: list[MissingField]
    next_question: str | None
    answer: str
    retrieved_chunks: list[RetrievedChunk]
    tool_calls: list[ToolCallDraft]
    requires_approval: bool
    approval_payload: dict[str, Any]
    trace_steps: list[TraceStep]
    audit_events: list[AuditEvent]
    error: str | None
