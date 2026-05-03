from pydantic import BaseModel, Field

from app.models.base import TaskPriority


class TextWorkflowRequest(BaseModel):
    """文本类办公流程通用请求。"""

    content: str = Field(..., min_length=1, description="用户输入内容")


class TaskDraft(BaseModel):
    """任务草稿。"""

    title: str = Field(..., description="任务标题")
    assignee: str | None = Field(default=None, description="负责人")
    due_date: str | None = Field(default=None, description="截止日期")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="优先级")
    description: str = Field(default="", description="任务描述")


class TicketDraft(BaseModel):
    """工单草稿。"""

    ticket_type: str = Field(default="设备维修", description="工单类型")
    title: str = Field(..., description="工单标题")
    description: str = Field(default="", description="工单描述")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="优先级")
    suggested_action: str | None = Field(default=None, description="建议处理动作")


class QualityIssueTicketDraft(BaseModel):
    """质量异常工单草稿。

    对应制造业常见 NCR/质量异常处理单，但这里只承载草稿信息。
    """

    ticket_type: str = Field(default="质量异常", description="工单类型")
    title: str = Field(..., description="工单标题")
    description: str = Field(default="", description="异常描述")
    priority: TaskPriority = Field(default=TaskPriority.HIGH, description="优先级")
    abnormality_type: str = Field(default="一般质量异常", description="异常类型")
    affected_scope: str = Field(default="待确认", description="影响范围")
    initial_disposition: str = Field(default="", description="初步处置建议")
    required_actions: list[str] = Field(default_factory=list, description="后续必需动作")


class PurchaseDraft(BaseModel):
    """采购申请草稿。"""

    item_name: str | None = Field(default=None, description="物品名称")
    quantity: int | None = Field(default=None, ge=1, description="数量")
    reason: str | None = Field(default=None, description="采购原因")
    budget: float | None = Field(default=None, ge=0, description="预算")
    supplier: str | None = Field(default=None, description="供应商")


class WeeklyReportDraft(BaseModel):
    """项目周报草稿。"""

    progress: str = Field(default="", description="本周进展")
    issues: str = Field(default="", description="本周问题")
    quality_risks: str = Field(default="", description="质量风险")
    equipment_risks: str = Field(default="", description="设备风险")
    purchase_risks: str = Field(default="", description="采购风险")
    next_plan: str = Field(default="", description="下周计划")
    decisions_needed: str = Field(default="", description="需要决策事项")


class MeetingToTasksResponse(BaseModel):
    """会议纪要转任务响应。"""

    source: str = Field(..., description="原始输入")
    tasks: list[TaskDraft] = Field(default_factory=list, description="任务草稿列表")
    workflow_status: str = Field(default="draft_ready", description="流程状态")
    requires_approval: bool = Field(default=True, description="是否需要审批")
    message: str = Field(..., description="说明信息")


class MaintenanceTicketResponse(BaseModel):
    """设备维修工单响应。"""

    source: str = Field(..., description="原始输入")
    ticket_draft: TicketDraft | None = Field(default=None, description="工单草稿")
    workflow_status: str = Field(default="draft_ready", description="流程状态")
    requires_approval: bool = Field(default=True, description="是否需要审批")
    message: str = Field(..., description="说明信息")


class QualityIssueResponse(BaseModel):
    """质量异常处理流程响应。"""

    source: str = Field(..., description="原始输入")
    quality_issue_draft: QualityIssueTicketDraft | None = Field(default=None, description="质量异常工单草稿")
    workflow_status: str = Field(default="draft_ready", description="流程状态")
    requires_approval: bool = Field(default=True, description="是否需要审批")
    message: str = Field(..., description="说明信息")


class PurchaseWorkflowResponse(BaseModel):
    """采购申请流程响应。"""

    source: str = Field(..., description="原始输入")
    purchase_draft: PurchaseDraft | None = Field(default=None, description="采购申请草稿")
    missing_fields: list[str] = Field(default_factory=list, description="缺失字段")
    workflow_status: str = Field(default="draft_ready", description="流程状态")
    requires_approval: bool = Field(default=True, description="是否需要审批")
    message: str = Field(..., description="说明信息")


class WeeklyReportResponse(BaseModel):
    """项目周报响应。"""

    source: str = Field(..., description="原始输入")
    weekly_report: WeeklyReportDraft | None = Field(default=None, description="周报草稿")
    message: str = Field(..., description="说明信息")
