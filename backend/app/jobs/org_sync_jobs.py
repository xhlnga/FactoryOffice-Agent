from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.integrations.core.schemas import IntegrationPlatform
from app.integrations.services.org_sync_service import OrgSyncService
from app.models.base import IntegrationConfigStatus, IntegrationEventStatus, utc_now
from app.models.integration_config import IntegrationConfig
from app.models.integration_event import IntegrationEvent


def scan_active_org_sync_configs(*, limit: int | None = None, enqueue: bool = True) -> dict[str, Any]:
    """扫描启用的组织同步配置，并按配置入队。"""
    from app.jobs.worker import enqueue_job

    db = SessionLocal()
    try:
        configs = list(
            db.scalars(
                select(IntegrationConfig)
                .where(IntegrationConfig.status == IntegrationConfigStatus.ACTIVE)
                .where(
                    IntegrationConfig.platform.in_(
                        [
                            IntegrationPlatform.LOCAL.value,
                            IntegrationPlatform.WECOM.value,
                            IntegrationPlatform.DINGTALK.value,
                            IntegrationPlatform.FEISHU.value,
                        ]
                    )
                )
                .order_by(IntegrationConfig.id.asc())
                .limit(limit or settings.job_batch_size)
            )
        )
        enqueued = 0
        processed = 0
        for config in configs:
            if enqueue:
                enqueue_job(
                    sync_organization_for_config,
                    config.id,
                    job_id=f"org-sync:{config.id}",
                )
                enqueued += 1
            else:
                sync_organization_for_config(config.id)
                processed += 1
        return {"scanned": len(configs), "enqueued": enqueued, "processed": processed}
    finally:
        db.close()


def sync_organization_for_config(config_id: int) -> dict[str, Any]:
    """按集成配置同步组织架构快照，并记录 integration_event。"""
    db = SessionLocal()
    try:
        config = db.get(IntegrationConfig, config_id)
        if config is None:
            return {"status": "skipped", "reason": "integration_config_not_found", "config_id": config_id}

        platform = _platform_or_none(config.platform)
        if platform is None:
            _record_event(
                db,
                config=config,
                status=IntegrationEventStatus.FAILED,
                payload={"error": f"未知组织同步平台：{config.platform}"},
            )
            return {"status": "failed", "config_id": config_id, "error": "unknown_platform"}

        try:
            result = OrgSyncService().sync(
                platform=platform,
                config=_config_dict(config),
                enterprise_id=config.enterprise_id,
                db=db,
                commit=False,
            )
        except Exception as exc:  # noqa: BLE001 - 外部组织同步失败必须落库，便于重试和排查。
            _record_event(
                db,
                config=config,
                status=IntegrationEventStatus.FAILED,
                payload={"error": str(exc)},
            )
            return {"status": "failed", "config_id": config_id, "error": str(exc)}

        _record_event(
            db,
            config=config,
            status=IntegrationEventStatus.SUCCESS,
            payload=result.model_dump(mode="json"),
        )
        return {
            "status": "success",
            "config_id": config_id,
            "department_count": result.department_count,
            "user_count": result.user_count,
        }
    finally:
        db.close()


def _record_event(
    db,
    *,
    config: IntegrationConfig,
    status: IntegrationEventStatus,
    payload: dict[str, Any],
) -> None:
    event = IntegrationEvent(
        enterprise_id=config.enterprise_id,
        provider=config.platform,
        event_type="org_sync",
        external_event_id=f"org-sync-{config.id}-{int(utc_now().timestamp())}",
        payload=payload,
        status=status,
        processed_at=utc_now() if status == IntegrationEventStatus.SUCCESS else None,
        last_error=payload.get("error"),
        retry_count=1 if status == IntegrationEventStatus.FAILED else 0,
    )
    db.add(event)
    db.commit()


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
