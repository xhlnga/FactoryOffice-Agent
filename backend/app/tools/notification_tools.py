from app.tools.base import AgentTool, RiskLevel, ToolResult


def build_notification_draft(
    *,
    title: str,
    content: str,
    receiver: str | None = None,
) -> ToolResult:
    """生成通知草稿，不真实发送。"""
    return ToolResult(
        tool_name="build_notification_draft",
        success=True,
        message="通知草稿已生成，当前不会真实发送。",
        data={
            "title": title,
            "content": content,
            "receiver": receiver,
        },
        requires_approval=False,
    )


BUILD_NOTIFICATION_DRAFT_TOOL = AgentTool(
    name="build_notification_draft",
    description="生成通知或邮件草稿，不真实发送。",
    handler=build_notification_draft,
    requires_approval=False,
    risk_level=RiskLevel.LOW,
)
