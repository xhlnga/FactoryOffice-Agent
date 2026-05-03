from dataclasses import dataclass
from typing import Literal


SopApprovalPolicy = Literal["none", "always", "when_complete"]


@dataclass(frozen=True)
class SlotDefinition:
    """SOP 槽位定义。

    槽位用于描述一个企业流程在提交前必须补齐哪些字段。
    """

    name: str
    label: str
    question: str
    required: bool = True


@dataclass(frozen=True)
class SOPDefinition:
    """企业流程 SOP 定义。

    这里不放复杂执行逻辑，只描述流程身份、必填字段、审批策略和对应工具。
    真正的草稿生成仍由 workflows 和 tools 负责。
    """

    sop_id: str
    intent: str
    name: str
    description: str
    slots: tuple[SlotDefinition, ...]
    approval_policy: SopApprovalPolicy
    preview_tool_name: str
    execution_target: str


SOP_DEFINITIONS: dict[str, SOPDefinition] = {
    "knowledge_qa": SOPDefinition(
        sop_id="knowledge_qa",
        intent="knowledge_qa",
        name="知识库问答 SOP",
        description="检索企业制度、SOP、设备手册、质量流程等文档，并返回带来源的回答。",
        slots=(
            SlotDefinition("query", "问题", "请补充要查询的制度、SOP、设备或流程问题。"),
        ),
        approval_policy="none",
        preview_tool_name="search_knowledge_base",
        execution_target="knowledge_search",
    ),
    "meeting_to_tasks": SOPDefinition(
        sop_id="meeting_to_tasks",
        intent="meeting_to_tasks",
        name="会议纪要转任务 SOP",
        description="从会议纪要中提取任务、负责人、截止时间和优先级，批量创建前进入审批。",
        slots=(
            SlotDefinition("meeting_minutes", "会议纪要正文", "请补充会议纪要正文。"),
            SlotDefinition("action_items", "任务事项", "请补充至少一条明确的任务事项、负责人或截止时间。"),
        ),
        approval_policy="when_complete",
        preview_tool_name="preview_tasks_from_meeting",
        execution_target="tasks",
    ),
    "maintenance_ticket": SOPDefinition(
        sop_id="maintenance_ticket",
        intent="maintenance_ticket",
        name="设备维修工单 SOP",
        description="根据设备异常描述生成维修工单草稿，正式提交前必须人工确认。",
        slots=(
            SlotDefinition("equipment_or_line", "设备或产线", "请补充发生异常的设备或产线。"),
            SlotDefinition("abnormal_signal", "异常现象", "请补充报警、故障、停线、压力波动等异常现象。"),
            SlotDefinition("issue_description", "异常描述", "请补充设备异常的现场描述。"),
        ),
        approval_policy="when_complete",
        preview_tool_name="preview_maintenance_ticket",
        execution_target="tickets",
    ),
    "quality_issue": SOPDefinition(
        sop_id="quality_issue",
        intent="quality_issue",
        name="质量异常处理 SOP",
        description="根据质量异常描述生成 NCR/质量异常工单草稿，正式提交前必须人工确认。",
        slots=(
            SlotDefinition("abnormality_signal", "异常现象或检验结果", "请补充质量异常现象或检验结果。"),
            SlotDefinition("affected_scope", "影响范围", "请补充批次、产品、数量或客户影响范围。"),
            SlotDefinition("issue_description", "异常描述", "请补充质量异常的完整描述。"),
        ),
        approval_policy="when_complete",
        preview_tool_name="preview_quality_issue_ticket",
        execution_target="tickets",
    ),
    "purchase_request": SOPDefinition(
        sop_id="purchase_request",
        intent="purchase_request",
        name="采购申请 SOP",
        description="从采购需求中提取物品、数量、用途、预算和供应商，提交前进入审批。",
        slots=(
            SlotDefinition("item_name", "物品名称", "请补充采购物品名称。"),
            SlotDefinition("quantity", "数量", "请补充采购数量和单位。"),
            SlotDefinition("reason", "采购原因", "请补充采购用途或原因。"),
            SlotDefinition("budget", "预算", "请补充预算金额。"),
            SlotDefinition("supplier", "供应商", "请补充供应商或候选供应商。"),
        ),
        approval_policy="when_complete",
        preview_tool_name="preview_purchase_request",
        execution_target="purchase_requests",
    ),
    "weekly_report": SOPDefinition(
        sop_id="weekly_report",
        intent="weekly_report",
        name="项目周报生成 SOP",
        description="根据项目记录生成周报草稿，不直接写入正式业务系统。",
        slots=(
            SlotDefinition("source_text", "项目记录", "请补充本周进展、问题、风险或下周计划。"),
        ),
        approval_policy="none",
        preview_tool_name="generate_weekly_report",
        execution_target="draft_only",
    ),
}


def get_sop_definition(intent: str | None) -> SOPDefinition | None:
    """根据意图获取 SOP 定义。"""
    if not intent:
        return None
    return SOP_DEFINITIONS.get(intent)

