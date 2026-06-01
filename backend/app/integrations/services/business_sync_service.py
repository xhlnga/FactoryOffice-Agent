from app.integrations.core.base import BaseIntegrationProvider, BusinessSystemProvider
from app.integrations.core.idempotency import build_business_idempotency_key
from app.integrations.core.registry import IntegrationProviderRegistry, provider_registry
from app.integrations.core.schemas import (
    BusinessObjectType,
    BusinessSyncPayload,
    BusinessSyncResult,
    IntegrationCapability,
    IntegrationPlatform,
    ProviderContext,
)
from app.integrations.providers import register_builtin_providers


class BusinessSyncService:
    """外部业务系统同步服务。

    负责把任务、工单、采购申请、质量异常等对象写入外部 OA/ERP/MES/WMS。
    """

    def __init__(self, registry: IntegrationProviderRegistry | None = None) -> None:
        if registry is None:
            register_builtin_providers(replace=True)
        self.registry = registry or provider_registry

    def push_object(
        self,
        *,
        platform: IntegrationPlatform,
        object_type: BusinessObjectType,
        local_id: int,
        payload: dict,
        config: dict | None = None,
        enterprise_id: int | None = None,
        idempotency_key: str | None = None,
        metadata: dict | None = None,
    ) -> BusinessSyncResult:
        """推送业务对象到外部系统。"""
        provider = self._business_provider(platform, config=config, enterprise_id=enterprise_id)
        final_key = idempotency_key or build_business_idempotency_key(
            provider=platform.value,
            object_type=object_type.value,
            local_id=local_id,
            action="push",
        )
        return provider.push_business_object(
            BusinessSyncPayload(
                object_type=object_type,
                local_id=local_id,
                payload=payload,
                external_system=platform,
                idempotency_key=final_key,
                metadata=metadata or {},
            )
        )

    def sync_status(
        self,
        *,
        platform: IntegrationPlatform,
        object_type: str,
        external_id: str,
        config: dict | None = None,
        enterprise_id: int | None = None,
    ) -> BusinessSyncResult:
        """从外部系统同步业务对象状态。"""
        provider = self._business_provider(platform, config=config, enterprise_id=enterprise_id)
        return provider.sync_status(object_type, external_id)

    def _business_provider(
        self,
        platform: IntegrationPlatform,
        *,
        config: dict | None,
        enterprise_id: int | None,
    ) -> BusinessSystemProvider:
        provider: BaseIntegrationProvider = self.registry.get(
            platform,
            ProviderContext(platform=platform, enterprise_id=enterprise_id, config=config or {}),
        )
        provider.ensure_capability(IntegrationCapability.BUSINESS)
        return provider  # type: ignore[return-value]
