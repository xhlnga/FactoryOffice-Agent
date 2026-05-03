from sqlalchemy.orm import Session

from app.schemas.purchase_request import PurchaseCreateRequest
from app.services.purchase_service import create_purchase_request, list_purchase_requests
from app.tools.base import AgentTool, RiskLevel, ToolResult, approval_required_result
from app.workflows.purchase_request import generate_purchase_request


def preview_purchase_request(purchase_description: str) -> ToolResult:
    """生成采购申请草稿，不直接提交。"""
    response = generate_purchase_request(purchase_description)
    if response.missing_fields:
        return ToolResult(
            tool_name="preview_purchase_request",
            success=True,
            message=response.message,
            data=response.model_dump(mode="json"),
            requires_approval=False,
        )

    return approval_required_result(
        tool_name="preview_purchase_request",
        message=f"{response.message} 如需提交正式采购申请，需要人工确认。",
        action_type="create_purchase_request",
        action_payload=response.purchase_draft.model_dump(mode="json") if response.purchase_draft else {},
        data=response.model_dump(mode="json"),
    )


def create_purchase_record(db: Session, purchase: PurchaseCreateRequest) -> ToolResult:
    """执行已审批的采购申请创建。"""
    record = create_purchase_request(db, purchase, approved_action=True)
    return ToolResult(
        tool_name="create_purchase_request",
        success=True,
        message="采购申请创建成功。",
        data={"purchase_request_id": record.id},
    )


def query_purchase_requests(db: Session, offset: int = 0, limit: int = 20) -> ToolResult:
    """查询采购申请列表。"""
    items, total = list_purchase_requests(db, offset=offset, limit=limit)
    return ToolResult(
        tool_name="query_purchase_requests",
        success=True,
        message="采购申请列表查询成功。",
        data={
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "budget": item.budget,
                    "status": item.status,
                }
                for item in items
            ],
        },
    )


PREVIEW_PURCHASE_REQUEST_TOOL = AgentTool(
    name="preview_purchase_request",
    description="根据采购需求生成采购申请草稿；真正提交采购申请前需要人工确认。",
    handler=preview_purchase_request,
    requires_approval=False,
    risk_level=RiskLevel.LOW,
)
