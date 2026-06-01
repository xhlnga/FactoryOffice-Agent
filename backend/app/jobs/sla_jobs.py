from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.base import SLAStatus, utc_now
from app.models.sla import SLAInstance
from app.services.sla_service import notify_sla_event_if_configured, should_escalate_sla_instance


def scan_active_sla_instances(*, limit: int | None = None) -> dict[str, Any]:
    """扫描 SLA 实例，更新提醒、超时和升级状态，并发送通知。"""
    db = SessionLocal()
    now = utc_now()
    changed = 0
    notified = 0
    try:
        instances = list(
            db.scalars(
                select(SLAInstance)
                .where(SLAInstance.status.in_([SLAStatus.ACTIVE, SLAStatus.BREACHED]))
                .order_by(SLAInstance.created_at.asc())
                .limit(limit or settings.job_batch_size)
            )
        )
        for instance in instances:
            if instance.resolved_at is not None:
                instance.status = SLAStatus.RESOLVED
                changed += 1
                continue

            if instance.status == SLAStatus.BREACHED:
                if should_escalate_sla_instance(db, instance, now=now):
                    instance.escalated_at = now
                    changed += 1
                    if notify_sla_event_if_configured(db, instance, event_type="escalated", commit=False):
                        notified += 1
                continue

            if _is_due(now, instance.deadline_at):
                instance.status = SLAStatus.BREACHED
                instance.breached_at = instance.breached_at or now
                changed += 1
                if notify_sla_event_if_configured(db, instance, event_type="breached", commit=False):
                    notified += 1
                continue

            if _is_due(now, instance.response_due_at) and instance.first_remind_at is None:
                instance.first_remind_at = now
                changed += 1
                if notify_sla_event_if_configured(db, instance, event_type="response_remind", commit=False):
                    notified += 1

        if changed:
            db.commit()
        return {"scanned": len(instances), "changed": changed, "notified": notified}
    finally:
        db.close()


def close_sla_instance(instance_id: int) -> dict[str, Any]:
    """关闭 SLA 实例。"""
    db = SessionLocal()
    try:
        instance = db.get(SLAInstance, instance_id)
        if instance is None:
            return {"status": "skipped", "reason": "sla_instance_not_found", "instance_id": instance_id}
        instance.status = SLAStatus.RESOLVED
        instance.resolved_at = instance.resolved_at or utc_now()
        db.commit()
        return {"status": "resolved", "instance_id": instance_id}
    finally:
        db.close()


def _is_due(now: datetime, target: datetime | None) -> bool:
    """比较 SLA 时间，兼容 SQLite 返回的无时区 datetime。"""
    if target is None:
        return False
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now >= target
