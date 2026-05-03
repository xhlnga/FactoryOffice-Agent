from sqlalchemy.orm import Session

from app.schemas.task import TaskCreateRequest
from app.services.task_service import create_task, list_tasks
from app.tools.base import AgentTool, RiskLevel, ToolResult, approval_required_result
from app.workflows.meeting_to_tasks import generate_task_drafts


def preview_tasks_from_meeting(source_text: str) -> ToolResult:
    """从会议纪要生成任务草稿，不直接写入数据库。"""
    response = generate_task_drafts(source_text)
    if not response.tasks:
        return ToolResult(
            tool_name="preview_tasks_from_meeting",
            success=True,
            message="未从会议纪要中识别出明确任务，请补充负责人、事项或截止时间。",
            data=response.model_dump(mode="json"),
            requires_approval=False,
        )

    return approval_required_result(
        tool_name="preview_tasks_from_meeting",
        message=f"{response.message} 如需批量创建任务，需要人工确认。",
        action_type="create_tasks",
        action_payload={
            "source": "meeting",
            "source_text": response.source,
            "tasks": [task.model_dump(mode="json") for task in response.tasks],
        },
        data=response.model_dump(mode="json"),
    )


def create_task_record(db: Session, task: TaskCreateRequest) -> ToolResult:
    """执行已审批的任务创建。"""
    record = create_task(db, task, approved_action=True)
    return ToolResult(
        tool_name="create_task",
        success=True,
        message="任务创建成功。",
        data={"task_id": record.id},
    )


def query_tasks(db: Session, offset: int = 0, limit: int = 20) -> ToolResult:
    """查询任务列表。"""
    items, total = list_tasks(db, offset=offset, limit=limit)
    return ToolResult(
        tool_name="query_tasks",
        success=True,
        message="任务列表查询成功。",
        data={
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "status": item.status,
                    "priority": item.priority,
                    "assignee": item.assignee,
                }
                for item in items
            ],
        },
    )


PREVIEW_TASKS_FROM_MEETING_TOOL = AgentTool(
    name="preview_tasks_from_meeting",
    description="根据会议纪要生成任务草稿；真正批量创建任务前需要人工确认。",
    handler=preview_tasks_from_meeting,
    requires_approval=False,
    risk_level=RiskLevel.LOW,
)
