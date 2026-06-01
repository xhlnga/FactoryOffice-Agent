from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppException
from app.integrations.core.base import ApprovalProvider
from app.integrations.core.idempotency import build_idempotency_key
from app.integrations.core.registry import provider_registry
from app.integrations.core.schemas import ApprovalCallbackAction, IntegrationPlatform, ProviderContext
from app.integrations.providers import register_builtin_providers
from app.models.base import AuditStatus, IntegrationConfigStatus, IntegrationEventStatus
from app.models.idempotency_key import IdempotencyKey
from app.models.integration_config import IntegrationConfig
from app.models.integration_event import IntegrationEvent
from app.schemas.approval import ApprovalDecisionRequest
from app.schemas.approval_template import ApprovalWithdrawRequest
from app.schemas.audit_log import AuditLogCreateRequest
from app.schemas.integration import IntegrationEventRead
from app.services.approval_service import approve_approval, reject_approval, withdraw_approval
from app.services.audit_service import create_audit_log
from app.utils.time_utils import utc_now

router = APIRouter()


@router.post("/{platform}", summary="接收外部平台回调")
def receive_callback(
    platform: IntegrationPlatform,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict:
    """接收企业微信、钉钉、飞书或通用 Webhook 回调。

    当前最小闭环支持通用回调字段：
    local_approval_id / approval_id、action、actor_external_user_id、comment。
    真实平台的验签、解密和专有字段转换由对应 Provider 逐步扩展。
    """
    event_type = _event_type(payload)
    external_event_id = _external_event_id(payload)
    idempotency_key = build_idempotency_key(
        provider=platform.value,
        event_type=event_type,
        external_event_id=external_event_id,
        payload=payload,
    )
    existing_key = db.get(IdempotencyKey, idempotency_key)
    if existing_key is not None:
        return {
            "event": None,
            "duplicated": True,
            "message": "该回调已处理，已按幂等规则跳过。",
            "previous_result": existing_key.result,
        }

    event = IntegrationEvent(
        enterprise_id=_enterprise_id(payload),
        provider=platform.value,
        event_type=event_type,
        external_event_id=external_event_id,
        payload=payload,
        status=IntegrationEventStatus.RECEIVED,
    )
    db.add(event)
    db.flush()

    try:
        event.status = IntegrationEventStatus.PROCESSING
        result = _process_approval_callback(db, platform, payload)
        event.status = IntegrationEventStatus.SUCCESS
        event.processed_at = utc_now()
        db.add(
            IdempotencyKey(
                key=idempotency_key,
                provider=platform.value,
                event_type=event_type,
                result=result,
                processed_at=utc_now(),
                expires_at=utc_now() + timedelta(days=30),
            )
        )
        _write_callback_audit(db, platform=platform, event_id=event.id, payload=payload, result=result, failed=False)
        db.commit()
    except Exception as exc:
        event.status = IntegrationEventStatus.FAILED
        event.last_error = str(exc)
        event.processed_at = utc_now()
        _write_callback_audit(
            db,
            platform=platform,
            event_id=event.id,
            payload=payload,
            result={"error": str(exc)},
            failed=True,
        )
        db.commit()
        raise

    db.refresh(event)
    return {
        "event": IntegrationEventRead.model_validate(event).model_dump(mode="json"),
        "duplicated": False,
        "result": result,
        "message": "外部回调处理完成。",
    }


def _process_approval_callback(
    db: Session,
    platform: IntegrationPlatform,
    payload: dict[str, Any],
) -> dict[str, Any]:
    provider = _approval_provider(db, platform)
    approval_event = provider.parse_callback(payload)
    if approval_event.local_approval_id is None:
        return {"message": "回调已记录，未携带本地审批 ID，未变更业务状态。"}

    actor_name = approval_event.actor_external_user_id or "外部平台用户"
    comment = approval_event.comment or ""
    if approval_event.action == ApprovalCallbackAction.APPROVE:
        approval = approve_approval(
            db,
            approval_event.local_approval_id,
            ApprovalDecisionRequest(reviewer=actor_name, comment=comment),
        )
        return {"approval_id": approval.id, "status": approval.status.value, "action": "approve"}

    if approval_event.action == ApprovalCallbackAction.REJECT:
        approval = reject_approval(
            db,
            approval_event.local_approval_id,
            ApprovalDecisionRequest(reviewer=actor_name, comment=comment),
        )
        return {"approval_id": approval.id, "status": approval.status.value, "action": "reject"}

    if approval_event.action == ApprovalCallbackAction.WITHDRAW:
        approval = withdraw_approval(
            db,
            approval_event.local_approval_id,
            ApprovalWithdrawRequest(actor_name=actor_name, comment=comment),
        )
        return {"approval_id": approval.id, "status": approval.status.value, "action": "withdraw"}

    raise AppException(
        "该回调动作当前不能自动处理。",
        status_code=status.HTTP_400_BAD_REQUEST,
        details={"action": approval_event.action.value},
    )


def _approval_provider(db: Session, platform: IntegrationPlatform) -> ApprovalProvider:
    register_builtin_providers(replace=True)
    config = db.scalars(
        select(IntegrationConfig)
        .where(IntegrationConfig.platform == platform.value)
        .where(IntegrationConfig.status == IntegrationConfigStatus.ACTIVE)
        .order_by(IntegrationConfig.id.asc())
        .limit(1)
    ).first()
    provider_config = dict(config.encrypted_config or {}) if config is not None else {}
    if config is not None and config.webhook_url:
        provider_config["webhook_url"] = config.webhook_url
    provider = provider_registry.get(
        platform,
        ProviderContext(
            platform=platform,
            enterprise_id=config.enterprise_id if config is not None else _enterprise_id({}),
            config_id=config.id if config is not None else None,
            config=provider_config,
        ),
    )
    if not isinstance(provider, ApprovalProvider):
        raise AppException(
            "该平台当前只支持通知，不支持直接审批回调处理。",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"platform": platform.value},
        )
    return provider


def _write_callback_audit(
    db: Session,
    *,
    platform: IntegrationPlatform,
    event_id: int,
    payload: dict[str, Any],
    result: dict[str, Any],
    failed: bool,
) -> None:
    create_audit_log(
        db,
        AuditLogCreateRequest(
            action="integration_callback",
            input=str({"platform": platform.value, "event_id": event_id}),
            output=str(result),
            tool_name="callback_endpoint",
            tool_args={"payload": payload},
            status=AuditStatus.FAILED if failed else AuditStatus.SUCCESS,
        ),
        commit=False,
    )


def _event_type(payload: dict[str, Any]) -> str:
    value = payload.get("event_type") or payload.get("type") or payload.get("action") or "callback"
    return str(value)


def _external_event_id(payload: dict[str, Any]) -> str | None:
    value = payload.get("event_id") or payload.get("uuid") or payload.get("request_id")
    return str(value) if value is not None else None


def _enterprise_id(payload: dict[str, Any]) -> int | None:
    value = payload.get("enterprise_id")
    return int(value) if isinstance(value, int | str) and str(value).isdigit() else None
