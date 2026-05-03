from typing import Literal


AgentTaskStatus = Literal[
    "new",
    "collecting_info",
    "waiting_approval",
    "approved",
    "executing",
    "completed",
    "failed",
    "cancelled",
    "suspended",
]


TERMINAL_STATUSES: set[AgentTaskStatus] = {
    "completed",
    "failed",
    "cancelled",
}


def infer_task_status(
    *,
    has_sop: bool,
    missing_fields: list[dict],
    requires_approval: bool,
    has_tool_calls: bool,
    error: str | None = None,
) -> AgentTaskStatus:
    """根据当前 Agent 阶段推断任务状态。

    企业流程 Agent 不能只返回一句话。它需要说明业务动作现在处在哪个阶段：
    信息收集中、等待审批、准备执行，还是已经失败。
    """
    if error:
        return "failed"
    if not has_sop:
        return "new"
    if missing_fields:
        return "collecting_info"
    if requires_approval:
        return "waiting_approval"
    if has_tool_calls:
        return "completed"
    return "new"

