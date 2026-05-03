from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.base import ApprovalStatus
from app.schemas.common import ORMModel


class ApprovalCreateRequest(BaseModel):
    """创建审批请求。"""

    action_type: str = Field(..., min_length=1, max_length=128, description="动作类型")
    action_payload: dict[str, Any] = Field(default_factory=dict, description="动作参数")


class ApprovalDecisionRequest(BaseModel):
    """审批决定请求。"""

    reviewer: str = Field(..., min_length=1, max_length=128, description="审批人")
    comment: str = Field(default="", max_length=512, description="审批意见")


class ApprovalRead(ORMModel):
    """审批响应结构。"""

    id: int = Field(..., description="审批 ID")
    action_type: str = Field(..., description="动作类型")
    action_payload: dict[str, Any] = Field(default_factory=dict, description="动作参数")
    status: ApprovalStatus = Field(..., description="审批状态")
    reviewer: str | None = Field(default=None, description="审批人")
    reviewed_at: datetime | None = Field(default=None, description="审批时间")
    executed_at: datetime | None = Field(default=None, description="执行时间")
    execution_result: dict[str, Any] | None = Field(default=None, description="执行结果")
    comment: str | None = Field(default=None, description="审批意见")
    created_at: datetime = Field(..., description="创建时间")
