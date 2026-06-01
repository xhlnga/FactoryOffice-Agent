from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.approval import Approval
from app.models.approval_action import ApprovalAction
from app.models.approval_instance import ApprovalInstance
from app.models.approval_instance_step import ApprovalInstanceStep
from app.models.approval_step import ApprovalStep
from app.models.approval_template import ApprovalTemplate
from app.models.base import (
    ApprovalActionType,
    ApprovalInstanceStatus,
    ApprovalStepMode,
    ApprovalStepStatus,
    ApprovalTemplateStatus,
    ApproverType,
    utc_now,
)
from app.schemas.approval_template import (
    ApprovalTemplateCreateRequest,
    ApprovalTemplateUpdateRequest,
)


def create_approval_template(db: Session, data: ApprovalTemplateCreateRequest) -> ApprovalTemplate:
    """创建审批模板和模板步骤。"""
    template = ApprovalTemplate(
        enterprise_id=data.enterprise_id,
        name=data.name,
        business_type=data.business_type,
        description=data.description,
        min_amount=data.min_amount,
        max_amount=data.max_amount,
        status=data.status,
        is_default=data.is_default,
    )
    template.steps = [
        ApprovalStep(
            step_order=step.step_order,
            name=step.name,
            approver_type=step.approver_type,
            approver_value=step.approver_value,
            mode=step.mode,
            timeout_hours=step.timeout_hours,
            escalate_to=step.escalate_to,
        )
        for step in sorted(data.steps, key=lambda item: item.step_order)
    ]
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_approval_template(
    db: Session,
    template_id: int,
    data: ApprovalTemplateUpdateRequest,
) -> ApprovalTemplate:
    """更新审批模板基础字段；步骤调整建议通过重新创建模板完成。"""
    template = get_approval_template(db, template_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


def list_approval_templates(
    db: Session,
    *,
    business_type: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[ApprovalTemplate], int]:
    """分页查询审批模板。"""
    query = select(ApprovalTemplate)
    count_query = select(func.count()).select_from(ApprovalTemplate)
    if business_type:
        query = query.where(ApprovalTemplate.business_type == business_type)
        count_query = count_query.where(ApprovalTemplate.business_type == business_type)

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(ApprovalTemplate.business_type.asc(), ApprovalTemplate.min_amount.asc().nullsfirst())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(items), total


def get_approval_template(db: Session, template_id: int) -> ApprovalTemplate:
    """查询审批模板详情。"""
    template = db.get(ApprovalTemplate, template_id)
    if template is None:
        raise AppException("审批模板不存在。", status_code=status.HTTP_404_NOT_FOUND)
    return template


def select_template_for_action(
    db: Session,
    *,
    business_type: str,
    payload: dict[str, Any],
    enterprise_id: int | None = None,
) -> ApprovalTemplate | None:
    """根据业务类型和金额阈值选择审批模板。"""
    amount = _extract_amount(payload)
    query = select(ApprovalTemplate).where(
        ApprovalTemplate.business_type == business_type,
        ApprovalTemplate.status == ApprovalTemplateStatus.ENABLED,
    )
    if enterprise_id is None:
        query = query.where(ApprovalTemplate.enterprise_id.is_(None) | (ApprovalTemplate.enterprise_id == 1))
    else:
        query = query.where(or_(ApprovalTemplate.enterprise_id == enterprise_id, ApprovalTemplate.enterprise_id.is_(None)))
    if amount is not None:
        query = query.where(
            or_(ApprovalTemplate.min_amount.is_(None), ApprovalTemplate.min_amount <= amount),
            or_(ApprovalTemplate.max_amount.is_(None), amount < ApprovalTemplate.max_amount),
        )
    else:
        # 金额缺失时不能误选高金额审批流；企业里应走默认/无金额模板，或由补槽流程要求补金额。
        query = query.where(
            or_(
                ApprovalTemplate.is_default.is_(True),
                (ApprovalTemplate.min_amount.is_(None) & ApprovalTemplate.max_amount.is_(None)),
            )
        )

    query = _order_template_candidates(query)
    return db.scalars(query).first()


def create_instance_for_approval(
    db: Session,
    approval: Approval,
    *,
    enterprise_id: int | None = 1,
    created_by: str | None = None,
    commit: bool = False,
) -> ApprovalInstance | None:
    """为兼容审批创建审批引擎实例；轻量测试替身不支持写入时直接跳过。"""
    if not all(hasattr(db, attr) for attr in ("add", "flush")):
        return None

    template = select_template_for_action(
        db,
        business_type=approval.action_type,
        payload=approval.action_payload,
        enterprise_id=enterprise_id,
    )
    instance = ApprovalInstance(
        template_id=template.id if template else None,
        approval_id=approval.id,
        enterprise_id=enterprise_id,
        business_type=approval.action_type,
        business_id=str(approval.id),
        title=_build_instance_title(approval),
        status=ApprovalInstanceStatus.PENDING,
        current_step_order=None,
        created_by=created_by,
    )
    db.add(instance)
    db.flush()

    instance_steps = _build_instance_steps(instance.id, template)
    for step in instance_steps:
        db.add(step)
    if instance_steps:
        instance.current_step_order = instance_steps[0].step_order
    db.flush()

    _record_action(
        db,
        instance_id=instance.id,
        step_id=None,
        actor_name=created_by or "system",
        action=ApprovalActionType.COMMENT,
        comment="审批实例已创建。",
        action_metadata={"source": "approval_service"},
    )
    if commit:
        db.commit()
        db.refresh(instance)
    return instance


def approve_instance_for_approval(
    db: Session,
    approval: Approval,
    *,
    actor_name: str,
    comment: str = "",
    commit: bool = False,
) -> ApprovalInstance | None:
    """批准兼容审批关联的当前审批步骤。"""
    instance = _get_instance_by_approval(db, approval.id)
    if instance is None:
        return None
    approve_current_step(db, instance.id, actor_name=actor_name, comment=comment, commit=commit)
    return instance


def reject_instance_for_approval(
    db: Session,
    approval: Approval,
    *,
    actor_name: str,
    comment: str = "",
    commit: bool = False,
) -> ApprovalInstance | None:
    """拒绝兼容审批关联的审批实例。"""
    instance = _get_instance_by_approval(db, approval.id)
    if instance is None:
        return None
    reject_instance(db, instance.id, actor_name=actor_name, comment=comment, commit=commit)
    return instance


def approve_current_step(
    db: Session,
    instance_id: int,
    *,
    actor_name: str,
    comment: str = "",
    commit: bool = True,
) -> ApprovalInstance:
    """批准当前步骤，若还有下一步则推进，否则实例完成。"""
    instance = get_approval_instance(db, instance_id)
    _ensure_instance_pending(instance)
    step = _current_pending_step(instance)
    step.status = ApprovalStepStatus.APPROVED
    step.approved_at = utc_now()
    step.comment = comment
    _record_action(
        db,
        instance_id=instance.id,
        step_id=step.id,
        actor_name=actor_name,
        action=ApprovalActionType.APPROVE,
        comment=comment,
    )

    if step.mode == ApprovalStepMode.ANY:
        _skip_same_order_pending_steps(instance, step)
    next_step = _next_pending_step(
        instance,
        after_order=step.step_order,
        include_same_order=step.mode == ApprovalStepMode.ALL,
    )
    if next_step is None:
        instance.status = ApprovalInstanceStatus.APPROVED
        instance.completed_at = utc_now()
        instance.current_step_order = None
    else:
        instance.current_step_order = next_step.step_order
    if commit:
        db.commit()
        db.refresh(instance)
    return instance


def reject_instance(
    db: Session,
    instance_id: int,
    *,
    actor_name: str,
    comment: str = "",
    commit: bool = True,
) -> ApprovalInstance:
    """驳回审批实例。"""
    instance = get_approval_instance(db, instance_id)
    _ensure_instance_pending(instance)
    step = _current_pending_step(instance)
    step.status = ApprovalStepStatus.REJECTED
    step.comment = comment
    instance.status = ApprovalInstanceStatus.REJECTED
    instance.completed_at = utc_now()
    _record_action(
        db,
        instance_id=instance.id,
        step_id=step.id,
        actor_name=actor_name,
        action=ApprovalActionType.REJECT,
        comment=comment,
    )
    if commit:
        db.commit()
        db.refresh(instance)
    return instance


def transfer_current_step(
    db: Session,
    instance_id: int,
    *,
    actor_name: str,
    to_approver: str,
    comment: str = "",
    commit: bool = True,
) -> ApprovalInstance:
    """转交当前步骤。"""
    instance = get_approval_instance(db, instance_id)
    _ensure_instance_pending(instance)
    step = _current_pending_step(instance)
    from_approver = step.assigned_to or step.approver_value
    step.status = ApprovalStepStatus.TRANSFERRED
    step.assigned_to = to_approver
    instance.status = ApprovalInstanceStatus.TRANSFERRED
    _record_action(
        db,
        instance_id=instance.id,
        step_id=step.id,
        actor_name=actor_name,
        action=ApprovalActionType.TRANSFER,
        comment=comment,
        from_approver=from_approver,
        to_approver=to_approver,
    )
    # 转交后仍需继续审批，因此把实例恢复为待审批状态。
    instance.status = ApprovalInstanceStatus.PENDING
    step.status = ApprovalStepStatus.PENDING
    if commit:
        db.commit()
        db.refresh(instance)
    return instance


def withdraw_instance(
    db: Session,
    instance_id: int,
    *,
    actor_name: str,
    comment: str = "",
    commit: bool = True,
) -> ApprovalInstance:
    """撤回审批实例。"""
    instance = get_approval_instance(db, instance_id)
    _ensure_instance_pending(instance)
    instance.status = ApprovalInstanceStatus.WITHDRAWN
    instance.withdrawn_at = utc_now()
    instance.completed_at = utc_now()
    _record_action(
        db,
        instance_id=instance.id,
        step_id=None,
        actor_name=actor_name,
        action=ApprovalActionType.WITHDRAW,
        comment=comment,
    )
    if commit:
        db.commit()
        db.refresh(instance)
    return instance


def withdraw_instance_for_approval(
    db: Session,
    approval: Approval,
    *,
    actor_name: str,
    comment: str = "",
    commit: bool = False,
) -> ApprovalInstance | None:
    """撤回兼容审批关联的审批实例。"""
    instance = _get_instance_by_approval(db, approval.id)
    if instance is None:
        return None
    withdraw_instance(db, instance.id, actor_name=actor_name, comment=comment, commit=commit)
    return instance


def escalate_overdue_steps(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 100,
    commit: bool = True,
) -> list[ApprovalInstanceStep]:
    """扫描超时审批步骤，并升级到配置的角色或人员。"""
    current_time = now or utc_now()
    pending_steps = db.scalars(
        select(ApprovalInstanceStep)
        .join(ApprovalInstance)
        .where(
            ApprovalInstance.status == ApprovalInstanceStatus.PENDING,
            ApprovalInstanceStep.status == ApprovalStepStatus.PENDING,
            ApprovalInstanceStep.timeout_hours.is_not(None),
            ApprovalInstanceStep.escalate_to.is_not(None),
        )
        .order_by(ApprovalInstanceStep.created_at.asc())
        .limit(limit)
    ).all()

    escalated_steps: list[ApprovalInstanceStep] = []
    for step in pending_steps:
        base_time = step.created_at or step.instance.created_at
        if not _is_overdue(base_time, current_time, step.timeout_hours):
            continue
        from_approver = step.assigned_to or step.approver_value
        step.assigned_to = step.escalate_to
        escalated_steps.append(step)
        _record_action(
            db,
            instance_id=step.instance_id,
            step_id=step.id,
            actor_name="system",
            action=ApprovalActionType.ESCALATE,
            comment="审批步骤超时，已按模板规则升级。",
            from_approver=from_approver,
            to_approver=step.escalate_to,
            action_metadata={"timeout_hours": step.timeout_hours},
        )
    if commit and escalated_steps:
        db.commit()
    return escalated_steps


def transfer_instance_for_approval(
    db: Session,
    approval: Approval,
    *,
    actor_name: str,
    to_approver: str,
    comment: str = "",
    commit: bool = False,
) -> ApprovalInstance | None:
    """转交兼容审批关联的当前审批步骤。"""
    instance = _get_instance_by_approval(db, approval.id)
    if instance is None:
        return None
    transfer_current_step(db, instance.id, actor_name=actor_name, to_approver=to_approver, comment=comment, commit=commit)
    return instance


def get_approval_instance(db: Session, instance_id: int) -> ApprovalInstance:
    """查询审批实例。"""
    instance = db.get(ApprovalInstance, instance_id)
    if instance is None:
        raise AppException("审批实例不存在。", status_code=status.HTTP_404_NOT_FOUND)
    return instance


def _get_instance_by_approval(db: Session, approval_id: int) -> ApprovalInstance | None:
    if not hasattr(db, "scalars"):
        return None
    return db.scalars(
        select(ApprovalInstance)
        .where(ApprovalInstance.approval_id == approval_id)
        .order_by(ApprovalInstance.created_at.desc())
    ).first()


def _extract_amount(payload: dict[str, Any]) -> float | None:
    for key in ("budget", "budget_amount", "amount", "total_amount"):
        value = payload.get(key)
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return None


def _order_template_candidates(query: Select[tuple[ApprovalTemplate]]) -> Select[tuple[ApprovalTemplate]]:
    return query.order_by(
        ApprovalTemplate.enterprise_id.desc().nullslast(),
        ApprovalTemplate.min_amount.desc().nullslast(),
        ApprovalTemplate.is_default.desc(),
        ApprovalTemplate.id.asc(),
    )


def _build_instance_title(approval: Approval) -> str:
    item_name = approval.action_payload.get("item_name")
    title = approval.action_payload.get("title") or item_name
    if title:
        return f"{approval.action_type}: {title}"
    return f"{approval.action_type} #{approval.id}"


def _build_instance_steps(instance_id: int, template: ApprovalTemplate | None) -> list[ApprovalInstanceStep]:
    if template and template.steps:
        instance_steps: list[ApprovalInstanceStep] = []
        for step in sorted(template.steps, key=lambda item: item.step_order):
            for approver_value in _split_approver_values(step.approver_value):
                instance_steps.append(
                    ApprovalInstanceStep(
                        instance_id=instance_id,
                        template_step_id=step.id,
                        step_order=step.step_order,
                        name=step.name,
                        approver_type=step.approver_type,
                        approver_value=approver_value,
                        assigned_to=approver_value,
                        mode=step.mode,
                        status=ApprovalStepStatus.PENDING,
                        timeout_hours=step.timeout_hours,
                        escalate_to=step.escalate_to,
                    )
                )
        return instance_steps
    return [
        ApprovalInstanceStep(
            instance_id=instance_id,
            template_step_id=None,
            step_order=1,
            name="人工确认",
            approver_type=ApproverType.ROLE,
            approver_value="manager",
            assigned_to="manager",
            mode=ApprovalStepMode.ANY,
            status=ApprovalStepStatus.PENDING,
            timeout_hours=24,
            escalate_to="admin",
        )
    ]


def _record_action(
    db: Session,
    *,
    instance_id: int,
    step_id: int | None,
    actor_name: str,
    action: ApprovalActionType,
    comment: str | None = None,
    from_approver: str | None = None,
    to_approver: str | None = None,
    action_metadata: dict[str, Any] | None = None,
) -> ApprovalAction:
    record = ApprovalAction(
        instance_id=instance_id,
        step_id=step_id,
        actor_name=actor_name,
        action=action,
        comment=comment,
        from_approver=from_approver,
        to_approver=to_approver,
        action_metadata=action_metadata or {},
    )
    db.add(record)
    return record


def _ensure_instance_pending(instance: ApprovalInstance) -> None:
    if instance.status != ApprovalInstanceStatus.PENDING:
        raise AppException("只有待审批实例可以继续处理。", status_code=status.HTTP_409_CONFLICT)


def _current_pending_step(instance: ApprovalInstance) -> ApprovalInstanceStep:
    pending_steps = [step for step in instance.steps if step.status == ApprovalStepStatus.PENDING]
    if not pending_steps:
        raise AppException("审批实例没有待处理步骤。", status_code=status.HTTP_409_CONFLICT)
    if instance.current_step_order is not None:
        for step in pending_steps:
            if step.step_order == instance.current_step_order:
                return step
    return sorted(pending_steps, key=lambda item: item.step_order)[0]


def _next_pending_step(
    instance: ApprovalInstance,
    *,
    after_order: int,
    include_same_order: bool = False,
) -> ApprovalInstanceStep | None:
    candidates = [
        step
        for step in instance.steps
        if step.status == ApprovalStepStatus.PENDING
        and (step.step_order > after_order or (include_same_order and step.step_order == after_order))
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.step_order)[0]


def _skip_same_order_pending_steps(instance: ApprovalInstance, approved_step: ApprovalInstanceStep) -> None:
    for step in instance.steps:
        if step.id == approved_step.id:
            continue
        if step.step_order == approved_step.step_order and step.status == ApprovalStepStatus.PENDING:
            step.status = ApprovalStepStatus.SKIPPED
            step.comment = "同一步骤已由其他审批人通过。"


def _split_approver_values(value: str) -> list[str]:
    values = [item.strip() for item in value.split(",") if item.strip()]
    return values or [value]


def _is_overdue(started_at: datetime | None, now: datetime, timeout_hours: int | None) -> bool:
    if started_at is None or timeout_hours is None:
        return False
    if started_at.tzinfo is None and now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    if started_at.tzinfo is not None and now.tzinfo is None:
        started_at = started_at.replace(tzinfo=None)
    return started_at + timedelta(hours=timeout_hours) <= now
