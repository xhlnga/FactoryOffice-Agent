from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.base import (
    ApprovalActionType,
    ApprovalInstanceStatus,
    ApprovalStepMode,
    ApprovalStepStatus,
    ApprovalTemplateStatus,
    ApproverType,
)
from app.schemas.common import ORMModel


class ApprovalStepCreateRequest(BaseModel):
    """审批模板步骤创建结构。"""

    step_order: int = Field(..., ge=1, description="步骤顺序")
    name: str = Field(..., min_length=1, max_length=128, description="步骤名称")
    approver_type: ApproverType = Field(..., description="审批人选择方式")
    approver_value: str = Field(..., min_length=1, max_length=128, description="审批人、角色或表达式")
    mode: ApprovalStepMode = Field(default=ApprovalStepMode.ANY, description="会签/或签模式")
    timeout_hours: int | None = Field(default=None, ge=1, le=720, description="超时小时数")
    escalate_to: str | None = Field(default=None, max_length=128, description="超时升级对象")


class ApprovalTemplateCreateRequest(BaseModel):
    """审批模板创建结构。"""

    enterprise_id: int | None = Field(default=1, description="企业 ID")
    name: str = Field(..., min_length=1, max_length=128, description="模板名称")
    business_type: str = Field(..., min_length=1, max_length=128, description="业务类型或动作类型")
    description: str | None = Field(default=None, description="模板说明")
    min_amount: float | None = Field(default=None, ge=0, description="适用最小金额，含边界")
    max_amount: float | None = Field(default=None, gt=0, description="适用最大金额，不含边界")
    status: ApprovalTemplateStatus = Field(default=ApprovalTemplateStatus.ENABLED, description="模板状态")
    is_default: bool = Field(default=False, description="是否默认模板")
    steps: list[ApprovalStepCreateRequest] = Field(..., min_length=1, description="审批步骤")

    @model_validator(mode="after")
    def validate_amount_range(self) -> "ApprovalTemplateCreateRequest":
        """金额区间必须符合企业审批阈值常识。"""
        if self.min_amount is not None and self.max_amount is not None and self.min_amount >= self.max_amount:
            raise ValueError("min_amount 必须小于 max_amount。")
        return self


class ApprovalTemplateUpdateRequest(BaseModel):
    """审批模板更新结构。"""

    name: str | None = Field(default=None, min_length=1, max_length=128, description="模板名称")
    description: str | None = Field(default=None, description="模板说明")
    min_amount: float | None = Field(default=None, ge=0, description="适用最小金额")
    max_amount: float | None = Field(default=None, gt=0, description="适用最大金额")
    status: ApprovalTemplateStatus | None = Field(default=None, description="模板状态")
    is_default: bool | None = Field(default=None, description="是否默认模板")


class ApprovalStepRead(ORMModel):
    """审批模板步骤响应结构。"""

    id: int = Field(..., description="步骤 ID")
    template_id: int = Field(..., description="模板 ID")
    step_order: int = Field(..., description="步骤顺序")
    name: str = Field(..., description="步骤名称")
    approver_type: ApproverType = Field(..., description="审批人选择方式")
    approver_value: str = Field(..., description="审批人、角色或表达式")
    mode: ApprovalStepMode = Field(..., description="会签/或签模式")
    timeout_hours: int | None = Field(default=None, description="超时小时数")
    escalate_to: str | None = Field(default=None, description="超时升级对象")
    created_at: datetime = Field(..., description="创建时间")


class ApprovalTemplateRead(ORMModel):
    """审批模板响应结构。"""

    id: int = Field(..., description="模板 ID")
    enterprise_id: int | None = Field(default=None, description="企业 ID")
    name: str = Field(..., description="模板名称")
    business_type: str = Field(..., description="业务类型")
    description: str | None = Field(default=None, description="模板说明")
    min_amount: float | None = Field(default=None, description="适用最小金额")
    max_amount: float | None = Field(default=None, description="适用最大金额")
    status: ApprovalTemplateStatus = Field(..., description="模板状态")
    is_default: bool = Field(..., description="是否默认模板")
    steps: list[ApprovalStepRead] = Field(default_factory=list, description="审批步骤")
    created_at: datetime = Field(..., description="创建时间")


class ApprovalTransferRequest(BaseModel):
    """审批转交请求。"""

    actor_name: str = Field(..., min_length=1, max_length=128, description="操作人")
    to_approver: str = Field(..., min_length=1, max_length=128, description="转交对象")
    comment: str = Field(default="", max_length=512, description="转交说明")


class ApprovalWithdrawRequest(BaseModel):
    """审批撤回请求。"""

    actor_name: str = Field(..., min_length=1, max_length=128, description="操作人")
    comment: str = Field(default="", max_length=512, description="撤回说明")


class ApprovalInstanceStepRead(ORMModel):
    """审批实例步骤响应结构。"""

    id: int = Field(..., description="实例步骤 ID")
    step_order: int = Field(..., description="步骤顺序")
    name: str = Field(..., description="步骤名称")
    approver_type: ApproverType = Field(..., description="审批人选择方式")
    approver_value: str = Field(..., description="审批人、角色或表达式")
    assigned_to: str | None = Field(default=None, description="当前处理人或角色")
    mode: ApprovalStepMode = Field(..., description="会签/或签模式")
    status: ApprovalStepStatus = Field(..., description="步骤状态")
    timeout_hours: int | None = Field(default=None, description="超时小时数")
    escalate_to: str | None = Field(default=None, description="超时升级对象")
    comment: str | None = Field(default=None, description="审批意见")


class ApprovalActionRead(ORMModel):
    """审批动作响应结构。"""

    id: int = Field(..., description="动作 ID")
    actor_name: str = Field(..., description="操作人")
    action: ApprovalActionType = Field(..., description="动作类型")
    comment: str | None = Field(default=None, description="操作意见")
    from_approver: str | None = Field(default=None, description="转交前对象")
    to_approver: str | None = Field(default=None, description="转交后对象")
    created_at: datetime = Field(..., description="创建时间")


class ApprovalInstanceRead(ORMModel):
    """审批实例响应结构。"""

    id: int = Field(..., description="实例 ID")
    template_id: int | None = Field(default=None, description="模板 ID")
    approval_id: int | None = Field(default=None, description="兼容审批 ID")
    business_type: str = Field(..., description="业务类型")
    business_id: str | None = Field(default=None, description="业务对象 ID")
    title: str = Field(..., description="审批标题")
    status: ApprovalInstanceStatus = Field(..., description="实例状态")
    current_step_order: int | None = Field(default=None, description="当前步骤")
    steps: list[ApprovalInstanceStepRead] = Field(default_factory=list, description="实例步骤")
    actions: list[ApprovalActionRead] = Field(default_factory=list, description="审批动作")
    created_at: datetime = Field(..., description="创建时间")
