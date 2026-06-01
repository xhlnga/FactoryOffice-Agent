from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import SessionLocal
from app.integrations.core.schemas import BusinessObjectType, IntegrationEventStatus, IntegrationPlatform
from app.models.external_id_mapping import ExternalIdMapping
from app.models.purchase_request import PurchaseRequest
from app.models.task import Task
from app.models.ticket import Ticket
from app.services.business_sync_service import BusinessSyncRequest, sync_business_object


def scan_failed_business_sync_records(*, limit: int | None = None, enqueue: bool = True) -> dict[str, Any]:
    """扫描失败的外部业务同步记录，默认逐条入队重试。"""
    from app.jobs.worker import enqueue_job

    db = SessionLocal()
    try:
        mappings = list(
            db.scalars(
                select(ExternalIdMapping)
                .where(ExternalIdMapping.sync_status == IntegrationEventStatus.FAILED.value)
                .where(ExternalIdMapping.retry_count < settings.job_max_retries)
                .order_by(ExternalIdMapping.last_sync_at.asc().nullsfirst(), ExternalIdMapping.created_at.asc())
                .limit(limit or settings.job_batch_size)
            )
        )
        enqueued = 0
        processed = 0
        for mapping in mappings:
            if enqueue:
                enqueue_job(
                    retry_business_sync_mapping,
                    mapping.id,
                    job_id=f"business-sync-retry:{mapping.id}:{mapping.retry_count}",
                )
                enqueued += 1
            else:
                retry_business_sync_mapping(mapping.id)
                processed += 1
        return {"scanned": len(mappings), "enqueued": enqueued, "processed": processed}
    finally:
        db.close()


def retry_business_sync_mapping(mapping_id: int) -> dict[str, Any]:
    """根据 external_id_mappings 记录重试外部业务同步。"""
    db = SessionLocal()
    try:
        mapping = db.get(ExternalIdMapping, mapping_id)
        if mapping is None:
            return {"status": "skipped", "reason": "mapping_not_found", "mapping_id": mapping_id}
        if mapping.sync_status == IntegrationEventStatus.SUCCESS.value and mapping.external_id:
            return {"status": "skipped", "reason": "already_success", "mapping_id": mapping_id}
        if mapping.retry_count >= settings.job_max_retries:
            return {"status": "skipped", "reason": "retry_limit_reached", "mapping_id": mapping_id}

        request = _request_from_mapping(db, mapping)
        if request is None:
            mapping.retry_count += 1
            mapping.last_error = "无法根据本地对象重建外部同步请求。"
            db.commit()
            return {"status": "failed", "mapping_id": mapping_id, "error": mapping.last_error}

        record = sync_business_object(db, request)
        return {
            "status": record.sync_status if record is not None else "skipped",
            "mapping_id": mapping_id,
            "external_system": record.external_system if record is not None else mapping.external_system,
            "external_id": record.external_id if record is not None else None,
            "error": record.last_error if record is not None else None,
        }
    finally:
        db.close()


def _request_from_mapping(db, mapping: ExternalIdMapping) -> BusinessSyncRequest | None:
    object_type = _object_type_or_none(mapping.object_type)
    target_system = _platform_or_none(mapping.external_system)
    local_id = _int_or_none(mapping.local_id)
    if object_type is None or target_system is None or local_id is None:
        return None

    payload = _payload_from_local_object(db, object_type=object_type, local_id=local_id)
    if payload is None:
        return None

    return BusinessSyncRequest(
        enterprise_id=mapping.enterprise_id,
        object_type=object_type,
        local_id=local_id,
        target_system=target_system,
        payload=payload,
        action="retry",
        metadata={"retry_mapping_id": mapping.id, "previous_external_id": mapping.external_id},
    )


def _payload_from_local_object(db, *, object_type: BusinessObjectType, local_id: int) -> dict[str, Any] | None:
    if object_type == BusinessObjectType.TASK:
        task = _get_if_table_exists(db, Task, "tasks", local_id)
        return None if task is None else {
            "title": task.title,
            "description": task.description,
            "assignee": task.assignee,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "priority": _enum_value(task.priority),
            "status": _enum_value(task.status),
            "source": task.source,
        }
    if object_type in {BusinessObjectType.TICKET, BusinessObjectType.QUALITY_ISSUE}:
        ticket = _get_if_table_exists(db, Ticket, "tickets", local_id)
        return None if ticket is None else {
            "ticket_type": ticket.ticket_type,
            "title": ticket.title,
            "description": ticket.description,
            "priority": _enum_value(ticket.priority),
            "status": _enum_value(ticket.status),
            "created_by": ticket.created_by,
        }
    if object_type == BusinessObjectType.PURCHASE_REQUEST:
        purchase = _get_if_table_exists(db, PurchaseRequest, "purchase_requests", local_id)
        return None if purchase is None else {
            "item_name": purchase.item_name,
            "quantity": purchase.quantity,
            "reason": purchase.reason,
            "budget": purchase.budget,
            "supplier": purchase.supplier,
            "status": _enum_value(purchase.status),
            "created_by": purchase.created_by,
        }
    return None


def _get_if_table_exists(db, model: type[Any], table_name: str, local_id: int) -> Any | None:
    try:
        if not inspect(db.connection()).has_table(table_name):
            return None
        return db.get(model, local_id)
    except SQLAlchemyError:
        db.rollback()
        return None


def _object_type_or_none(value: str) -> BusinessObjectType | None:
    try:
        return BusinessObjectType(value)
    except ValueError:
        return None


def _platform_or_none(value: str) -> IntegrationPlatform | None:
    try:
        return IntegrationPlatform(value)
    except ValueError:
        return None


def _int_or_none(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value

