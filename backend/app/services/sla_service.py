from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import inspect, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.core.schemas import IntegrationPlatform, NotificationSeverity
from app.integrations.services.notification_service import NotificationService
from app.integrations.services.sla_escalation_service import SLAEscalationService
from app.models.base import IntegrationConfigStatus, SLAStatus, utc_now
from app.models.integration_config import IntegrationConfig
from app.models.purchase_request import PurchaseRequest
from app.models.sla import SLAInstance, SLAPolicyModel
from app.models.ticket import Ticket
from app.models.user import User


def ensure_sla_for_ticket(db: Session, ticket: Ticket, *, commit: bool = True) -> SLAInstance | None:
    """工单创建后自动生成 SLA 实例。

    质量异常和设备维修在制造业里都需要响应时限，不能只靠人工记忆。
    """
    business_type = "quality_issue" if "质量" in (ticket.ticket_type or "") else "ticket"
    return ensure_sla_instance(
        db,
        enterprise_id=_resolve_enterprise_id(db, ticket),
        business_type=business_type,
        business_id=str(ticket.id),
        priority=_enum_value(ticket.priority) or "medium",
        created_at=ticket.created_at,
        commit=commit,
    )


def ensure_sla_for_purchase_request(
    db: Session,
    purchase_request: PurchaseRequest,
    *,
    commit: bool = True,
) -> SLAInstance | None:
    """采购申请创建后自动生成 SLA 实例。"""
    return ensure_sla_instance(
        db,
        enterprise_id=_resolve_enterprise_id(db, purchase_request),
        business_type="purchase_request",
        business_id=str(purchase_request.id),
        priority=_purchase_priority(purchase_request),
        created_at=purchase_request.created_at,
        commit=commit,
    )


def ensure_sla_instance(
    db: Session,
    *,
    enterprise_id: int | None,
    business_type: str,
    business_id: str,
    priority: str,
    created_at: datetime | None = None,
    commit: bool = True,
) -> SLAInstance | None:
    """按业务对象创建 SLA 实例；已存在未关闭实例时直接复用。"""
    if not _table_exists(db, "sla_instances"):
        return None

    existing = db.scalar(
        select(SLAInstance)
        .where(SLAInstance.enterprise_id == enterprise_id)
        .where(SLAInstance.business_type == business_type)
        .where(SLAInstance.business_id == business_id)
        .where(SLAInstance.status.in_([SLAStatus.ACTIVE, SLAStatus.BREACHED]))
        .limit(1)
    )
    if existing is not None:
        return existing

    policy_model, response_minutes, resolve_minutes = _resolve_policy(
        db,
        enterprise_id=enterprise_id,
        business_type=business_type,
        priority=priority,
    )
    start_at = _aware(created_at or utc_now())
    instance = SLAInstance(
        enterprise_id=enterprise_id,
        policy_id=policy_model.id if policy_model is not None else None,
        business_type=business_type,
        business_id=business_id,
        status=SLAStatus.ACTIVE,
        response_due_at=start_at + timedelta(minutes=response_minutes),
        deadline_at=start_at + timedelta(minutes=resolve_minutes),
    )
    db.add(instance)
    if commit:
        db.commit()
        db.refresh(instance)
    else:
        db.flush()
    return instance


def notify_sla_event_if_configured(
    db: Session,
    instance: SLAInstance,
    *,
    event_type: str,
    commit: bool = True,
) -> bool:
    """SLA 提醒/超时/升级时发送通知并写 notification_deliveries。

    没有启用通知配置时返回 False，不影响 SLA 状态落库。
    """
    config = _find_notification_config(db, enterprise_id=instance.enterprise_id)
    if config is None:
        return False

    platform = _platform_or_none(config.platform)
    if platform is None:
        return False

    title, summary, severity = _sla_message(instance, event_type)
    NotificationService().send_card(
        platform=platform,
        title=title,
        summary=summary,
        db=db,
        config=_config_dict(config),
        enterprise_id=config.enterprise_id,
        fields={
            "业务类型": instance.business_type,
            "业务 ID": instance.business_id,
            "SLA 状态": _enum_value(instance.status),
            "响应截止": instance.response_due_at.isoformat() if instance.response_due_at else "",
            "处理截止": instance.deadline_at.isoformat() if instance.deadline_at else "",
        },
        severity=severity,
        business_type="sla",
        business_id=instance.id,
        commit=commit,
    )
    return True


