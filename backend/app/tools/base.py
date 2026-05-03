from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


ToolHandler = Callable[..., "ToolResult"]


class RiskLevel(StrEnum):
    """工具或业务动作的风险等级。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class ActionRiskPolicy:
    """需要被人工确认的业务动作策略。"""

    action_type: str
    display_name: str
    risk_level: RiskLevel
    requires_approval: bool
    approval_reason: str


# 这里定义的是“真正执行业务写入或外发”的风险，不是“生成草稿”的风险。
# 生成草稿、查询知识库、查询业务列表通常是低风险；写入、删除、外发才需要确认。
ACTION_RISK_POLICIES: dict[str, ActionRiskPolicy] = {
    "search_knowledge_base": ActionRiskPolicy(
        action_type="search_knowledge_base",
        display_name="查询知识库",
        risk_level=RiskLevel.LOW,
        requires_approval=False,
        approval_reason="只读取企业知识库内容，不修改业务数据。",
    ),
    "build_notification_draft": ActionRiskPolicy(
        action_type="build_notification_draft",
        display_name="生成通知草稿",
        risk_level=RiskLevel.LOW,
        requires_approval=False,
        approval_reason="只生成草稿，不真实发送。",
    ),
    "create_task": ActionRiskPolicy(
        action_type="create_task",
        display_name="创建单条任务",
        risk_level=RiskLevel.MEDIUM,
        requires_approval=True,
        approval_reason="会写入任务系统，影响后续人员安排，需要人工确认。",
    ),
    "create_tasks": ActionRiskPolicy(
        action_type="create_tasks",
        display_name="批量创建任务",
        risk_level=RiskLevel.MEDIUM,
        requires_approval=True,
        approval_reason="会批量写入任务系统，影响多人工作安排，需要人工确认。",
    ),
    "update_task_status": ActionRiskPolicy(
        action_type="update_task_status",
        display_name="修改任务状态",
        risk_level=RiskLevel.MEDIUM,
        requires_approval=True,
        approval_reason="会改变任务执行状态，需要保留人工判断。",
    ),
    "create_maintenance_ticket": ActionRiskPolicy(
        action_type="create_maintenance_ticket",
        display_name="提交维修工单",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        approval_reason="会形成正式维修工单，可能影响生产排程和设备维修资源，需要人工确认。",
    ),
    "create_quality_issue_ticket": ActionRiskPolicy(
        action_type="create_quality_issue_ticket",
        display_name="提交质量异常工单",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        approval_reason="会形成正式质量异常记录，可能影响批次放行、返工和客户交付，需要质量负责人确认。",
    ),
    "create_purchase_request": ActionRiskPolicy(
        action_type="create_purchase_request",
        display_name="提交采购申请",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        approval_reason="会形成采购申请并占用预算，需要人工确认。",
    ),
    "send_notification": ActionRiskPolicy(
        action_type="send_notification",
        display_name="发送通知",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        approval_reason="会向外部或内部人员真实发送信息，需要人工确认。",
    ),
    "delete_document": ActionRiskPolicy(
        action_type="delete_document",
        display_name="删除知识库文档",
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        approval_reason="会删除企业知识库资料，可能影响后续检索和审计，需要人工确认。",
    ),
}


@dataclass(slots=True)
class ToolResult:
    """工具执行结果。

    requires_approval 表示结果中携带的后续业务动作需要人工确认。
    例如“生成采购草稿”本身是低风险，但草稿里的“提交采购申请”需要审批。
    """

    tool_name: str
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    approval_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentTool:
    """Agent 工具定义。risk_level 描述工具本身的风险。"""

    name: str
    description: str
    handler: ToolHandler
    requires_approval: bool = False
    risk_level: RiskLevel | str = RiskLevel.LOW

    def __post_init__(self) -> None:
        self.risk_level = RiskLevel(self.risk_level)

    def invoke(self, **kwargs: Any) -> ToolResult:
        """执行工具。"""
        result = self.handler(**kwargs)
        if self.requires_approval and not result.requires_approval:
            result.requires_approval = True
        return result


def classify_action_risk(
    action_type: str,
    action_payload: dict[str, Any] | None = None,
) -> ActionRiskPolicy:
    """根据动作类型和参数判断风险等级。"""
    action_payload = action_payload or {}

    if action_type == "create_purchase_request":
        budget = action_payload.get("budget")
        if isinstance(budget, int | float) and budget < 50000:
            return ActionRiskPolicy(
                action_type=action_type,
                display_name="提交采购申请",
                risk_level=RiskLevel.MEDIUM,
                requires_approval=True,
                approval_reason="采购申请会占用预算并形成业务记录，低于 5 万元仍需要人工确认。",
            )

    return ACTION_RISK_POLICIES.get(
        action_type,
        ActionRiskPolicy(
            action_type=action_type,
            display_name=action_type,
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_reason="未知业务动作默认按高风险处理，避免 Agent 自动执行不可审计操作。",
        ),
    )


def requires_human_approval(
    action_type: str,
    action_payload: dict[str, Any] | None = None,
) -> bool:
    """判断某个业务动作是否需要人工审批。"""
    return classify_action_risk(action_type, action_payload).requires_approval


def approval_required_result(
    *,
    tool_name: str,
    message: str,
    action_type: str,
    action_payload: dict[str, Any],
    data: dict[str, Any] | None = None,
) -> ToolResult:
    """构造携带待审批业务动作的工具结果。"""
    risk_policy = classify_action_risk(action_type, action_payload)
    return ToolResult(
        tool_name=tool_name,
        success=True,
        message=message,
        data=data or {},
        requires_approval=True,
        approval_payload={
            "action_type": action_type,
            "action_payload": action_payload,
            "display_name": risk_policy.display_name,
            "risk_level": risk_policy.risk_level.value,
            "approval_reason": risk_policy.approval_reason,
        },
    )
