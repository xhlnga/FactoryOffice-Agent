from abc import ABC
from datetime import datetime, timezone

from app.integrations.core.exceptions import IntegrationCapabilityError, IntegrationNotImplementedError
from app.integrations.core.schemas import (
    ApprovalCallbackEvent,
    ApprovalTaskPayload,
    ApprovalTaskResult,
    BusinessSyncPayload,
    BusinessSyncResult,
    DepartmentRecord,
    ExternalUserProfile,
    IdentityAuthCode,
    IntegrationCapability,
    IntegrationPlatform,
    InteractiveCard,
    NotificationDeliveryResult,
    NotificationMessage,
    OrgSyncResult,
    ProviderContext,
    ProviderHealthCheck,
    UserRecord,
)


class BaseIntegrationProvider(ABC):
    """企业集成 Provider 基类。

    业务层只依赖这些抽象接口。具体平台差异，例如 access_token、回调验签、
    卡片消息格式，由各 provider 自己处理。
    """

    platform: IntegrationPlatform = IntegrationPlatform.LOCAL
    capabilities: frozenset[IntegrationCapability] = frozenset()

    def __init__(self, context: ProviderContext) -> None:
        self.context = context

    @property
    def enterprise_id(self) -> int | None:
        """当前企业/租户 ID。"""
        return self.context.enterprise_id

    def supports(self, capability: IntegrationCapability) -> bool:
        """判断 provider 是否支持某项能力。"""
        return capability in self.capabilities

    def ensure_capability(self, capability: IntegrationCapability) -> None:
        """业务调用前显式检查能力，避免误用 provider。"""
        if not self.supports(capability):
            raise IntegrationCapabilityError(self.platform.value, capability.value)

    def health_check(self) -> ProviderHealthCheck:
        """健康检查。

        基类只确认 provider 已创建；真实平台 provider 应覆盖此方法并检查 token、
        webhook、回调地址或外部系统可用性。
        """
        return ProviderHealthCheck(
            platform=self.platform,
            healthy=True,
            message="Provider 已加载，尚未执行外部平台连通性检查。",
            checked_at=datetime.now(timezone.utc),
        )


class NotificationProvider(BaseIntegrationProvider):
    """通知 Provider，负责企业微信/钉钉/飞书/webhook 消息发送。"""

    capabilities = frozenset({IntegrationCapability.NOTIFICATION})

    def send_message(self, message: NotificationMessage) -> NotificationDeliveryResult:
        """发送普通通知。"""
        raise IntegrationNotImplementedError(self.platform.value, "send_message")

    def send_interactive_card(self, card: InteractiveCard) -> NotificationDeliveryResult:
        """发送交互卡片。"""
        raise IntegrationNotImplementedError(self.platform.value, "send_interactive_card")


class IdentityProvider(BaseIntegrationProvider):
    """身份 Provider，负责企业登录和用户身份换取。"""

    capabilities = frozenset({IntegrationCapability.IDENTITY})

    def exchange_code_for_user(self, auth_code: IdentityAuthCode) -> ExternalUserProfile:
        """用企业平台授权码换取用户信息。"""
        raise IntegrationNotImplementedError(self.platform.value, "exchange_code_for_user")

    def get_user_profile(self, external_user_id: str) -> ExternalUserProfile:
        """根据外部用户 ID 查询用户信息。"""
        raise IntegrationNotImplementedError(self.platform.value, "get_user_profile")


class OrgProvider(BaseIntegrationProvider):
    """组织 Provider，负责同步部门和人员。"""

    capabilities = frozenset({IntegrationCapability.ORG})

    def list_departments(self) -> list[DepartmentRecord]:
        """获取外部平台部门列表。"""
        raise IntegrationNotImplementedError(self.platform.value, "list_departments")

    def list_users(self, department_external_id: str | None = None) -> list[UserRecord]:
        """获取外部平台用户列表。"""
        raise IntegrationNotImplementedError(self.platform.value, "list_users")

    def sync_all(self) -> OrgSyncResult:
        """同步组织架构。

        默认实现只做读取和计数，真正落库由 org_sync_service 负责。
        """
        departments = self.list_departments()
        users = self.list_users()
        return OrgSyncResult(
            department_count=len(departments),
            user_count=len(users),
            disabled_user_count=sum(1 for user in users if not user.active),
        )


class ApprovalProvider(BaseIntegrationProvider):
    """审批 Provider，负责外部审批任务和审批回调转换。"""

    capabilities = frozenset({IntegrationCapability.APPROVAL})

    def create_approval_task(self, payload: ApprovalTaskPayload) -> ApprovalTaskResult:
        """在外部平台创建审批待办或审批卡片。"""
        raise IntegrationNotImplementedError(self.platform.value, "create_approval_task")

    def parse_callback(self, payload: dict) -> ApprovalCallbackEvent:
        """把外部平台回调转换为内部审批事件。"""
        raise IntegrationNotImplementedError(self.platform.value, "parse_callback")


class BusinessSystemProvider(BaseIntegrationProvider):
    """业务系统 Provider，负责 OA/ERP/MES/WMS 等系统同步。"""

    capabilities = frozenset({IntegrationCapability.BUSINESS})

    def push_business_object(self, payload: BusinessSyncPayload) -> BusinessSyncResult:
        """把本地业务对象写入外部系统。"""
        raise IntegrationNotImplementedError(self.platform.value, "push_business_object")

    def sync_status(self, object_type: str, external_id: str) -> BusinessSyncResult:
        """从外部系统同步状态。"""
        raise IntegrationNotImplementedError(self.platform.value, "sync_status")
