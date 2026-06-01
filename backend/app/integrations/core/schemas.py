from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IntegrationPlatform(StrEnum):
    """企业集成平台类型。"""

    LOCAL = "local"
    GENERIC_WEBHOOK = "generic_webhook"
    WECOM = "wecom"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
    GENERIC_OA = "generic_oa"
    GENERIC_ERP = "generic_erp"
    GENERIC_MES = "generic_mes"
    GENERIC_WMS = "generic_wms"


class IntegrationCapability(StrEnum):
    """Provider 能力类型。"""

    NOTIFICATION = "notification"
    IDENTITY = "identity"
    ORG = "org"
    APPROVAL = "approval"
    BUSINESS = "business"


class IntegrationEventStatus(StrEnum):
    """集成事件处理状态。"""

    RECEIVED = "received"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    DUPLICATED = "duplicated"
    RETRYING = "retrying"


class NotificationSeverity(StrEnum):
    """通知严重程度，用于决定消息样式和升级策略。"""

    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"


class ApprovalCallbackAction(StrEnum):
    """外部审批回调动作。"""

    APPROVE = "approve"
    REJECT = "reject"
    TRANSFER = "transfer"
    COMMENT = "comment"
    WITHDRAW = "withdraw"


class BusinessObjectType(StrEnum):
    """可同步到外部业务系统的对象类型。"""

    TASK = "task"
    TICKET = "ticket"
    PURCHASE_REQUEST = "purchase_request"
    QUALITY_ISSUE = "quality_issue"
    WEEKLY_REPORT = "weekly_report"
    DOCUMENT = "document"


class ProviderContext(BaseModel):
    """Provider 运行上下文。

    config 由配置服务读取并传入。敏感字段在落库时应加密，日志中不能直接输出。
    """

    platform: IntegrationPlatform
    enterprise_id: int | None = Field(default=None, description="企业/租户 ID")
    config_id: int | None = Field(default=None, description="集成配置 ID")
    config: dict[str, Any] = Field(default_factory=dict, description="平台配置")
    request_id: str | None = Field(default=None, description="请求追踪 ID")


class ProviderHealthCheck(BaseModel):
    """Provider 健康检查结果。"""

    platform: IntegrationPlatform
    healthy: bool
    message: str
    checked_at: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class NotificationRecipient(BaseModel):
    """通知接收人。"""

    user_id: int | None = None
    external_user_id: str | None = None
    department_id: int | None = None
    external_department_id: str | None = None
    name: str | None = None
    mobile_hash: str | None = None
    email: str | None = None


class NotificationMessage(BaseModel):
    """统一通知消息。"""

    title: str = Field(..., min_length=1, max_length=120)
    content: str = Field(..., min_length=1)
    recipients: list[NotificationRecipient] = Field(default_factory=list)
    severity: NotificationSeverity = NotificationSeverity.INFO
    business_type: str | None = None
    business_id: int | str | None = None
    action_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InteractiveCardAction(BaseModel):
    """交互卡片按钮。"""

    key: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=32)
    action_url: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class InteractiveCard(BaseModel):
    """统一交互卡片。

    企业微信、钉钉、飞书的卡片格式不同，Provider 负责把该结构转换为平台格式。
    """

    title: str = Field(..., min_length=1, max_length=120)
    summary: str = Field(..., min_length=1)
    fields: dict[str, Any] = Field(default_factory=dict)
    recipients: list[NotificationRecipient] = Field(default_factory=list)
    actions: list[InteractiveCardAction] = Field(default_factory=list)
    severity: NotificationSeverity = NotificationSeverity.INFO
    business_type: str | None = None
    business_id: int | str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationDeliveryResult(BaseModel):
    """通知发送结果。"""

    success: bool
    provider_message_id: str | None = None
    response_code: int | None = None
    response_body: str | None = None
    retryable: bool = False
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IdentityAuthCode(BaseModel):
    """企业登录授权码。"""

    code: str
    redirect_uri: str | None = None
    state: str | None = None


class ExternalUserProfile(BaseModel):
    """外部平台用户信息。"""

    external_user_id: str
    name: str
    enterprise_id: int | None = None
    external_department_ids: list[str] = Field(default_factory=list)
    mobile_hash: str | None = None
    email: str | None = None
    position: str | None = None
    active: bool = True
    raw: dict[str, Any] = Field(default_factory=dict)


class DepartmentRecord(BaseModel):
    """外部部门记录。"""

    external_department_id: str
    name: str
    parent_external_department_id: str | None = None
    order: int | None = None
    active: bool = True
    raw: dict[str, Any] = Field(default_factory=dict)


class UserRecord(BaseModel):
    """外部用户记录。"""

    external_user_id: str
    name: str
    external_department_ids: list[str] = Field(default_factory=list)
    position: str | None = None
    mobile_hash: str | None = None
    email: str | None = None
    active: bool = True
    raw: dict[str, Any] = Field(default_factory=dict)


class OrgSyncResult(BaseModel):
    """组织架构同步结果。"""

    department_count: int = 0
    user_count: int = 0
    disabled_user_count: int = 0
    message: str = "组织架构同步完成。"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalTaskPayload(BaseModel):
    """发送到外部平台的审批任务。"""

    approval_id: int
    title: str
    summary: str
    applicant_user_id: int | None = None
    approver_user_ids: list[int] = Field(default_factory=list)
    business_type: str
    business_id: int | str | None = None
    action_url: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalTaskResult(BaseModel):
    """外部审批任务创建结果。"""

    success: bool
    external_approval_id: str | None = None
    external_task_id: str | None = None
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalCallbackEvent(BaseModel):
    """外部平台审批回调事件。"""

    platform: IntegrationPlatform
    external_approval_id: str | None = None
    external_task_id: str | None = None
    local_approval_id: int | None = None
    actor_external_user_id: str | None = None
    action: ApprovalCallbackAction
    comment: str | None = None
    event_time: datetime | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class BusinessSyncPayload(BaseModel):
    """同步到外部业务系统的对象。"""

    object_type: BusinessObjectType
    local_id: int
    payload: dict[str, Any]
    external_system: IntegrationPlatform
    idempotency_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessSyncResult(BaseModel):
    """外部业务系统同步结果。"""

    success: bool
    external_id: str | None = None
    sync_status: IntegrationEventStatus = IntegrationEventStatus.SUCCESS
    retryable: bool = False
    error_message: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class IdempotencyCheckResult(BaseModel):
    """幂等检查结果。"""

    key: str
    duplicated: bool
    reason: str | None = None
    previous_result: dict[str, Any] | None = None

