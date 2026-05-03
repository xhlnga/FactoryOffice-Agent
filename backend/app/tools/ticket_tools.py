from sqlalchemy.orm import Session

from app.schemas.ticket import TicketCreateRequest
from app.services.ticket_service import create_ticket, list_tickets
from app.tools.base import AgentTool, RiskLevel, ToolResult, approval_required_result
from app.workflows.maintenance_ticket import generate_maintenance_ticket
from app.workflows.quality_issue import generate_quality_issue_ticket


def preview_maintenance_ticket(issue_description: str) -> ToolResult:
    """生成维修工单草稿，不直接提交。"""
    response = generate_maintenance_ticket(issue_description)
    if response.ticket_draft is None:
        return ToolResult(
            tool_name="preview_maintenance_ticket",
            success=True,
            message=response.message,
            data=response.model_dump(mode="json"),
            requires_approval=False,
        )

    return approval_required_result(
        tool_name="preview_maintenance_ticket",
        message=f"{response.message} 如需提交正式维修工单，需要人工确认。",
        action_type="create_maintenance_ticket",
        action_payload=response.ticket_draft.model_dump(mode="json") if response.ticket_draft else {},
        data=response.model_dump(mode="json"),
    )


def preview_quality_issue_ticket(issue_description: str) -> ToolResult:
    """生成质量异常工单草稿，不直接提交。"""
    response = generate_quality_issue_ticket(issue_description)
    if response.quality_issue_draft is None:
        return ToolResult(
            tool_name="preview_quality_issue_ticket",
            success=True,
            message=response.message,
            data=response.model_dump(mode="json"),
            requires_approval=False,
        )

    payload = response.quality_issue_draft.model_dump(mode="json") if response.quality_issue_draft else {}
    return approval_required_result(
        tool_name="preview_quality_issue_ticket",
        message=f"{response.message} 如需提交正式质量异常工单，需要人工确认。",
        action_type="create_quality_issue_ticket",
        action_payload=payload,
        data=response.model_dump(mode="json"),
    )


def create_ticket_record(db: Session, ticket: TicketCreateRequest) -> ToolResult:
    """执行已审批的工单创建。"""
    record = create_ticket(db, ticket, approved_action=True)
    return ToolResult(
        tool_name="create_ticket",
        success=True,
        message="工单创建成功。",
        data={"ticket_id": record.id},
    )


def query_tickets(db: Session, offset: int = 0, limit: int = 20) -> ToolResult:
    """查询工单列表。"""
    items, total = list_tickets(db, offset=offset, limit=limit)
    return ToolResult(
        tool_name="query_tickets",
        success=True,
        message="工单列表查询成功。",
        data={
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "ticket_type": item.ticket_type,
                    "title": item.title,
                    "status": item.status,
                    "priority": item.priority,
                }
                for item in items
            ],
        },
    )


PREVIEW_MAINTENANCE_TICKET_TOOL = AgentTool(
    name="preview_maintenance_ticket",
    description="根据设备异常生成维修工单草稿；真正提交工单前需要人工确认。",
    handler=preview_maintenance_ticket,
    requires_approval=False,
    risk_level=RiskLevel.LOW,
)

PREVIEW_QUALITY_ISSUE_TICKET_TOOL = AgentTool(
    name="preview_quality_issue_ticket",
    description="根据质量异常描述生成 NCR/质量异常工单草稿；真正提交工单前需要人工确认。",
    handler=preview_quality_issue_ticket,
    requires_approval=False,
    risk_level=RiskLevel.LOW,
)
