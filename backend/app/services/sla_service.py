from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import TicketStatus
from app.models.ticket import Ticket
from app.integration import IntegrationMessage
from app.services.notification_service import notify


class SLAConfig:
    _thresholds: dict[tuple[str, str], int] = {
        ("设备维修", "urgent"): 2,
        ("设备维修", "high"): 8,
        ("设备维修", "medium"): 24,
        ("设备维修", "low"): 72,
        ("质量异常", "urgent"): 4,
        ("质量异常", "high"): 12,
        ("质量异常", "medium"): 48,
        ("质量异常", "low"): 96,
    }

    @classmethod
    def get_sla_hours(cls, ticket_type: str, priority: str) -> int:
        return cls._thresholds.get((ticket_type, priority), 48)


VALID_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.OPEN: {TicketStatus.PROCESSING, TicketStatus.CLOSED},
    TicketStatus.PROCESSING: {TicketStatus.RESOLVED, TicketStatus.CLOSED},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.PROCESSING},
    TicketStatus.CLOSED: set(),
}


def set_sla_on_create(db: Session, ticket: Ticket, ticket_type: str, priority: str) -> None:
    sla_hours = SLAConfig.get_sla_hours(ticket_type, priority)
    ticket.sla_hours = sla_hours
    ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=sla_hours)
    db.commit()


def check_sla_breach(db: Session) -> list[Ticket]:
    now = datetime.now(timezone.utc)
    breached = db.scalars(
        select(Ticket).where(
            Ticket.sla_deadline < now,
            Ticket.sla_breached == False,
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.PROCESSING]),
        )
    ).all()
    for ticket in breached:
        ticket.sla_breached = True
    if breached:
        db.commit()
    for ticket in breached:
        notify(IntegrationMessage(
            title=f"SLA 超时 — 工单 #{ticket.id}",
            content=(
                f"工单 #{ticket.id}「{ticket.title}」SLA 已超时。\n"
                f"类型：{ticket.ticket_type}，创建时间：{ticket.created_at}"
            ),
        ))
    return list(breached)


def transition_status(db: Session, ticket: Ticket, new_status: TicketStatus) -> Ticket:
    current = ticket.status
    allowed = VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        allowed_names = [s.value for s in allowed]
        raise ValueError(
            f"不允许从 {current.value} 直接转换到 {new_status.value}。允许的目标状态：{allowed_names}"
        )
    ticket.status = new_status
    if new_status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
        ticket.resolved_at = datetime.now(timezone.utc)
        if ticket.sla_deadline and not ticket.sla_breached:
            now = datetime.now(timezone.utc)
            if now > ticket.sla_deadline:
                ticket.sla_breached = True
    db.commit()
    db.refresh(ticket)
    return ticket
