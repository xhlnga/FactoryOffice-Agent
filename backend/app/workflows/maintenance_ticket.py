from app.models.base import TaskPriority
from app.schemas.workflow import MaintenanceTicketResponse, TicketDraft


def generate_maintenance_ticket(issue_description: str) -> MaintenanceTicketResponse:
    """根据设备异常描述生成维修工单草稿。"""
    cleaned = issue_description.strip()
    if not _has_maintenance_signal(cleaned):
        return MaintenanceTicketResponse(
            source=issue_description,
            ticket_draft=None,
            workflow_status="needs_clarification",
            requires_approval=False,
            message="未识别到明确设备异常，请补充设备名称、报警代码、故障现象或现场影响。",
        )

    priority = infer_maintenance_priority(issue_description)
    ticket = TicketDraft(
        ticket_type="设备维修",
        title=build_ticket_title(issue_description),
        description=issue_description,
        priority=priority,
        suggested_action=build_suggested_action(issue_description),
    )
    return MaintenanceTicketResponse(
        source=issue_description,
        ticket_draft=ticket,
        requires_approval=True,
        message="已生成维修工单草稿，提交工单前需要人工确认。",
    )


def _has_maintenance_signal(text: str) -> bool:
    """判断输入是否像设备维修工单，而不是普通采购、会议或制度咨询。"""
    issue_keywords = ["故障", "报警", "停机", "停线", "停产", "暂停", "异常", "漏电", "冒烟", "无法启动"]
    equipment_keywords = ["空压机", "注塑机", "输送线", "包装机", "传感器", "生产线", "设备", "电机", "泵", "阀"]
    return any(keyword in text for keyword in issue_keywords) and any(
        keyword in text for keyword in equipment_keywords
    )


def infer_maintenance_priority(text: str) -> TaskPriority:
    """推断维修工单优先级。"""
    if any(keyword in text for keyword in ["停线", "停产", "暂停", "冒烟", "漏电", "安全"]):
        return TaskPriority.URGENT
    if any(keyword in text for keyword in ["报警", "异常", "压力", "温度", "传感器"]):
        return TaskPriority.HIGH
    return TaskPriority.MEDIUM


def build_ticket_title(text: str) -> str:
    """生成工单标题。"""
    equipment = "设备"
    for keyword in ["空压机", "注塑机", "输送线", "包装机", "传感器", "生产线"]:
        if keyword in text:
            equipment = keyword
            break

    if "E07" in text.upper():
        return f"{equipment} E07 报警处理"
    if "报警" in text:
        return f"{equipment} 报警处理"
    return f"{equipment} 异常处理"


def build_suggested_action(text: str) -> str:
    """生成建议处理动作。"""
    actions = ["确认现场安全状态", "记录设备编号和报警信息"]
    if "压力" in text:
        actions.extend(["检查压力传感器读数", "检查气路和接线", "必要时校验或更换压力传感器"])
    if "温度" in text:
        actions.extend(["检查温度传感器读数", "检查散热和冷却系统"])
    if "停线" in text or "暂停" in text:
        actions.append("评估是否需要通知生产负责人和设备主管")
    return "；".join(actions)
