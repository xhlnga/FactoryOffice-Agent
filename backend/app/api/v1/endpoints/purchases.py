from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.approval import ApprovalCreateRequest, ApprovalRead
from app.schemas.purchase_request import PurchaseCreateRequest
from app.schemas.purchase_request import PurchaseRead
from app.services.approval_service import create_approval
from app.services.purchase_service import get_purchase_request
from app.services.purchase_service import list_purchase_requests

router = APIRouter()


@router.get("", summary="获取采购申请列表")
def list_purchases(
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
) -> dict:
    """分页查询采购申请列表。"""
    items, total = list_purchase_requests(db, offset=offset, limit=limit)
    return {
        "items": [PurchaseRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "采购申请列表查询成功。",
    }


@router.post("", summary="创建采购申请")
def create_purchase(request: PurchaseCreateRequest, db: Session = Depends(get_db)) -> dict:
    """创建采购申请属于正式业务动作，先生成待审批记录。"""
    approval = create_approval(
        db,
        ApprovalCreateRequest(
            action_type="create_purchase_request",
            action_payload=request.model_dump(mode="json"),
        ),
    )
    return {
        "approval": ApprovalRead.model_validate(approval).model_dump(mode="json"),
        "requires_approval": True,
        "message": "创建采购申请属于正式业务动作，已创建待审批记录。",
    }


@router.get("/{purchase_id}", summary="获取采购申请详情")
def get_purchase(purchase_id: int, db: Session = Depends(get_db)) -> dict:
    """查询单个采购申请详情。"""
    purchase_request = get_purchase_request(db, purchase_id)
    return {
        "purchase_request": PurchaseRead.model_validate(purchase_request).model_dump(mode="json"),
        "message": "采购申请详情查询成功。",
    }
