from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.base import AuditStatus
from app.schemas.common import ORMModel


class AuditLogCreateRequest(BaseModel):
    """创建审计日志请求。"""

    user_id: int | None = Field(default=None, description="用户 ID")
    action: str = Field(..., min_length=1, max_length=128, description="动作名称")
    input: str | None = Field(default=None, description="用户输入")
    output: str | None = Field(default=None, description="模型或工具输出")
    tool_name: str | None = Field(default=None, max_length=128, description="工具名称")
    tool_args: dict[str, Any] | None = Field(default=None, description="工具参数")
    status: AuditStatus = Field(default=AuditStatus.PENDING, description="执行状态")


class AuditLogRead(ORMModel):
    """审计日志响应结构。"""

    id: int = Field(..., description="审计日志 ID")
    user_id: int | None = Field(default=None, description="用户 ID")
    action: str = Field(..., description="动作名称")
    input: str | None = Field(default=None, description="用户输入")
    output: str | None = Field(default=None, description="模型或工具输出")
    tool_name: str | None = Field(default=None, description="工具名称")
    tool_args: dict[str, Any] | None = Field(default=None, description="工具参数")
    status: AuditStatus = Field(..., description="执行状态")
    created_at: datetime = Field(..., description="创建时间")

