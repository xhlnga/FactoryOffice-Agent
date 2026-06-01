from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.core.schemas import (
    BusinessObjectType,
    BusinessSyncResult,
    IntegrationEventStatus,
    IntegrationPlatform,
)
from app.integrations.services.business_sync_service import BusinessSyncService as IntegrationBusinessSyncService
from app.models.approval import Approval
from app.models.base import AuditStatus, IntegrationConfigStatus, utc_now
from app.models.external_id_mapping import ExternalIdMapping
from app.models.integration_config import IntegrationConfig
from app.models.purchase_request import PurchaseRequest
from app.models.task import Task
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.audit_log import AuditLogCreateRequest
from app.services.audit_service import create_audit_log


@dataclass(frozen=True, slots=True)
class BusinessSyncRequest:
    """本地业务对象同步请求。"""

    object_type: BusinessObjectType
    local_id: int
    target_system: IntegrationPlatform
    payload: dict[str, Any]
    enterprise_id: int | None = None
    action: str = "create"
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class BusinessSyncRecord:
    """业务同步落库结果。"""

    external_system: str
    external_id: str | None
    sync_status: str
    last_error: str | None
    retry_count: int
    last_sync_at: str | None


def sync_task_created(db: Session, task: Task, *, commit: bool = True) -> BusinessSyncRecord | None:
    """任务创建后同步到 OA。"""
    return sync_business_object(
        db,
        BusinessSyncRequest(
            object_type=BusinessObjectType.TASK,
            local_id=task.id,
            target_system=IntegrationPlatform.GENERIC_OA,
            payload=_task_payload(task),
            enterprise_id=_resolve_enterprise_id(db, task),
            action="create",
        ),
        commit=commit,
    )


def sync_ticket_created(db: Session, ticket: Ticket, *, commit: bool = True) -> BusinessSyncRecord | None:
    """工单创建后同步到 MES/QMS 类系统。"""
    object_type = BusinessObjectType.QUALITY_ISSUE if "质量" in (ticket.ticket_type or "") else BusinessObjectType.TICKET
    return sync_business_object(
        db,
        BusinessSyncRequest(
            object_type=object_type,
            local_id=ticket.id,
            target_system=IntegrationPlatform.GENERIC_MES,
            payload=_ticket_payload(ticket),
            enterprise_id=_resolve_enterprise_id(db, ticket),
            action="create",
        ),
        commit=commit,
    )


def sync_purchase_request_created(
    db: Session,
    purchase_request: PurchaseRequest,
    *,
    commit: bool = True,
) -> BusinessSyncRecord | None:
    """采购申请创建后同步到 ERP。"""
    return sync_business_object(
        db,
        BusinessSyncRequest(
            object_type=BusinessObjectType.PURCHASE_REQUEST,
            local_id=purchase_request.id,
            target_system=IntegrationPlatform.GENERIC_ERP,
            payload=_purchase_payload(purchase_request),
            enterprise_id=_resolve_enterprise_id(db, purchase_request),
            action="create",
        ),
        commit=commit,
    )


def sync_approval_execution_result(
    db: Session,
    approval: Approval,
    *,
    commit: bool = True,
) -> list[BusinessSyncRecord]:
    """审批完成后根据执行结果触发外部系统同步。

    注意：这里只处理已经写入本地业务表的对象，避免未审批草稿直接进入外部系统。
    """
    result = approval.execution_result or {}
    records: list[BusinessSyncRecord] = []

    purchase_id = result.get("purchase_request_id")
    if isinstance(purchase_id, int):
        purchase = _get_if_table_exists(db, PurchaseRequest, "purchase_requests", purchase_id)
        if purchase is not None:
            record = sync_purchase_request_created(db, purchase, commit=False)
            if record is not None:
                records.append(record)

    ticket_id = result.get("ticket_id")
    if isinstance(ticket_id, int):
        ticket = _get_if_table_exists(db, Ticket, "tickets", ticket_id)
        if ticket is not None:
            record = sync_ticket_created(db, ticket, commit=False)
            if record is not None:
                records.append(record)

    task_id = result.get("task_id")
    if isinstance(task_id, int):
        task = _get_if_table_exists(db, Task, "tasks", task_id)
        if task is not None:
            record = sync_task_created(db, task, commit=False)
            if record is not None:
                records.append(record)

    task_ids = result.get("task_ids")
    if isinstance(task_ids, list):
        for item in task_ids:
            if not isinstance(item, int):
                continue
            task = _get_if_table_exists(db, Task, "tasks", item)
            if task is None:
                continue
            record = sync_task_created(db, task, commit=False)
            if record is not None:
                records.append(record)

    if commit and records:
        db.commit()
    return records


