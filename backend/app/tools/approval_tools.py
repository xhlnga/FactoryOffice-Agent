from sqlalchemy.orm import Session

from app.schemas.approval import ApprovalCreateRequest
from app.services.approval_service import create_approval
from app.tools.base import AgentTool, RiskLevel, ToolResult


def create_approval_record(
    db: Session,
    *,
    action_type: str,
    action_payload: dict,
) -> ToolResult:
    """创建审批记录。"""
    approval = create_approval(
        db,
        ApprovalCreateRequest(
            action_type=action_type,
            action_payload=action_payload,
        ),
    )
    return ToolResult(
        tool_name="create_approval",
        success=True,
        message="审批记录创建成功。",
        data={"approval_id": approval.id, "status": approval.status},
        requires_approval=False,
    )


CREATE_APPROVAL_TOOL = AgentTool(
    name="create_approval",
    description="把需要确认的业务动作写入审批表，等待人工批准或拒绝。",
    handler=create_approval_record,
    requires_approval=False,
    risk_level=RiskLevel.LOW,
)
