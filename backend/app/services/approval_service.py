from datetime import date
from typing import Any

from fastapi import status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.approval import Approval
from app.models.base import ApprovalStatus, AuditStatus, utc_now
from app.schemas.approval import ApprovalCreateRequest, ApprovalDecisionRequest
from app.schemas.audit_log import AuditLogCreateRequest
from app.schemas.purchase_request import PurchaseCreateRequest
from app.schemas.task import TaskCreateRequest
from app.schemas.ticket import TicketCreateRequest
from app.services.audit_service import create_audit_log
from app.services.document_service import delete_document
from app.services.purchase_service import create_purchase_request
from app.services.task_service import create_task
from app.services.ticket_service import create_ticket


EXECUTABLE_ACTION_TYPES = {
    "create_purchase_request",
    "create_maintenance_ticket",
    "create_quality_issue_ticket",
    "create_task",
    "create_tasks",
    "delete_document",
}


def create_approval(db: Session, data: ApprovalCreateRequest) -> Approval:
    """创建待审批动作。"""
    if data.action_type not in EXECUTABLE_ACTION_TYPES:
        raise AppException(
            "该动作类型暂不支持进入审批执行。",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"action_type": data.action_type},
        )
    approval = Approval(**data.model_dump(), status=ApprovalStatus.PENDING)
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def list_approvals(
    db: Session,
    *,
    approval_status: ApprovalStatus | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Approval], int]:
    """分页查询审批列表。"""
    query = select(Approval)
    count_query = select(func.count()).select_from(Approval)

    if approval_status is not None:
        query = query.where(Approval.status == approval_status)
        count_query = count_query.where(Approval.status == approval_status)

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(Approval.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(items), total


def list_pending_approvals(db: Session, *, offset: int = 0, limit: int = 20) -> tuple[list[Approval], int]:
    """查询待审批动作。"""
    return list_approvals(
        db,
        approval_status=ApprovalStatus.PENDING,
        offset=offset,
        limit=limit,
    )


def get_approval(db: Session, approval_id: int) -> Approval:
    """查询审批详情。"""
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise AppException("审批记录不存在。", status_code=status.HTTP_404_NOT_FOUND)
    return approval


def approve_approval(db: Session, approval_id: int, data: ApprovalDecisionRequest) -> Approval:
    """批准审批，并执行对应业务动作。"""
    approval = get_approval(db, approval_id)
    if approval.status != ApprovalStatus.PENDING:
        raise AppException("只有待审批记录可以批准。", status_code=status.HTTP_409_CONFLICT)

    approval.reviewer = data.reviewer
    approval.comment = data.comment
    approval.reviewed_at = utc_now()

    try:
        result = execute_approved_action(db, approval)
    except Exception as exc:
        _rollback_if_available(db)
        approval = get_approval(db, approval_id)
        approval.status = ApprovalStatus.EXECUTION_FAILED
        approval.reviewer = data.reviewer
        approval.comment = data.comment
        approval.reviewed_at = utc_now()
        approval.execution_result = {
            "error": str(exc),
            "message": "审批动作执行失败，业务数据未写入或已回滚。",
        }
        _write_audit_log_if_possible(
            db,
            AuditLogCreateRequest(
                action=approval.action_type,
                input=str(approval.action_payload),
                output=str(approval.execution_result),
                tool_name=approval.action_type,
                tool_args=approval.action_payload,
                status=AuditStatus.FAILED,
            ),
        )
        db.commit()
        db.refresh(approval)
        raise

    approval.status = ApprovalStatus.APPROVED
    approval.executed_at = utc_now()
    approval.execution_result = result
    db.commit()
    db.refresh(approval)
    return approval


def reject_approval(db: Session, approval_id: int, data: ApprovalDecisionRequest) -> Approval:
    """拒绝审批。"""
    approval = get_approval(db, approval_id)
    if approval.status != ApprovalStatus.PENDING:
        raise AppException("只有待审批记录可以拒绝。", status_code=status.HTTP_409_CONFLICT)

    approval.status = ApprovalStatus.REJECTED
    approval.reviewer = data.reviewer
    approval.comment = data.comment
    approval.reviewed_at = utc_now()
    db.commit()
    db.refresh(approval)
    return approval


def execute_approved_action(db: Session, approval: Approval) -> dict[str, Any]:
    """审批通过后执行业务动作，并写入审计日志。"""
    result = _execute_action(db, approval.action_type, approval.action_payload)
    create_audit_log(
        db,
        AuditLogCreateRequest(
            action=approval.action_type,
            input=str(approval.action_payload),
            output=str(result),
            tool_name=approval.action_type,
            tool_args=approval.action_payload,
            status=AuditStatus.SUCCESS,
        ),
        commit=False,
    )
    return result


def _execute_action(db: Session, action_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """根据审批动作类型调用对应服务。"""
    try:
        if action_type == "create_purchase_request":
            purchase = create_purchase_request(
                db,
                PurchaseCreateRequest(**payload),
                approved_action=True,
                commit=False,
            )
            return {"purchase_request_id": purchase.id}

        if action_type in {"create_maintenance_ticket", "create_quality_issue_ticket"}:
            default_ticket_type = "质量异常" if action_type == "create_quality_issue_ticket" else "设备维修"
            ticket = create_ticket(
                db,
                TicketCreateRequest(**_ticket_payload(payload, default_ticket_type=default_ticket_type)),
                approved_action=True,
                commit=False,
            )
            return {"ticket_id": ticket.id}

        if action_type == "create_task":
            task = create_task(
                db,
                TaskCreateRequest(**_task_payload(payload, source=payload.get("source"))),
                approved_action=True,
                commit=False,
            )
            return {"task_id": task.id}

        if action_type == "create_tasks":
            created_ids: list[int] = []
            task_payloads = payload.get("tasks", [])
            if not isinstance(task_payloads, list) or not task_payloads:
                raise AppException(
                    "批量创建任务审批缺少 tasks 列表。",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            for task_payload in task_payloads:
                task = create_task(
                    db,
                    TaskCreateRequest(**_task_payload(task_payload, source=payload.get("source"))),
                    approved_action=True,
                    commit=False,
                )
                created_ids.append(task.id)
            return {"task_ids": created_ids}

        if action_type == "delete_document":
            document_id = payload.get("document_id")
            if not isinstance(document_id, int):
                raise AppException(
                    "删除文档审批缺少 document_id。",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            delete_document(db, document_id, approved_action=True, commit=False)
            return {"document_id": document_id, "deleted": True}

    except ValidationError as exc:
        raise AppException(
            "审批动作参数不完整，无法执行。",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"errors": exc.errors()},
        ) from exc

    raise AppException(
        "暂不支持执行该审批动作。",
        status_code=status.HTTP_400_BAD_REQUEST,
        details={"action_type": action_type},
    )


def _ticket_payload(payload: dict[str, Any], *, default_ticket_type: str) -> dict[str, Any]:
    """过滤工单草稿字段，只保留工单表需要的内容。"""
    ticket_type = payload.get("ticket_type") or default_ticket_type
    if ticket_type != default_ticket_type:
        raise AppException(
            "审批动作类型与工单类型不一致，已拒绝执行。",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"action_ticket_type": default_ticket_type, "payload_ticket_type": ticket_type},
        )
    return {
        "ticket_type": ticket_type,
        "title": payload.get("title"),
        "description": payload.get("description", ""),
        "priority": payload.get("priority", "medium"),
        "created_by": payload.get("created_by"),
    }


def _task_payload(payload: dict[str, Any], *, source: str | None = None) -> dict[str, Any]:
    """过滤任务草稿字段；自然语言截止时间暂不强行写入 date 字段。"""
    return {
        "title": payload.get("title"),
        "description": payload.get("description", ""),
        "assignee": payload.get("assignee"),
        "due_date": _parse_iso_date(payload.get("due_date")),
        "priority": payload.get("priority", "medium"),
        "source": source or payload.get("source"),
    }


def _parse_iso_date(value: Any) -> date | None:
    """只接受 ISO 日期；周五、下周一这类自然语言先不落入 date 字段。"""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _rollback_if_available(db: Session) -> None:
    """执行失败时回滚当前事务；测试替身没有 rollback 时跳过。"""
    rollback = getattr(db, "rollback", None)
    if callable(rollback):
        rollback()


def _write_audit_log_if_possible(db: Session, data: AuditLogCreateRequest) -> None:
    """失败审计尽量写入；轻量测试替身不支持 add/flush 时跳过。"""
    if not all(hasattr(db, attr) for attr in ("add", "flush")):
        return
    create_audit_log(db, data, commit=False)
