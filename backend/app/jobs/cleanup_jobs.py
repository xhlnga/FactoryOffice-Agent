from datetime import timedelta
from typing import Any

from sqlalchemy import delete

from app.core.database import SessionLocal
from app.models.base import IntegrationEventStatus, NotificationDeliveryStatus, utc_now
from app.models.integration_event import IntegrationEvent
from app.models.notification_delivery import NotificationDelivery


def cleanup_old_integration_events(*, retention_days: int = 90) -> dict[str, Any]:
    """清理已成功或重复的旧集成事件，失败事件默认保留便于排查。"""
    db = SessionLocal()
    try:
        cutoff = utc_now() - timedelta(days=retention_days)
        result = db.execute(
            delete(IntegrationEvent)
            .where(IntegrationEvent.created_at < cutoff)
            .where(IntegrationEvent.status.in_([IntegrationEventStatus.SUCCESS, IntegrationEventStatus.DUPLICATED]))
        )
        db.commit()
        return {"deleted": result.rowcount or 0, "retention_days": retention_days}
    finally:
        db.close()


def cleanup_old_notification_deliveries(*, retention_days: int = 90) -> dict[str, Any]:
    """清理已成功的旧通知记录，失败/重试中记录保留。"""
    db = SessionLocal()
    try:
        cutoff = utc_now() - timedelta(days=retention_days)
        result = db.execute(
            delete(NotificationDelivery)
            .where(NotificationDelivery.created_at < cutoff)
            .where(NotificationDelivery.status == NotificationDeliveryStatus.SUCCESS)
        )
        db.commit()
        return {"deleted": result.rowcount or 0, "retention_days": retention_days}
    finally:
        db.close()

