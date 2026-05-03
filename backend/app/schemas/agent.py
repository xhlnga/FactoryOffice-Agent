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


class AgentTraceStep(BaseModel):
    """Agent 执行轨迹。"""

    step: str = Field(..., description="执行步骤")
    status: str = Field(..., description="步骤状态")
    detail: dict[str, Any] = Field(default_factory=dict, description="步骤详情")


class MissingField(BaseModel):
    """SOP 缺失字段。"""

    name: str = Field(..., description="字段名")
    label: str = Field(..., description="业务展示名")
    question: str = Field(..., description="补充提示")


class AgentChatResponse(BaseModel):
    """通用 Agent 对话响应。"""

    message: str = Field(..., description="用户输入")
    intent: str = Field(..., description="识别出的意图")
    sop_id: str | None = Field(default=None, description="命中的 SOP ID")
    sop_name: str | None = Field(default=None, description="命中的 SOP 名称")
    task_status: str | None = Field(default=None, description="当前任务状态")
    answer: str = Field(..., description="回答内容")
    slot_values: dict[str, Any] = Field(default_factory=dict, description="已识别字段")
    missing_fields: list[MissingField] = Field(default_factory=list, description="缺失字段")
    next_question: str | None = Field(default=None, description="下一步追问")
    tool_calls: list[ToolCallPreview] = Field(default_factory=list, description="工具调用预览")
    requires_approval: bool = Field(default=False, description="是否需要审批")
    trace: list[AgentTraceStep] = Field(default_factory=list, description="Agent 执行轨迹")
