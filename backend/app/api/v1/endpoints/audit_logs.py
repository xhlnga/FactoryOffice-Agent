from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, require_role
from app.schemas.audit_log import AuditLogRead
from app.services.audit_service import get_audit_log as get_audit_log_record
from app.services.audit_service import list_audit_logs as list_audit_log_records

router = APIRouter()


@router.get("", summary="获取审计日志列表")
def list_audit_logs(
    user_id: int | None = None,
    action: str | None = None,
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 50,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """查询 Agent 执行、工具调用和人工审批的审计记录。"""
    items, total = list_audit_log_records(
        db,
        user_id=user_id,
        action=action,
        offset=offset,
        limit=limit,
    )
    return {
        "filters": {
            "user_id": user_id,
            "action": action,
            "offset": offset,
            "limit": limit,
        },
        "items": [AuditLogRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "审计日志列表查询成功。",
    }


@router.get("/{log_id}", summary="获取审计日志详情")
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """查询单条审计日志详情。"""
    audit_log = get_audit_log_record(db, log_id)
    return {
        "audit_log": AuditLogRead.model_validate(audit_log).model_dump(mode="json"),
        "message": "审计日志详情查询成功。",
    }