def sync_business_object(
    db: Session,
    request: BusinessSyncRequest,
    *,
    commit: bool = True,
) -> BusinessSyncRecord | None:
    """统一外部业务系统同步入口。

    没有启用外部系统配置时直接返回 None；同步失败只记录状态，不回滚本地业务。
    """
    if not _table_exists(db, "external_id_mappings") or not _table_exists(db, "integration_configs"):
        return None

    config = _find_active_config(db, request.target_system, enterprise_id=request.enterprise_id)
    if config is None:
        return None

    platform = _platform_or_none(config.platform)
    if platform is None:
        return None

    existing = _find_mapping(
        db,
        enterprise_id=config.enterprise_id,
        object_type=request.object_type.value,
        local_id=str(request.local_id),
        external_system=platform.value,
    )
    if existing is not None and existing.sync_status == IntegrationEventStatus.SUCCESS.value and existing.external_id:
        return _to_record(existing)

    provider_config = dict(config.encrypted_config or {})
    if config.webhook_url:
        provider_config["webhook_url"] = config.webhook_url
    if config.callback_url:
        provider_config["callback_url"] = config.callback_url

    try:
        result = IntegrationBusinessSyncService().push_object(
            platform=platform,
            object_type=request.object_type,
            local_id=request.local_id,
            payload={
                "action": request.action,
                "object_type": request.object_type.value,
                "local_id": request.local_id,
                **request.payload,
            },
            config=provider_config,
            enterprise_id=config.enterprise_id,
            metadata=request.metadata or {},
        )
    except Exception as exc:  # noqa: BLE001 - 外部系统失败必须落库，不应打断本地业务。
        result = BusinessSyncResult(
            success=False,
            sync_status=IntegrationEventStatus.FAILED,
            retryable=True,
            error_message=str(exc),
        )

    mapping = _upsert_mapping(db, request=request, config=config, platform=platform, result=result, existing=existing)
    _write_sync_audit_log(db, request=request, mapping=mapping, result=result)
    if commit:
        db.commit()
        db.refresh(mapping)
    else:
        db.flush()
    return _to_record(mapping)


def _find_active_config(
    db: Session,
    target_system: IntegrationPlatform,
    *,
    enterprise_id: int | None,
) -> IntegrationConfig | None:
    """查找启用的外部系统配置；没有专用配置时允许使用 local 作为本地演示兜底。"""
    if enterprise_id is None:
        # 没有企业上下文时不能随便选中真实外部系统，避免多租户场景串到别人的 OA/ERP/MES。
        candidate_platforms = [IntegrationPlatform.LOCAL.value]
    else:
        candidate_platforms = [target_system.value, IntegrationPlatform.LOCAL.value]
    query = (
        select(IntegrationConfig)
        .where(IntegrationConfig.status == IntegrationConfigStatus.ACTIVE)
        .where(IntegrationConfig.platform.in_(candidate_platforms))
        .order_by(IntegrationConfig.id.asc())
    )
    if enterprise_id is not None:
        query = query.where(IntegrationConfig.enterprise_id == enterprise_id)
    try:
        configs = list(db.scalars(query).all())
    except SQLAlchemyError:
        db.rollback()
        return None
    if not configs:
        return None
    return next((item for item in configs if item.platform == target_system.value), configs[0])


def _resolve_enterprise_id(db: Session, obj: Any) -> int | None:
    """从业务对象上解析企业 ID；解析不到时返回 None，只允许 local 演示同步。"""
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


