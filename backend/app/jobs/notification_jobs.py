from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.integrations.core.schemas import IntegrationPlatform, NotificationRecipient
from app.integrations.services.notification_service import NotificationService
from app.models.base import IntegrationConfigStatus, NotificationDeliveryStatus, utc_now
from app.models.integration_config import IntegrationConfig
from app.models.notification_delivery import NotificationDelivery


def scan_retryable_notifications(*, limit: int | None = None, enqueue: bool = True) -> dict[str, Any]:
    """扫描可重试通知，默认把逐条重试任务放入队列。"""
    from app.jobs.worker import enqueue_job

    db = SessionLocal()
    try:
        deliveries = list(
            db.scalars(
                select(NotificationDelivery)
                .where(NotificationDelivery.retryable.is_(True))
                .where(NotificationDelivery.retry_count < settings.job_max_retries)
                .where(NotificationDelivery.status.in_([NotificationDeliveryStatus.PENDING, NotificationDeliveryStatus.RETRYING]))
                .order_by(NotificationDelivery.created_at.asc())
                .limit(limit or settings.job_batch_size)
            )
        )
        enqueued = 0
        processed = 0
        for delivery in deliveries:
            if enqueue:
                enqueue_job(
                    retry_notification_delivery,
                    delivery.id,
                    job_id=f"notification-retry:{delivery.id}:{delivery.retry_count}",
                )
                enqueued += 1
            else:
                retry_notification_delivery(delivery.id)
                processed += 1
        return {"scanned": len(deliveries), "enqueued": enqueued, "processed": processed}
    finally:
        db.close()


def retry_notification_delivery(delivery_id: int) -> dict[str, Any]:
    """重试单条通知投递，尽量使用原始内容快照和跳转链接。"""
    db = SessionLocal()
    try:
        delivery = db.get(NotificationDelivery, delivery_id)
        if delivery is None:
            return {"status": "skipped", "reason": "notification_delivery_not_found", "delivery_id": delivery_id}
        if not delivery.retryable or delivery.retry_count >= settings.job_max_retries:
            return {"status": "skipped", "reason": "not_retryable", "delivery_id": delivery_id}

        platform = _platform_or_none(delivery.platform)
        if platform is None:
            _mark_delivery_failed(db, delivery, f"未知通知平台：{delivery.platform}")
            return {"status": "failed", "delivery_id": delivery_id, "error": delivery.last_error}

        config = _find_active_config(db, platform=platform, enterprise_id=delivery.enterprise_id)
        if config is None:
            _mark_delivery_failed(db, delivery, "未找到启用的通知平台配置。")
            return {"status": "failed", "delivery_id": delivery_id, "error": delivery.last_error}

        result = NotificationService().send_message(
            platform=platform,
            title=delivery.title or _snapshot_value(delivery, "title") or "企业通知重试",
            content=_retry_content(delivery),
            db=None,
            config=_config_dict(config),
            enterprise_id=delivery.enterprise_id,
            recipients=[
                NotificationRecipient(
                    user_id=delivery.recipient_user_id,
                    external_user_id=delivery.recipient_external_user_id,
                )
            ],
            business_type=delivery.business_type,
            business_id=delivery.business_id,
            action_url=delivery.action_url or _snapshot_value(delivery, "action_url"),
            metadata={"retry_for_delivery_id": delivery.id},
            commit=False,
        )

        delivery.response_code = result.response_code
        delivery.response_body = result.response_body
        delivery.last_error = result.error_message
        delivery.retry_count += 1
        delivery.retryable = result.retryable
        delivery.status = (
            NotificationDeliveryStatus.SUCCESS
            if result.success
            else NotificationDeliveryStatus.RETRYING
            if result.retryable and delivery.retry_count < settings.job_max_retries
            else NotificationDeliveryStatus.FAILED
        )
        delivery.delivered_at = utc_now() if result.success else delivery.delivered_at
        db.commit()
        return {
            "status": delivery.status.value,
            "delivery_id": delivery.id,
            "retry_count": delivery.retry_count,
            "response_code": delivery.response_code,
            "error": delivery.last_error,
        }
    finally:
        db.close()


def _find_active_config(db: Session, *, platform: IntegrationPlatform, enterprise_id: int | None) -> IntegrationConfig | None:
    query = (
        select(IntegrationConfig)
        .where(IntegrationConfig.status == IntegrationConfigStatus.ACTIVE)
        .where(IntegrationConfig.platform.in_([platform.value, IntegrationPlatform.LOCAL.value]))
        .order_by(IntegrationConfig.id.asc())
    )
    if enterprise_id is not None:
        query = query.where(IntegrationConfig.enterprise_id == enterprise_id)
    configs = list(db.scalars(query).all())
    if not configs:
        return None
    return next((item for item in configs if item.platform == platform.value), configs[0])


def _mark_delivery_failed(db: Session, delivery: NotificationDelivery, error: str) -> None:
    delivery.status = NotificationDeliveryStatus.FAILED
    delivery.last_error = error
    delivery.retry_count += 1
    db.commit()


def _retry_content(delivery: NotificationDelivery) -> str:
    snapshot = delivery.payload_snapshot or {}
    content = snapshot.get("content") or snapshot.get("summary")
    if content:
        return str(content)
    return (
        "这是一条失败通知的后台重试。\n"
        f"原通知编号：{delivery.id}\n"
        f"业务类型：{delivery.business_type or '-'}\n"
        f"业务编号：{delivery.business_id or '-'}\n"
        f"上次错误：{delivery.last_error or '-'}"
    )


def _snapshot_value(delivery: NotificationDelivery, key: str) -> str | None:
    """读取通知快照中的字符串字段。"""
    value = (delivery.payload_snapshot or {}).get(key)
    return str(value) if value else None


def _config_dict(config: IntegrationConfig) -> dict[str, Any]:
    data = dict(config.encrypted_config or {})
    if config.webhook_url:
        data["webhook_url"] = config.webhook_url
    if config.callback_url:
        data["callback_url"] = config.callback_url
    return data


def _platform_or_none(value: str) -> IntegrationPlatform | None:
    try:
        return IntegrationPlatform(value)
    except ValueError:
        return None