def should_escalate_sla_instance(db: Session, instance: SLAInstance, *, now: datetime | None = None) -> bool:
    """判断 SLA 是否应升级。"""
    if instance.breached_at is None or instance.escalated_at is not None:
        return False
    policy_model, _, _ = _resolve_policy(
        db,
        enterprise_id=instance.enterprise_id,
        business_type=instance.business_type,
        priority=_priority_from_policy(db, instance),
    )
    escalate_after = policy_model.escalate_after_minutes if policy_model is not None else 60
    return _aware(now or utc_now()) >= _aware(instance.breached_at) + timedelta(minutes=escalate_after)


def _resolve_policy(
    db: Session,
    *,
    enterprise_id: int | None,
    business_type: str,
    priority: str,
) -> tuple[SLAPolicyModel | None, int, int]:
    """优先使用企业配置的 SLA 策略，没有配置时回落到内置制造业规则。"""
    policy_model = None
    if _table_exists(db, "sla_policies"):
        query = (
            select(SLAPolicyModel)
            .where(SLAPolicyModel.business_type == business_type)
            .where(SLAPolicyModel.priority == priority)
            .where(SLAPolicyModel.enabled.is_(True))
        )
        if enterprise_id is not None:
            policy_model = db.scalar(query.where(SLAPolicyModel.enterprise_id == enterprise_id).limit(1))
        if policy_model is None:
            policy_model = db.scalar(query.where(SLAPolicyModel.enterprise_id.is_(None)).limit(1))

    if policy_model is not None:
        return policy_model, policy_model.response_minutes, policy_model.resolve_minutes

    policy = SLAEscalationService().get_policy(business_type=business_type, priority=priority)
    return None, policy.response_minutes, policy.resolve_minutes


def _find_notification_config(db: Session, *, enterprise_id: int | None) -> IntegrationConfig | None:
    if not _table_exists(db, "integration_configs"):
        return None
    platforms = [
        IntegrationPlatform.WECOM.value,
        IntegrationPlatform.DINGTALK.value,
        IntegrationPlatform.FEISHU.value,
        IntegrationPlatform.GENERIC_WEBHOOK.value,
        IntegrationPlatform.LOCAL.value,
    ]
    query = (
        select(IntegrationConfig)
        .where(IntegrationConfig.status == IntegrationConfigStatus.ACTIVE)
        .where(IntegrationConfig.platform.in_(platforms))
        .order_by(IntegrationConfig.id.asc())
    )
    if enterprise_id is not None:
        query = query.where(IntegrationConfig.enterprise_id == enterprise_id)
    else:
        query = query.where(IntegrationConfig.platform == IntegrationPlatform.LOCAL.value)
    return db.scalar(query.limit(1))


def _resolve_enterprise_id(db: Session, obj: Any) -> int | None:
    enterprise_id = getattr(obj, "enterprise_id", None)
    if isinstance(enterprise_id, int):
        return enterprise_id
    created_by = getattr(obj, "created_by", None)
    if not isinstance(created_by, int) or not _table_exists(db, "users"):
        return None
    try:
        user = db.get(User, created_by)
    except SQLAlchemyError:
        db.rollback()
        return None
    return user.enterprise_id if user is not None else None


def _priority_from_policy(db: Session, instance: SLAInstance) -> str:
    if instance.policy_id and _table_exists(db, "sla_policies"):
        policy = db.get(SLAPolicyModel, instance.policy_id)
        if policy is not None:
            return policy.priority
    if instance.business_type == "purchase_request":
        return "medium"
    return "high" if instance.business_type in {"ticket", "quality_issue"} else "medium"


def _purchase_priority(purchase_request: PurchaseRequest) -> str:
    reason = purchase_request.reason or ""
    if any(keyword in reason for keyword in ["紧急", "急需", "停线", "影响生产", "客户交付"]):
        return "urgent"
    if purchase_request.budget is not None and purchase_request.budget >= 50000:
        return "high"
    return "medium"


def _sla_message(instance: SLAInstance, event_type: str) -> tuple[str, str, NotificationSeverity]:
    if event_type == "response_remind":
        return (
            "SLA 响应提醒",
            f"{instance.business_type} #{instance.business_id} 已到响应提醒节点，请及时确认责任人和处理计划。",
            NotificationSeverity.WARNING,
        )
    if event_type == "breached":
        return (
            "SLA 已超时",
            f"{instance.business_type} #{instance.business_id} 已超过处理截止时间，需要负责人立即跟进。",
            NotificationSeverity.URGENT,
        )
    return (
        "SLA 超时升级",
        f"{instance.business_type} #{instance.business_id} 已持续超时，需要升级给上级负责人。",
        NotificationSeverity.URGENT,
    )


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


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _table_exists(db: Session, table_name: str) -> bool:
    try:
        return bool(inspect(db.connection()).has_table(table_name))
    except SQLAlchemyError:
        db.rollback()
        return False
    except Exception:
        return False
