from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, require_role
from app.schemas.approval_template import (
    ApprovalTemplateCreateRequest,
    ApprovalTemplateRead,
    ApprovalTemplateUpdateRequest,
)
from app.services.approval_engine import (
    create_approval_template,
    get_approval_template,
    list_approval_templates,
    update_approval_template,
)

router = APIRouter()


@router.get("", summary="获取审批模板列表")
def list_templates(
    business_type: str | None = Query(default=None, description="业务类型"),
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """分页查询审批模板，可按业务类型过滤。"""
    items, total = list_approval_templates(db, business_type=business_type, offset=offset, limit=limit)
    return {
        "items": [ApprovalTemplateRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "审批模板列表查询成功。",
    }


@router.post("", summary="创建审批模板")
def create_template(
    request: ApprovalTemplateCreateRequest,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """创建多级审批模板。"""
    template = create_approval_template(db, request)
    return {
        "template": ApprovalTemplateRead.model_validate(template).model_dump(mode="json"),
        "message": "审批模板创建成功。",
    }


@router.get("/{template_id}", summary="获取审批模板详情")
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """查询审批模板详情。"""
    template = get_approval_template(db, template_id)
    return {
        "template": ApprovalTemplateRead.model_validate(template).model_dump(mode="json"),
        "message": "审批模板详情查询成功。",
    }


@router.patch("/{template_id}", summary="更新审批模板")
def update_template(
    template_id: int,
    request: ApprovalTemplateUpdateRequest,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """更新审批模板基础信息。"""
    template = update_approval_template(db, template_id, request)
    return {
        "template": ApprovalTemplateRead.model_validate(template).model_dump(mode="json"),
        "message": "审批模板更新成功。",
    }
