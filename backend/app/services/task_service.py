from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.task import Task
from app.schemas.task import TaskCreateRequest, TaskUpdateRequest
from app.services.approval_guard import ensure_approved_action
from app.services.business_sync_service import sync_task_created


def create_task(
    db: Session,
    data: TaskCreateRequest,
    *,
    approved_action: bool = False,
    commit: bool = True,
) -> Task:
    """创建任务。"""
    ensure_approved_action("创建任务", approved_action)
    task = Task(**data.model_dump())
    db.add(task)
    if commit:
        db.commit()
        db.refresh(task)
        sync_task_created(db, task)
    else:
        db.flush()
    return task


def list_tasks(db: Session, *, offset: int = 0, limit: int = 20) -> tuple[list[Task], int]:
    """分页查询任务列表。"""
    total = db.scalar(select(func.count()).select_from(Task)) or 0
    items = db.scalars(
        select(Task)
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(items), total


def get_task(db: Session, task_id: int) -> Task:
    """查询任务详情。"""
    task = db.get(Task, task_id)
    if task is None:
        raise AppException("任务不存在。", status_code=status.HTTP_404_NOT_FOUND)
    return task


def update_task(db: Session, task_id: int, data: TaskUpdateRequest) -> Task:
    """更新任务。"""
    task = get_task(db, task_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: int, *, approved_action: bool = False) -> None:
    """删除任务。"""
    ensure_approved_action("删除任务", approved_action)
    task = get_task(db, task_id)
    db.delete(task)
    db.commit()
