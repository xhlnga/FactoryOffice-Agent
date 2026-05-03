from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.approval import ApprovalCreateRequest, ApprovalRead
from app.schemas.task import TaskCreateRequest
from app.schemas.task import TaskRead
from app.services.approval_service import create_approval
from app.services.task_service import get_task as get_task_record
from app.services.task_service import list_tasks as list_task_records

router = APIRouter()


@router.get("", summary="获取任务列表")
def list_tasks(
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
) -> dict:
    """分页查询任务列表。"""
    items, total = list_task_records(db, offset=offset, limit=limit)
    return {
        "items": [TaskRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "任务列表查询成功。",
    }


@router.post("", summary="创建任务")
def create_task(request: TaskCreateRequest, db: Session = Depends(get_db)) -> dict:
    """创建任务属于正式业务动作，先生成待审批记录。"""
    approval = create_approval(
        db,
        ApprovalCreateRequest(
            action_type="create_tasks",
            action_payload={"source": request.source, "tasks": [request.model_dump(mode="json")]},
        ),
    )
    return {
        "approval": ApprovalRead.model_validate(approval).model_dump(mode="json"),
        "requires_approval": True,
        "message": "创建任务属于正式业务动作，已创建待审批记录。",
    }


@router.get("/{task_id}", summary="获取任务详情")
def get_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    """查询单个任务详情。"""
    task = get_task_record(db, task_id)
    return {
        "task": TaskRead.model_validate(task).model_dump(mode="json"),
        "message": "任务详情查询成功。",
    }
