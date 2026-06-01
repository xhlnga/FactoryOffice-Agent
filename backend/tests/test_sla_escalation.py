from datetime import timedelta

from app.integrations.providers.generic_webhook import utc_now
from app.integrations.services.sla_escalation_service import SLAEscalationService, SLAStatus


def test_sla_escalation_marks_overdue_ticket_as_breached_or_escalated() -> None:
    """高优先级工单超过时限后应触发提醒或升级状态。"""
    service = SLAEscalationService()
    evaluation = service.evaluate(
        business_type="ticket",
        priority="high",
        created_at=utc_now() - timedelta(hours=8),
        now=utc_now(),
    )

    assert evaluation.status in {SLAStatus.BREACHED, SLAStatus.ESCALATED}
    assert evaluation.minutes_left < 0

