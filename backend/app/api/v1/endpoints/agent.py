from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.factory_office_agent import run_factory_office_agent
from app.core.database import get_db
from app.models.base import AuditStatus
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentTraceStep, MissingField, ToolCallPreview
from app.schemas.audit_log import AuditLogCreateRequest
from app.services.audit_service import create_audit_log

router = APIRouter()


@router.post("/chat", response_model=AgentChatResponse, summary="通用 Agent 对话")
def chat_with_agent(request: AgentChatRequest, db: Session = Depends(get_db)) -> AgentChatResponse:
    """Agent 总入口，执行意图识别、知识检索、工具选择和审批判断。"""
    state = run_factory_office_agent(
        request.message,
        user_id=request.user_id,
        db=db,
        context=request.context,
    )
    tool_calls = state.get("tool_calls", [])
    answer = state.get("answer", "")
    create_audit_log(
        db,
        AuditLogCreateRequest(
            user_id=request.user_id,
            action="agent_chat",
            input=request.message,
            output=answer,
            tool_name=tool_calls[0].get("tool_name") if tool_calls else None,
            tool_args={
                "intent": state.get("intent", "unknown"),
                "requires_approval": state.get("requires_approval", False),
                "sop_id": state.get("sop_id"),
                "task_status": state.get("task_status"),
                "slot_values": state.get("slot_values", {}),
                "missing_fields": state.get("missing_fields", []),
                "tool_calls": tool_calls,
                "trace": state.get("trace_steps", []),
                "audit_events": state.get("audit_events", []),
            },
            status=AuditStatus.SUCCESS,
        ),
    )
    return AgentChatResponse(
        message=request.message,
        intent=state.get("intent", "unknown"),
        sop_id=state.get("sop_id"),
        sop_name=state.get("sop_name"),
        task_status=state.get("task_status"),
        answer=answer,
        slot_values=state.get("slot_values", {}),
        missing_fields=[
            MissingField(
                name=field.get("name", ""),
                label=field.get("label", ""),
                question=field.get("question", ""),
            )
            for field in state.get("missing_fields", [])
        ],
        next_question=state.get("next_question"),
        tool_calls=[
            ToolCallPreview(
                tool_name=tool_call.get("tool_name", ""),
                tool_args=tool_call.get("tool_args", {}),
                requires_approval=tool_call.get("requires_approval", False),
            )
            for tool_call in state.get("tool_calls", [])
        ],
        requires_approval=state.get("requires_approval", False),
        trace=[
            AgentTraceStep(
                step=step.get("step", ""),
                status=step.get("status", ""),
                detail=step.get("detail", {}),
            )
            for step in state.get("trace_steps", [])
        ],
    )
