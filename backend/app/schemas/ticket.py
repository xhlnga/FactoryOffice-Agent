from datetime import datetime

from pydantic import BaseModel, Field

from app.models.base import TaskPriority, TicketStatus
from app.schemas.common import ORMModel


class TicketBase(BaseModel):
    """工单基础字段。"""

    ticket_type: str = Field(default="设备维修", max_length=64, description="工单类型")
    title: str = Field(..., min_length=1, max_length=255, description="工单标题")
    description: str = Field(default="", description="工单描述")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="优先级")


class TicketCreateRequest(TicketBase):
    """创建工单请求。"""

    created_by: int | None = Field(default=None, description="创建人 ID")


class TicketUpdateRequest(BaseModel):
    """更新工单请求。"""

    title: str | None = Field(default=None, min_length=1, max_length=255, description="工单标题")
    description: str | None = Field(default=None, description="工单描述")
    priority: TaskPriority | None = Field(default=None, description="优先级")
    status: TicketStatus | None = Field(default=None, description="工单状态")


class TicketRead(TicketBase, ORMModel):
    """工单响应结构。"""

    id: int = Field(..., description="工单 ID")
    status: TicketStatus = Field(..., description="工单状态")
    created_by: int | None = Field(default=None, description="创建人 ID")
    created_at: datetime = Field(..., description="创建时间")

