from pydantic import BaseModel, Field

from app.schemas.approval import ApprovalRead
from app.schemas.approval_template import ApprovalInstanceRead


class MobileApprovalDetail(BaseModel):
    """移动审批详情结构。"""

    approval: ApprovalRead = Field(..., description="兼容审批记录")
    instance: ApprovalInstanceRead | None = Field(default=None, description="多级审批实例")
    message: str = Field(..., description="结果说明")


class MobileApprovalDecisionResponse(BaseModel):
    """移动审批操作响应。"""

    approval: ApprovalRead = Field(..., description="审批记录")
    message: str = Field(..., description="操作结果")
