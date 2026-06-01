from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreateRequest, TicketUpdateRequest
from app.services.approval_guard import ensure_approved_action
from app.services.business_sync_service import sync_ticket_created
from app.services.sla_service import ensure_sla_for_ticket


def create_ticket(
    db: Session,
    data: TicketCreateRequest,
    *,
    approved_action: bool = False,
    commit: bool = True,
) -> Ticket:
    """创建工单。"""
    ensure_approved_action("创建工单", approved_action)
    ticket = Ticket(**data.model_dump())
    db.add(ticket)
    if commit:
        db.commit()
        db.refresh(ticket)
        ensure_sla_for_ticket(db, ticket)
        sync_ticket_created(db, ticket)
    else:
        db.flush()
        ensure_sla_for_ticket(db, ticket, commit=False)
    return ticket


def list_tickets(db: Session, *, offset: int = 0, limit: int = 20) -> tuple[list[Ticket], int]:
    """分页查询工单列表。"""
    total = db.scalar(select(func.count()).select_from(Ticket)) or 0
    items = db.scalars(
        select(Ticket)
        .order_by(Ticket.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(items), total


def get_ticket(db: Session, ticket_id: int) -> Ticket:
    """查询工单详情。"""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise AppException("工单不存在。", status_code=status.HTTP_404_NOT_FOUND)
    return ticket


def update_ticket(db: Session, ticket_id: int, data: TicketUpdateRequest) -> Ticket:
    """更新工单。"""
    ticket = get_ticket(db, ticket_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    db.commit()
    db.refresh(ticket)
    return ticket
