from datetime import datetime

from pydantic import BaseModel, Field

from app.models.base import SLAStatus
from app.schemas.common import ORMModel


class SLAPolicyRead(ORMModel):
    """SLA 策略响应结构。"""

    id: int = Field(..., description="策略 ID")
    enterprise_id: int | None = Field(default=None, description="企业 ID")
    business_type: str = Field(..., description="业务类型")
    priority: str = Field(..., description="优先级")
    response_minutes: int = Field(..., description="响应时限，分钟")
    resolve_minutes: int = Field(..., description="处理时限，分钟")
    remind_before_minutes: int = Field(..., description="提前提醒分钟数")
    escalate_after_minutes: int = Field(..., description="超时后升级分钟数")
    escalate_to_role: str | None = Field(default=None, description="升级到角色")
    enabled: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")


class SLAInstanceRead(ORMModel):
    """SLA 实例响应结构。"""

    id: int = Field(..., description="实例 ID")
    enterprise_id: int | None = Field(default=None, description="企业 ID")
    policy_id: int | None = Field(default=None, description="策略 ID")
    business_type: str = Field(..., description="业务类型")
    business_id: str = Field(..., description="业务对象 ID")
    status: SLAStatus = Field(..., description="SLA 状态")
    response_due_at: datetime | None = Field(default=None, description="响应截止时间")
    deadline_at: datetime | None = Field(default=None, description="处理截止时间")
    first_remind_at: datetime | None = Field(default=None, description="首次提醒时间")
    breached_at: datetime | None = Field(default=None, description="超时时间")
    escalated_at: datetime | None = Field(default=None, description="升级时间")
    resolved_at: datetime | None = Field(default=None, description="关闭时间")
    created_at: datetime = Field(..., description="创建时间")


class SLADefaultPolicyRead(BaseModel):
    """内置 SLA 策略响应结构。"""

    business_type: str
    priority: str
    response_minutes: int
    resolve_minutes: int
    remind_before_minutes: int
    escalate_after_minutes: int
    escalate_to_role: str
