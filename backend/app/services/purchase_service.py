from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.base import PurchaseStatus
from app.models.purchase_request import PurchaseRequest
from app.schemas.purchase_request import PurchaseCreateRequest, PurchaseUpdateRequest
from app.services.approval_guard import ensure_approved_action


def create_purchase_request(
    db: Session,
    data: PurchaseCreateRequest,
    *,
    approved_action: bool = False,
    commit: bool = True,
) -> PurchaseRequest:
    """创建采购申请。

    AI 生成的是草稿；走到这里说明草稿已经经过人工确认。
    因此正式写入采购申请表时，应进入待采购审批状态，而不是继续停留在草稿状态。
    """
    ensure_approved_action("创建采购申请", approved_action)
    purchase_request = PurchaseRequest(**data.model_dump())
    if approved_action:
        purchase_request.status = PurchaseStatus.PENDING_APPROVAL
    db.add(purchase_request)
    if commit:
        db.commit()
        db.refresh(purchase_request)
    else:
        db.flush()
    return purchase_request


def list_purchase_requests(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[PurchaseRequest], int]:
    """分页查询采购申请列表。"""
    total = db.scalar(select(func.count()).select_from(PurchaseRequest)) or 0
    items = db.scalars(
        select(PurchaseRequest)
        .order_by(PurchaseRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(items), total


def get_purchase_request(db: Session, purchase_id: int) -> PurchaseRequest:
    """查询采购申请详情。"""
    purchase_request = db.get(PurchaseRequest, purchase_id)
    if purchase_request is None:
        raise AppException("采购申请不存在。", status_code=status.HTTP_404_NOT_FOUND)
    return purchase_request


def update_purchase_request(
    db: Session,
    purchase_id: int,
    data: PurchaseUpdateRequest,
) -> PurchaseRequest:
    """更新采购申请。"""
    purchase_request = get_purchase_request(db, purchase_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(purchase_request, field, value)
    db.commit()
    db.refresh(purchase_request)
    return purchase_request
