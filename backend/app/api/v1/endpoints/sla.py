from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, require_role
from app.integrations.services.sla_escalation_service import SLAEscalationService
from app.models.sla import SLAInstance, SLAPolicyModel
from app.schemas.sla import SLADefaultPolicyRead, SLAInstanceRead, SLAPolicyRead

router = APIRouter()


@router.get("/policies", summary="获取 SLA 策略列表")
def list_sla_policies(
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """查询已落库的 SLA 策略。"""
    total = db.scalar(select(func.count()).select_from(SLAPolicyModel)) or 0
    items = db.scalars(
        select(SLAPolicyModel)
        .order_by(SLAPolicyModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "items": [SLAPolicyRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "SLA 策略查询成功。",
    }


@router.get("/instances", summary="获取 SLA 实例列表")
def list_sla_instances(
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """查询 SLA 实例，用于观察提醒和升级状态。"""
    total = db.scalar(select(func.count()).select_from(SLAInstance)) or 0
    items = db.scalars(
        select(SLAInstance)
        .order_by(SLAInstance.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "items": [SLAInstanceRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "SLA 实例查询成功。",
    }


@router.get("/default-policies", summary="获取内置 SLA 策略")
def list_default_sla_policies(
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """返回系统内置的制造业办公 SLA 规则。"""
    policies = SLAEscalationService.DEFAULT_POLICIES.values()
    return {
        "items": [SLADefaultPolicyRead(**policy.__dict__).model_dump(mode="json") for policy in policies],
        "total": len(SLAEscalationService.DEFAULT_POLICIES),
        "message": "内置 SLA 策略查询成功。",
    }
