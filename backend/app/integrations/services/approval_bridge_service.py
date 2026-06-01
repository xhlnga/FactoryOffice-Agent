from app.integrations.core.base import ApprovalProvider, BaseIntegrationProvider
from app.integrations.core.idempotency import InMemoryIdempotencyStore, build_idempotency_key
from app.integrations.core.registry import IntegrationProviderRegistry, provider_registry
from app.integrations.core.schemas import (
    ApprovalCallbackAction,
    ApprovalCallbackEvent,
    ApprovalTaskPayload,
    ApprovalTaskResult,
    IdempotencyCheckResult,
    IntegrationCapability,
    IntegrationPlatform,
    ProviderContext,
)
from app.integrations.providers import register_builtin_providers
from app.models.base import ApprovalStatus


class ApprovalBridgeService:
    """外部审批桥接服务。

    负责把本系统审批任务投递到外部平台，并把外部回调解析为内部事件。
    """

    def __init__(
        self,
        registry: IntegrationProviderRegistry | None = None,
        idempotency_store: InMemoryIdempotencyStore | None = None,
    ) -> None:
        if registry is None:
            register_builtin_providers(replace=True)
        self.registry = registry or provider_registry
        self.idempotency_store = idempotency_store or InMemoryIdempotencyStore()

    def create_external_approval(
        self,
        *,
        platform: IntegrationPlatform,
        approval_id: int,
        title: str,
        summary: str,
        business_type: str,
        config: dict | None = None,
        enterprise_id: int | None = None,
        applicant_user_id: int | None = None,
        approver_user_ids: list[int] | None = None,
        business_id: int | str | None = None,
        action_url: str | None = None,
        payload: dict | None = None,
    ) -> ApprovalTaskResult:
        """创建外部审批待办或审批卡片。"""
        provider = self._approval_provider(platform, config=config, enterprise_id=enterprise_id)
        return provider.create_approval_task(
            ApprovalTaskPayload(
                approval_id=approval_id,
                title=title,
                summary=summary,
                applicant_user_id=applicant_user_id,
                approver_user_ids=approver_user_ids or [],
                business_type=business_type,
                business_id=business_id,
                action_url=action_url,
                payload=payload or {},
            )
        )

    def parse_callback(
        self,
        *,
        platform: IntegrationPlatform,
        raw_payload: dict,
        config: dict | None = None,
        enterprise_id: int | None = None,
    ) -> ApprovalCallbackEvent:
        """解析外部审批回调。"""
        provider = self._approval_provider(platform, config=config, enterprise_id=enterprise_id)
        return provider.parse_callback(raw_payload)

    def parse_callback_once(
        self,
        *,
        platform: IntegrationPlatform,
        raw_payload: dict,
        config: dict | None = None,
        enterprise_id: int | None = None,
        external_event_id: str | None = None,
    ) -> tuple[ApprovalCallbackEvent | None, IdempotencyCheckResult]:
        """带幂等保护地解析外部审批回调。"""
        key = build_idempotency_key(
            provider=platform.value,
            event_type="approval_callback",
            external_event_id=external_event_id,
            payload=raw_payload,
        )
        check_result = self.idempotency_store.check(key)
        if check_result.duplicated:
            return None, check_result

        event = self.parse_callback(
            platform=platform,
            raw_payload=raw_payload,
            config=config,
            enterprise_id=enterprise_id,
        )
        mark_result = self.idempotency_store.mark_processed(
            key,
            {
                "local_approval_id": event.local_approval_id,
                "action": event.action.value,
            },
        )
        return event, mark_result

    def map_callback_to_local_status(self, event: ApprovalCallbackEvent) -> ApprovalStatus | None:
        """把外部审批动作映射为本地审批状态。"""
        if event.action == ApprovalCallbackAction.APPROVE:
            return ApprovalStatus.APPROVED
        if event.action == ApprovalCallbackAction.REJECT:
            return ApprovalStatus.REJECTED
        return None

    def _approval_provider(
        self,
        platform: IntegrationPlatform,
        *,
        config: dict | None,
        enterprise_id: int | None,
    ) -> ApprovalProvider:
        provider: BaseIntegrationProvider = self.registry.get(
            platform,
            ProviderContext(platform=platform, enterprise_id=enterprise_id, config=config or {}),
        )
        provider.ensure_capability(IntegrationCapability.APPROVAL)
        return provider  # type: ignore[return-value]
