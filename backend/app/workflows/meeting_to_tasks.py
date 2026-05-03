import re

from app.models.base import TaskPriority
from app.schemas.workflow import MeetingToTasksResponse, TaskDraft


DUE_DATE_PATTERN = re.compile(
    r"(下周[一二三四五六日天]?(?:前)?|本周[一二三四五六日天]?(?:前)?|周[一二三四五六日天](?:前)?|"
    r"明天(?:前)?|后天(?:前)?|今天(?:前)?|月底|本月底|下月底)"
)


def generate_task_drafts(meeting_notes: str) -> MeetingToTasksResponse:
    """从会议纪要中生成任务草稿。

    当前使用规则抽取，后续可替换为 LLM 结构化抽取。
    """
    tasks: list[TaskDraft] = []
    for sentence in _split_sentences(meeting_notes):
        if not _looks_like_task(sentence):
            continue

        tasks.append(
            TaskDraft(
                title=_extract_title(sentence),
                assignee=_extract_assignee(sentence),
                due_date=_extract_due_date(sentence),
                priority=_infer_priority(sentence),
                description=sentence,
            )
        )

    if not tasks:
        return MeetingToTasksResponse(
            source=meeting_notes,
            tasks=[],
            workflow_status="needs_clarification",
            requires_approval=False,
            message="未识别出明确任务，请补充会议纪要正文、负责人、事项或截止时间。",
        )

    return MeetingToTasksResponse(
        source=meeting_notes,
        tasks=tasks,
        workflow_status="draft_ready",
        requires_approval=True,
        message="已生成任务草稿，批量创建任务前需要人工确认。",
    )


def _split_sentences(text: str) -> list[str]:
    """把会议纪要切成候选事项。"""
    parts = re.split(r"[；;\n。]+", text)
    return [part.strip(" ，,：:") for part in parts if part.strip()]


def _looks_like_task(sentence: str) -> bool:
    """判断一句话是否像任务事项。"""
    if _looks_like_user_command(sentence):
        return False
    keywords = ["负责", "完成", "跟进", "确认", "联系", "提交", "输出", "整理", "审批", "检查"]
    return any(keyword in sentence for keyword in keywords)


def _looks_like_user_command(sentence: str) -> bool:
    """排除“请帮我整理会议纪要”这类用户操作指令。"""
    command_prefixes = ["帮我", "请帮我", "请你", "麻烦"]
    if not any(sentence.startswith(prefix) for prefix in command_prefixes):
        return False
    return any(keyword in sentence for keyword in ["会议纪要", "会议记录", "整理成任务", "生成任务"])


def _extract_title(sentence: str) -> str:
    """生成任务标题。"""
    cleaned = _business_part(sentence)
    assignee = _extract_assignee(sentence)
    if assignee:
        cleaned = re.sub(rf"^{re.escape(assignee)}", "", cleaned)
    cleaned = DUE_DATE_PATTERN.sub("", cleaned, count=1)
    cleaned = re.sub(r"^(负责|需|需要|要|前|完成|联系)", "", cleaned)
    return cleaned.strip(" ，,：:；;")[:80] or sentence[:80]


def _extract_assignee(sentence: str) -> str | None:
    """抽取负责人。"""
    text = _business_part(sentence)
    match = re.search(
        r"(?P<assignee>[\u4e00-\u9fffA-Za-z]{1,10}(?:工|经理|主管|主任|专员))"
        r"(?=负责|需|需要|要|今天|明天|后天|本周|下周|周[一二三四五六日天]|完成|联系|确认|提交|检查)",
        text,
    )
    if match:
        return match.group("assignee")

    match = re.search(r"(?P<assignee>[\u4e00-\u9fffA-Za-z]{2,8})(负责|需|需要|要)", text)
    if match:
        return match.group("assignee")
    return None


def _extract_due_date(sentence: str) -> str | None:
    """抽取截止时间文本。"""
    match = DUE_DATE_PATTERN.search(_business_part(sentence))
    return match.group(0) if match else None


def _infer_priority(sentence: str) -> TaskPriority:
    """根据关键词推断优先级。"""
    if any(keyword in sentence for keyword in ["紧急", "立即", "停线", "停产", "高风险"]):
        return TaskPriority.URGENT
    if any(keyword in sentence for keyword in ["审批", "周五前", "本周", "必须"]):
        return TaskPriority.HIGH
    return TaskPriority.MEDIUM


def _business_part(sentence: str) -> str:
    """去掉会议描述前缀，保留真正任务内容。"""
    cleaned = sentence.strip(" ，,：:")
    cleaned = re.sub(r"^(今天|本次|此次)?会议(确定|要求|明确|决定)?[:：，,\s]*", "", cleaned)
    cleaned = re.sub(r"^(会上|会后|要求|确定|决定|明确)[:：，,\s]*", "", cleaned)
    return cleaned
