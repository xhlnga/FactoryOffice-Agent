from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, require_role
from app.models.base import ApprovalStatus
from app.schemas.approval import ApprovalDecisionRequest, ApprovalRead
from app.schemas.approval_template import ApprovalTransferRequest, ApprovalWithdrawRequest
from app.services.approval_service import (
    approve_approval,
    list_approvals,
    list_pending_approvals,
    reject_approval,
    transfer_approval,
    withdraw_approval,
)

router = APIRouter()


@router.get("", summary="获取审批列表")
def get_approvals(
    status: ApprovalStatus | None = None,
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """查询审批列表，可按状态过滤。"""
    items, total = list_approvals(db, approval_status=status, offset=offset, limit=limit)
    return {
        "status_filter": status,
        "items": [ApprovalRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "审批列表查询成功。",
    }


@router.get("/pending", summary="获取待审批列表")
def get_pending_approvals(
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """查询待人工确认的动作。"""
    items, total = list_pending_approvals(db, offset=offset, limit=limit)
    return {
        "items": [ApprovalRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "待审批列表查询成功。",
    }


@router.post("/{approval_id}/approve", summary="批准审批")
def approve(
    approval_id: int,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """批准待执行动作，后续由服务层触发工具执行。"""
    approval = approve_approval(db, approval_id, request)
    message = "审批已批准，业务动作已执行并写入审计日志。"
    if approval.status == ApprovalStatus.PENDING:
        message = "当前审批步骤已批准，仍需后续审批步骤完成后再执行业务动作。"
    return {
        "approval": ApprovalRead.model_validate(approval).model_dump(mode="json"),
        "message": message,
    }


@router.post("/{approval_id}/reject", summary="拒绝审批")
def reject(
    approval_id: int,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """拒绝待执行动作，并记录审批意见。"""
    approval = reject_approval(db, approval_id, request)
    return {
        "approval": ApprovalRead.model_validate(approval).model_dump(mode="json"),
        "message": "审批已拒绝，业务动作不会执行。",
    }


@router.post("/{approval_id}/transfer", summary="转交审批")
def transfer(
    approval_id: int,
    request: ApprovalTransferRequest,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """转交当前审批步骤。"""
    approval = transfer_approval(db, approval_id, request)
    return {
        "approval": ApprovalRead.model_validate(approval).model_dump(mode="json"),
        "message": "审批已转交。",
    }


@router.post("/{approval_id}/withdraw", summary="撤回审批")
def withdraw(
    approval_id: int,
    request: ApprovalWithdrawRequest,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """撤回待审批动作，业务动作不会执行。"""
    approval = withdraw_approval(db, approval_id, request)
    return {
        "approval": ApprovalRead.model_validate(approval).model_dump(mode="json"),
        "message": "审批已撤回，业务动作不会执行。",
    }
