from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppException
from app.schemas.approval import ApprovalCreateRequest, ApprovalRead
from app.schemas.ticket import TicketCreateRequest
from app.schemas.ticket import TicketRead
from app.services.approval_service import create_approval
from app.services.ticket_service import get_ticket as get_ticket_record
from app.services.ticket_service import list_tickets as list_ticket_records

router = APIRouter()

SUPPORTED_TICKET_ACTION_TYPES = {
    "设备维修": "create_maintenance_ticket",
    "质量异常": "create_quality_issue_ticket",
}


@router.get("", summary="获取工单列表")
def list_tickets(
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
) -> dict:
    """分页查询工单列表。"""
    items, total = list_ticket_records(db, offset=offset, limit=limit)
    return {
        "items": [TicketRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "工单列表查询成功。",
    }


@router.post("", summary="创建工单")
def create_ticket(request: TicketCreateRequest, db: Session = Depends(get_db)) -> dict:
    """创建工单属于正式业务动作，先生成待审批记录。"""
    action_type = SUPPORTED_TICKET_ACTION_TYPES.get(request.ticket_type)
    if action_type is None:
        raise AppException(
            "当前演示系统仅支持设备维修和质量异常工单。安全隐患、IT 支持等类型应接入对应专业流程后再开放。",
            status_code=400,
            details={"supported_ticket_types": sorted(SUPPORTED_TICKET_ACTION_TYPES)},
        )
    approval = create_approval(
        db,
        ApprovalCreateRequest(
            action_type=action_type,
            action_payload=request.model_dump(mode="json"),
        ),
    )
    return {
        "approval": ApprovalRead.model_validate(approval).model_dump(mode="json"),
        "requires_approval": True,
        "message": "创建工单属于正式业务动作，已创建待审批记录。",
    }


@router.get("/{ticket_id}", summary="获取工单详情")
def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> dict:
    """查询单个工单详情。"""
    ticket = get_ticket_record(db, ticket_id)
    return {
        "ticket": TicketRead.model_validate(ticket).model_dump(mode="json"),
        "message": "工单详情查询成功。",
    }
