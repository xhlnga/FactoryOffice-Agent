from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreateRequest


def create_audit_log(db: Session, data: AuditLogCreateRequest, *, commit: bool = True) -> AuditLog:
    """写入审计日志。"""
    audit_log = AuditLog(**data.model_dump())
    db.add(audit_log)
    if commit:
        db.commit()
        db.refresh(audit_log)
    else:
        db.flush()
    return audit_log


def list_audit_logs(
    db: Session,
    *,
    user_id: int | None = None,
    action: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[AuditLog], int]:
    """分页查询审计日志。"""
    query = select(AuditLog)
    count_query = select(func.count()).select_from(AuditLog)

    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)

    if action is not None:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(items), total


def get_audit_log(db: Session, log_id: int) -> AuditLog:
    """查询审计日志详情。"""
    audit_log = db.get(AuditLog, log_id)
    if audit_log is None:
        raise AppException("审计日志不存在。", status_code=status.HTTP_404_NOT_FOUND)
    return audit_log
