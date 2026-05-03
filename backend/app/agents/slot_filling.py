import re
from dataclasses import dataclass, field
from typing import Any

from app.workflows.meeting_to_tasks import generate_task_drafts
from app.workflows.purchase_request import generate_purchase_request
from app.workflows.quality_issue import generate_quality_issue_ticket
from app.workflows.sop_definitions import SOPDefinition, SlotDefinition


@dataclass
class SlotFillResult:
    """补槽检查结果。"""

    effective_message: str
    slot_values: dict[str, Any] = field(default_factory=dict)
    missing_slots: list[SlotDefinition] = field(default_factory=list)

    @property
    def missing_fields(self) -> list[dict[str, str]]:
        """输出给 API 和 Trace 的缺失字段。"""
        return [
            {
                "name": slot.name,
                "label": slot.label,
                "question": slot.question,
            }
            for slot in self.missing_slots
        ]


def build_effective_message(message: str, context: dict[str, Any] | None = None) -> str:
    """合并多轮信息。

    前端或外部系统可把上一轮待补充任务放在 context 里。当前用户输入会作为补充信息
    拼接进去，从而支持轻量多轮补槽。
    """
    context = context or {}
    previous_message = (
        context.get("active_message")
        or context.get("source_text")
        or context.get("previous_message")
        or context.get("message")
    )
    if previous_message and previous_message != message:
        return f"{previous_message}\n补充信息：{message}"
    return message


def fill_slots(sop: SOPDefinition | None, message: str, context: dict[str, Any] | None = None) -> SlotFillResult:
    """根据 SOP 检查必填字段是否齐全。"""
    effective_message = build_effective_message(message, context)
    if sop is None:
        return SlotFillResult(effective_message=effective_message)

    if sop.intent == "purchase_request":
        return _fill_purchase_slots(sop, effective_message)
    if sop.intent == "meeting_to_tasks":
        return _fill_meeting_slots(sop, effective_message)
    if sop.intent == "maintenance_ticket":
        return _fill_maintenance_slots(sop, effective_message)
    if sop.intent == "quality_issue":
        return _fill_quality_slots(sop, effective_message)
    if sop.intent == "weekly_report":
        return _fill_minimum_text_slot(sop, effective_message, "source_text")
    if sop.intent == "knowledge_qa":
        return _fill_minimum_text_slot(sop, effective_message, "query")
    return SlotFillResult(effective_message=effective_message)


def build_clarification_question(sop: SOPDefinition, missing_fields: list[dict[str, str]]) -> str:
    """根据缺失字段生成追问话术。"""
    labels = "、".join(field["label"] for field in missing_fields)
    questions = "；".join(field["question"] for field in missing_fields[:3])
    return f"{sop.name} 信息还不完整，请补充：{labels}。{questions}"


def _fill_purchase_slots(sop: SOPDefinition, text: str) -> SlotFillResult:
    response = generate_purchase_request(text)
    draft = response.purchase_draft
    slot_values = draft.model_dump()
    label_to_slot = {slot.label: slot for slot in sop.slots}
    missing_slots = [
        label_to_slot[label]
        for label in response.missing_fields
        if label in label_to_slot
    ]
    return SlotFillResult(
        effective_message=text,
        slot_values={key: value for key, value in slot_values.items() if value not in {None, ""}},
        missing_slots=missing_slots,
    )


def _fill_meeting_slots(sop: SOPDefinition, text: str) -> SlotFillResult:
    response = generate_task_drafts(text)
    slot_values: dict[str, Any] = {
        "meeting_minutes": text if len(text.strip()) >= 10 else None,
        "action_items": len(response.tasks),
    }
    missing_names: set[str] = set()
    if not slot_values["meeting_minutes"]:
        missing_names.add("meeting_minutes")
    if not response.tasks:
        missing_names.add("action_items")
    return SlotFillResult(
        effective_message=text,
        slot_values={key: value for key, value in slot_values.items() if value},
        missing_slots=_missing_slots_by_name(sop, missing_names),
    )


def _fill_maintenance_slots(sop: SOPDefinition, text: str) -> SlotFillResult:
    equipment_or_line = _extract_equipment_or_line(text)
    abnormal_signal = _extract_abnormal_signal(text)
    missing_names: set[str] = set()
    if not equipment_or_line:
        missing_names.add("equipment_or_line")
    if not abnormal_signal:
        missing_names.add("abnormal_signal")
    if len(text.strip()) < 10:
        missing_names.add("issue_description")
    return SlotFillResult(
        effective_message=text,
        slot_values={
            key: value
            for key, value in {
                "equipment_or_line": equipment_or_line,
                "abnormal_signal": abnormal_signal,
                "issue_description": text.strip() if text.strip() else None,
            }.items()
            if value
        },
        missing_slots=_missing_slots_by_name(sop, missing_names),
    )


def _fill_quality_slots(sop: SOPDefinition, text: str) -> SlotFillResult:
    response = generate_quality_issue_ticket(text)
    draft = response.quality_issue_draft
    missing_names: set[str] = set()
    slot_values: dict[str, Any] = {"issue_description": text.strip() if text.strip() else None}

    if draft is None:
        missing_names.update({"abnormality_signal", "affected_scope"})
    else:
        slot_values["abnormality_signal"] = draft.abnormality_type
        slot_values["affected_scope"] = draft.affected_scope
        if "待质量人员确认" in draft.affected_scope:
            missing_names.add("affected_scope")

    if len(text.strip()) < 10:
        missing_names.add("issue_description")

    return SlotFillResult(
        effective_message=text,
        slot_values={key: value for key, value in slot_values.items() if value},
        missing_slots=_missing_slots_by_name(sop, missing_names),
    )


def _fill_minimum_text_slot(sop: SOPDefinition, text: str, slot_name: str) -> SlotFillResult:
    missing_names = set() if len(text.strip()) >= 3 else {slot_name}
    return SlotFillResult(
        effective_message=text,
        slot_values={slot_name: text.strip()} if text.strip() else {},
        missing_slots=_missing_slots_by_name(sop, missing_names),
    )


def _missing_slots_by_name(sop: SOPDefinition, names: set[str]) -> list[SlotDefinition]:
    """按 SOP 中定义的顺序返回缺失槽位。"""
    return [slot for slot in sop.slots if slot.name in names]


def _extract_equipment_or_line(text: str) -> str | None:
    """抽取设备或产线描述。"""
    patterns = [
        r"([A-Za-z]\d{1,3}\s*产线)",
        r"(生产线\s*[A-Za-z0-9一二三四五六七八九十]+)",
        r"(产线\s*[A-Za-z0-9一二三四五六七八九十]+)",
        r"(空压机|注塑机|输送线|包装机|传感器|设备)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def _extract_abnormal_signal(text: str) -> str | None:
    """抽取异常信号。"""
    patterns = [
        r"([Ee]\d{1,4}\s*报警)",
        r"(报警|故障|停机|停线|停产|暂停|异常|压力波动|读数异常|漏电|冒烟)",
    ]
    signals: list[str] = []
    for pattern in patterns:
        signals.extend(match.group(1) for match in re.finditer(pattern, text))
    return "、".join(dict.fromkeys(signals)) or None

