from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import AuthenticatedUser, decode_session_token, get_current_user_optional
from app.core.database import get_db
from app.models.approval_instance import ApprovalInstance
from app.schemas.approval import ApprovalDecisionRequest, ApprovalRead
from app.schemas.approval_template import ApprovalInstanceRead
from app.schemas.mobile_approval import MobileApprovalDecisionResponse, MobileApprovalDetail
from app.services.approval_service import approve_approval, get_approval, reject_approval

router = APIRouter()


@router.get("/{approval_id}", summary="获取移动审批详情")
def get_mobile_approval(
    approval_id: int,
    token: str | None = Query(default=None, description="通知链接携带的移动审批签名 token"),
    current_user: AuthenticatedUser = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> MobileApprovalDetail:
    """H5 审批页读取审批详情。"""
    _verify_mobile_approval_access(approval_id, token=token, current_user=current_user)
    approval = get_approval(db, approval_id)
    instance = db.scalars(
        select(ApprovalInstance)
        .where(ApprovalInstance.approval_id == approval_id)
        .options(
            selectinload(ApprovalInstance.steps),
            selectinload(ApprovalInstance.actions),
        )
        .order_by(ApprovalInstance.id.desc())
        .limit(1)
    ).first()
    return MobileApprovalDetail(
        approval=ApprovalRead.model_validate(approval),
        instance=ApprovalInstanceRead.model_validate(instance) if instance is not None else None,
        message="移动审批详情查询成功。",
    )


@router.post("/{approval_id}/approve", summary="移动端批准审批")
def approve_mobile_approval(
    approval_id: int,
    request: ApprovalDecisionRequest,
    token: str | None = Query(default=None, description="通知链接携带的移动审批签名 token"),
    current_user: AuthenticatedUser = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> MobileApprovalDecisionResponse:
    """H5 审批页批准待处理动作。"""
    _verify_mobile_approval_access(approval_id, token=token, current_user=current_user)
    approval = approve_approval(db, approval_id, request)
    return MobileApprovalDecisionResponse(
        approval=ApprovalRead.model_validate(approval),
        message="审批已批准，系统已按审批引擎继续流转。",
    )


@router.post("/{approval_id}/reject", summary="移动端拒绝审批")
def reject_mobile_approval(
    approval_id: int,
    request: ApprovalDecisionRequest,
    token: str | None = Query(default=None, description="通知链接携带的移动审批签名 token"),
    current_user: AuthenticatedUser = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> MobileApprovalDecisionResponse:
    """H5 审批页拒绝待处理动作。"""
    _verify_mobile_approval_access(approval_id, token=token, current_user=current_user)
    approval = reject_approval(db, approval_id, request)
    return MobileApprovalDecisionResponse(
        approval=ApprovalRead.model_validate(approval),
        message="审批已拒绝，业务动作不会执行。",
    )


def _verify_mobile_approval_access(
    approval_id: int,
    *,
    token: str | None,
    current_user: AuthenticatedUser,
) -> None:
    """校验移动审批访问权限。

    企业通知里的 H5 链接必须带签名 token，避免任何人猜到审批 ID 后直接操作。
    本地调试和后台页面仍允许管理员/主管登录态访问，方便演示与问题排查。
    """
    role_codes = set(current_user.effective_role_codes)
    if current_user.is_admin or role_codes.intersection({"admin", "manager"}):
        return
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="移动审批链接缺少签名 token，请从通知消息中的链接进入。",
        )

    payload = decode_session_token(token)
    if not _is_valid_mobile_payload(payload, approval_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="移动审批 token 与当前审批不匹配。",
        )


def _is_valid_mobile_payload(payload: dict[str, Any], approval_id: int) -> bool:
    """判断 token 是否专用于当前审批。"""
    return payload.get("purpose") == "mobile_approval" and str(payload.get("approval_id")) == str(approval_id)
