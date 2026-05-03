from typing import Any

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """通用 Agent 对话请求。"""

    message: str = Field(..., min_length=1, description="用户输入")
    user_id: int | None = Field(default=None, description="用户 ID")
    context: dict[str, Any] = Field(default_factory=dict, description="上下文信息")


class ToolCallPreview(BaseModel):
    """工具调用预览。"""

    tool_name: str = Field(..., description="工具名称")
    tool_args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    requires_approval: bool = Field(default=False, description="是否需要审批")


class AgentChatResponse(BaseModel):
    """通用 Agent 对话响应。"""

    message: str = Field(..., description="用户输入")
    intent: str = Field(..., description="识别出的意图")
    answer: str = Field(..., description="回答内容")
    tool_calls: list[ToolCallPreview] = Field(default_factory=list, description="工具调用预览")
    requires_approval: bool = Field(default=False, description="是否需要审批")

