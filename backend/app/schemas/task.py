from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.base import TaskPriority, TaskStatus
from app.schemas.common import ORMModel


class TaskBase(BaseModel):
    """任务基础字段。"""

    title: str = Field(..., min_length=1, max_length=255, description="任务标题")
    description: str = Field(default="", description="任务描述")
    assignee: str | None = Field(default=None, max_length=128, description="负责人")
    due_date: date | None = Field(default=None, description="截止日期")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="优先级")
    source: str | None = Field(default=None, max_length=128, description="任务来源")


class TaskCreateRequest(TaskBase):
    """创建任务请求。"""


class TaskUpdateRequest(BaseModel):
    """更新任务请求。"""

    title: str | None = Field(default=None, min_length=1, max_length=255, description="任务标题")
    description: str | None = Field(default=None, description="任务描述")
    assignee: str | None = Field(default=None, max_length=128, description="负责人")
    due_date: date | None = Field(default=None, description="截止日期")
    priority: TaskPriority | None = Field(default=None, description="优先级")
    status: TaskStatus | None = Field(default=None, description="任务状态")


class TaskRead(TaskBase, ORMModel):
    """任务响应结构。"""

    id: int = Field(..., description="任务 ID")
    status: TaskStatus = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")

