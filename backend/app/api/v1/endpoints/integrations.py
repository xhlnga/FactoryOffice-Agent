from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import UserRole, require_role
from app.integrations.core.schemas import IntegrationPlatform
from app.integrations.services.notification_service import NotificationService
from app.integrations.services.org_sync_service import OrgSyncService
from app.models.base import IntegrationConfigStatus
from app.models.integration_config import IntegrationConfig
from app.models.notification_delivery import NotificationDelivery
from app.schemas.integration import (
    IntegrationConfigCreateRequest,
    IntegrationConfigRead,
    IntegrationConfigUpdateRequest,
    IntegrationTestRequest,
    IntegrationTestResponse,
    NotificationDeliveryRead,
)

router = APIRouter()


@router.get("", summary="获取企业集成配置列表")
def list_integration_configs(
    platform: IntegrationPlatform | None = Query(default=None, description="平台类型"),
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """分页查询企业集成配置。"""
    query = select(IntegrationConfig)
    count_query = select(func.count()).select_from(IntegrationConfig)
    if platform is not None:
        query = query.where(IntegrationConfig.platform == platform.value)
        count_query = count_query.where(IntegrationConfig.platform == platform.value)

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(IntegrationConfig.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "items": [IntegrationConfigRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "企业集成配置查询成功。",
    }


@router.post("", summary="创建企业集成配置")
def create_integration_config(
    request: IntegrationConfigCreateRequest,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """创建企业微信、钉钉、飞书或通用 Webhook 配置。"""
    config = IntegrationConfig(
        enterprise_id=request.enterprise_id,
        platform=request.platform.value,
        name=request.name,
        status=IntegrationConfigStatus.ACTIVE if request.enabled else IntegrationConfigStatus.DISABLED,
        corp_id=request.corp_id,
        app_key=request.app_key,
        agent_id=request.agent_id,
        encrypted_config=request.encrypted_config,
        webhook_url=request.webhook_url,
        callback_url=request.callback_url,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return {
        "config": IntegrationConfigRead.model_validate(config).model_dump(mode="json"),
        "message": "企业集成配置创建成功。",
    }


@router.get("/deliveries", summary="获取通知投递记录")
def list_notification_deliveries(
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """查询审批通知、测试通知等投递记录。"""
    total = db.scalar(select(func.count()).select_from(NotificationDelivery)) or 0
    items = db.scalars(
        select(NotificationDelivery)
        .order_by(NotificationDelivery.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "items": [NotificationDeliveryRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "通知投递记录查询成功。",
    }


@router.patch("/{config_id}", summary="更新企业集成配置")
def update_integration_config(
    config_id: int,
    request: IntegrationConfigUpdateRequest,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """更新企业集成配置。"""
    config = _get_config(db, config_id)
    update_data = request.model_dump(exclude_unset=True)
    enabled = update_data.pop("enabled", None)
    if enabled is not None:
        config.status = IntegrationConfigStatus.ACTIVE if enabled else IntegrationConfigStatus.DISABLED
    for field, value in update_data.items():
        if field == "encrypted_config" and value is None:
            value = {}
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return {
        "config": IntegrationConfigRead.model_validate(config).model_dump(mode="json"),
        "message": "企业集成配置更新成功。",
    }


@router.post("/{config_id}/enable", summary="启用企业集成配置")
def enable_integration_config(
    config_id: int,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """启用配置，后续审批创建会优先使用已启用配置发送通知。"""
    config = _get_config(db, config_id)
    config.status = IntegrationConfigStatus.ACTIVE
    db.commit()
    db.refresh(config)
    return {
        "config": IntegrationConfigRead.model_validate(config).model_dump(mode="json"),
        "message": "企业集成配置已启用。",
    }


@router.post("/{config_id}/disable", summary="停用企业集成配置")
def disable_integration_config(
    config_id: int,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """停用配置，后续不会使用该配置发送通知。"""
    config = _get_config(db, config_id)
    config.status = IntegrationConfigStatus.DISABLED
    db.commit()
    db.refresh(config)
    return {
        "config": IntegrationConfigRead.model_validate(config).model_dump(mode="json"),
        "message": "企业集成配置已停用。",
    }


@router.post("/{config_id}/test", summary="测试企业集成通知")
def test_integration_config(
    config_id: int,
    request: IntegrationTestRequest,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> IntegrationTestResponse:
    """发送一条测试通知，并记录投递结果。"""
    config = _get_config(db, config_id)
    try:
        platform = IntegrationPlatform(config.platform)
    except ValueError as exc:
        raise AppException(
            "集成平台类型不受支持。",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"platform": config.platform},
        ) from exc

    provider_config = _provider_config(config)
    result = NotificationService().send_message(
        db=db,
        platform=platform,
        title=request.title,
        content=request.content,
        config=provider_config,
        enterprise_id=config.enterprise_id,
        business_type="integration_test",
        business_id=config.id,
        action_url=request.action_url,
        commit=True,
    )
    config.last_health_status = "success" if result.success else "failed"
    db.commit()
    return IntegrationTestResponse(
        success=result.success,
        message="测试通知发送成功。" if result.success else "测试通知发送失败，请查看投递记录。",
        delivery_id=result.metadata.get("delivery_id"),
        response_code=result.response_code,
        response_body=result.response_body,
        error_message=result.error_message,
    )


@router.post("/{config_id}/org/preview", summary="预览组织架构同步")
def preview_org_sync(
    config_id: int,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """从配置对应 Provider 读取部门和人员快照，不写入数据库。"""
    config = _get_config(db, config_id)
    platform = IntegrationPlatform(config.platform)
    return {
        "preview": OrgSyncService().preview(
            platform=platform,
            config=_provider_config(config),
            enterprise_id=config.enterprise_id,
        ),
        "message": "组织架构同步预览生成成功。",
    }


@router.post("/{config_id}/org/sync", summary="执行组织架构同步")
def run_org_sync(
    config_id: int,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """执行组织架构同步，并按外部用户/部门 ID 落库。"""
    config = _get_config(db, config_id)
    platform = IntegrationPlatform(config.platform)
    result = OrgSyncService().sync(
        platform=platform,
        config=_provider_config(config),
        enterprise_id=config.enterprise_id,
        db=db,
    )
    return {
        "result": result.model_dump(mode="json"),
        "message": result.message,
    }


def _get_config(db: Session, config_id: int) -> IntegrationConfig:
    config = db.get(IntegrationConfig, config_id)
    if config is None:
        raise AppException("企业集成配置不存在。", status_code=status.HTTP_404_NOT_FOUND)
    return config


def _provider_config(config: IntegrationConfig) -> dict:
    provider_config = dict(config.encrypted_config or {})
    if config.webhook_url:
        provider_config["webhook_url"] = config.webhook_url
    return provider_config