def _upsert_mapping(
    db: Session,
    *,
    request: BusinessSyncRequest,
    config: IntegrationConfig,
    platform: IntegrationPlatform,
    result: BusinessSyncResult,
    existing: ExternalIdMapping | None,
) -> ExternalIdMapping:
    """新增或更新外部 ID 映射。"""
    now = utc_now()
    mapping = existing or ExternalIdMapping(
        enterprise_id=config.enterprise_id,
        object_type=request.object_type.value,
        local_id=str(request.local_id),
        external_system=platform.value,
    )
    mapping.external_id = result.external_id
    mapping.sync_status = _sync_status_value(result.sync_status)
    mapping.last_sync_at = now
    mapping.last_error = result.error_message
    if not result.success:
        mapping.retry_count = (mapping.retry_count or 0) + 1
    if existing is None:
        db.add(mapping)
    return mapping


def _find_mapping(
    db: Session,
    *,
    enterprise_id: int,
    object_type: str,
    local_id: str,
    external_system: str,
) -> ExternalIdMapping | None:
    return db.scalar(
        select(ExternalIdMapping)
        .where(ExternalIdMapping.enterprise_id == enterprise_id)
        .where(ExternalIdMapping.object_type == object_type)
        .where(ExternalIdMapping.local_id == local_id)
        .where(ExternalIdMapping.external_system == external_system)
        .limit(1)
    )


def _get_if_table_exists(db: Session, model: type[Any], table_name: str, local_id: int) -> Any | None:
    """只在业务表存在时查询对象，避免局部测试库或未迁移环境打断审批主流程。"""
    if not _table_exists(db, table_name):
        return None
    try:
        return db.get(model, local_id)
    except SQLAlchemyError:
        db.rollback()
        return None


def _write_sync_audit_log(
    db: Session,
    *,
    request: BusinessSyncRequest,
    mapping: ExternalIdMapping,
    result: BusinessSyncResult,
) -> None:
    """记录外部同步审计日志。"""
    if not _table_exists(db, "audit_logs"):
        return
    create_audit_log(
        db,
        AuditLogCreateRequest(
            action="external_business_sync",
            input=str({"object_type": request.object_type.value, "local_id": request.local_id}),
            output=str(
                {
                    "external_system": mapping.external_system,
                    "external_id": mapping.external_id,
                    "sync_status": mapping.sync_status,
                    "last_error": mapping.last_error,
                    "retry_count": mapping.retry_count,
                    "last_sync_at": mapping.last_sync_at.isoformat() if mapping.last_sync_at else None,
                }
            ),
            tool_name="business_sync_service",
            tool_args={"target_system": mapping.external_system, "payload": request.payload},
            status=AuditStatus.SUCCESS if result.success else AuditStatus.FAILED,
        ),
        commit=False,
    )


def _task_payload(task: Task) -> dict[str, Any]:
    return {
        "title": task.title,
        "description": task.description,
        "assignee": task.assignee,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "priority": _enum_value(task.priority),
        "status": _enum_value(task.status),
        "source": task.source,
    }


def _ticket_payload(ticket: Ticket) -> dict[str, Any]:
    return {
        "ticket_type": ticket.ticket_type,
        "title": ticket.title,
        "description": ticket.description,
        "priority": _enum_value(ticket.priority),
        "status": _enum_value(ticket.status),
        "created_by": ticket.created_by,
    }


def _purchase_payload(purchase_request: PurchaseRequest) -> dict[str, Any]:
    return {
        "item_name": purchase_request.item_name,
        "quantity": purchase_request.quantity,
        "reason": purchase_request.reason,
        "budget": purchase_request.budget,
        "supplier": purchase_request.supplier,
        "status": _enum_value(purchase_request.status),
        "created_by": purchase_request.created_by,
    }


def _to_record(mapping: ExternalIdMapping) -> BusinessSyncRecord:
    return BusinessSyncRecord(
        external_system=mapping.external_system,
        external_id=mapping.external_id,
        sync_status=mapping.sync_status,
        last_error=mapping.last_error,
        retry_count=mapping.retry_count,
        last_sync_at=mapping.last_sync_at.isoformat() if mapping.last_sync_at else None,
    )


def _sync_status_value(value: IntegrationEventStatus | str) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _platform_or_none(value: str) -> IntegrationPlatform | None:
    try:
        return IntegrationPlatform(value)
    except ValueError:
        return None


def _table_exists(db: Session, table_name: str) -> bool:
    try:
        return bool(inspect(db.connection()).has_table(table_name))
    except Exception:
        return False
