from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.integrations.core.schemas import IntegrationPlatform
from app.models.base import IntegrationConfigStatus, IntegrationEventStatus, NotificationDeliveryStatus
from app.schemas.common import ORMModel


class IntegrationConfigCreateRequest(BaseModel):
    """企业集成配置创建结构。"""

    enterprise_id: int = Field(default=1, ge=1, description="企业 ID")
    platform: IntegrationPlatform = Field(..., description="集成平台")
    name: str = Field(default="default", min_length=1, max_length=128, description="配置名称")
    corp_id: str | None = Field(default=None, max_length=128, description="CorpId 或企业 ID")
    app_key: str | None = Field(default=None, max_length=128, description="应用 Key")
    agent_id: str | None = Field(default=None, max_length=128, description="应用 AgentId")
    webhook_url: str | None = Field(default=None, max_length=512, description="Webhook 地址")
    callback_url: str | None = Field(default=None, max_length=512, description="回调地址")
    encrypted_config: dict[str, Any] = Field(default_factory=dict, description="加密配置或密钥引用")
    enabled: bool = Field(default=False, description="是否启用")

    @model_validator(mode="after")
    def validate_platform_requirements(self) -> "IntegrationConfigCreateRequest":
        """Webhook 类平台必须显式配置发送地址。"""
        if self.platform in {
            IntegrationPlatform.GENERIC_WEBHOOK,
            IntegrationPlatform.DINGTALK,
            IntegrationPlatform.FEISHU,
            IntegrationPlatform.WECOM,
        } and not self.webhook_url:
            raise ValueError("该平台需要配置 webhook_url 才能发送审批通知。")
        return self


class IntegrationConfigUpdateRequest(BaseModel):
    """企业集成配置更新结构。"""

    name: str | None = Field(default=None, min_length=1, max_length=128, description="配置名称")
    corp_id: str | None = Field(default=None, max_length=128, description="CorpId 或企业 ID")
    app_key: str | None = Field(default=None, max_length=128, description="应用 Key")
    agent_id: str | None = Field(default=None, max_length=128, description="应用 AgentId")
    webhook_url: str | None = Field(default=None, max_length=512, description="Webhook 地址")
    callback_url: str | None = Field(default=None, max_length=512, description="回调地址")
    encrypted_config: dict[str, Any] | None = Field(default=None, description="加密配置或密钥引用")
    enabled: bool | None = Field(default=None, description="是否启用")


class IntegrationConfigRead(ORMModel):
    """企业集成配置响应结构。"""

    id: int = Field(..., description="配置 ID")
    enterprise_id: int = Field(..., description="企业 ID")
    platform: str = Field(..., description="集成平台")
    name: str = Field(..., description="配置名称")
    status: IntegrationConfigStatus = Field(..., description="配置状态")
    corp_id: str | None = Field(default=None, description="CorpId 或企业 ID")
    app_key: str | None = Field(default=None, description="应用 Key")
    agent_id: str | None = Field(default=None, description="应用 AgentId")
    webhook_url: str | None = Field(default=None, description="Webhook 地址")
    callback_url: str | None = Field(default=None, description="回调地址")
    encrypted_config: dict[str, Any] = Field(default_factory=dict, description="加密配置或密钥引用")
    last_health_check_at: datetime | None = Field(default=None, description="最后健康检查时间")
    last_health_status: str | None = Field(default=None, description="最后健康检查状态")
    created_at: datetime = Field(..., description="创建时间")


class IntegrationTestRequest(BaseModel):
    """集成连通性测试请求。"""

    title: str = Field(default="FactoryOffice-Agent 集成测试", max_length=120, description="测试标题")
    content: str = Field(default="这是一条企业集成测试通知。", description="测试内容")
    action_url: str | None = Field(default=None, max_length=512, description="可选跳转链接")


class IntegrationTestResponse(BaseModel):
    """集成连通性测试响应。"""

    success: bool = Field(..., description="是否发送成功")
    message: str = Field(..., description="结果说明")
    delivery_id: int | None = Field(default=None, description="通知投递记录 ID")
    response_code: int | None = Field(default=None, description="外部平台响应码")
    response_body: str | None = Field(default=None, description="外部平台响应内容")
    error_message: str | None = Field(default=None, description="错误信息")


class IntegrationEventRead(ORMModel):
    """外部回调事件响应结构。"""

    id: int = Field(..., description="事件 ID")
    enterprise_id: int | None = Field(default=None, description="企业 ID")
    provider: str = Field(..., description="外部平台")
    event_type: str = Field(..., description="事件类型")
    external_event_id: str | None = Field(default=None, description="外部事件 ID")
    status: IntegrationEventStatus = Field(..., description="处理状态")
    retry_count: int = Field(..., description="重试次数")
    last_error: str | None = Field(default=None, description="最后错误")
    processed_at: datetime | None = Field(default=None, description="处理完成时间")
    created_at: datetime = Field(..., description="创建时间")


class NotificationDeliveryRead(ORMModel):
    """通知投递记录响应结构。"""

    id: int = Field(..., description="通知记录 ID")
    enterprise_id: int | None = Field(default=None, description="企业 ID")
    platform: str = Field(..., description="通知平台")
    message_type: str = Field(..., description="消息类型")
    title: str | None = Field(default=None, description="消息标题")
    business_type: str | None = Field(default=None, description="业务类型")
    business_id: str | None = Field(default=None, description="业务 ID")
    status: NotificationDeliveryStatus = Field(..., description="发送状态")
    response_code: int | None = Field(default=None, description="响应码")
    retryable: bool = Field(..., description="是否可重试")
    retry_count: int = Field(..., description="重试次数")
    last_error: str | None = Field(default=None, description="最后错误")
    delivered_at: datetime | None = Field(default=None, description="成功发送时间")
    created_at: datetime = Field(..., description="创建时间")
