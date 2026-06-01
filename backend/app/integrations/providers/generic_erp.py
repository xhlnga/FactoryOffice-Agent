from app.integrations.core.schemas import BusinessObjectType, BusinessSyncPayload, BusinessSyncResult, IntegrationPlatform
from app.integrations.providers.generic_webhook import GenericBusinessWebhookProvider


class GenericERPProvider(GenericBusinessWebhookProvider):
    """通用 ERP 适配器。

    主要用于采购申请、供应商、预算等对象的外部系统同步。不同企业 ERP 字段差异
    很大，正式落地时应通过字段映射配置处理。
    """

    platform = IntegrationPlatform.GENERIC_ERP
    external_system_name = "ERP"

    def create_purchase_request(
        self,
        *,
        local_id: int,
        payload: dict,
        idempotency_key: str | None = None,
    ) -> BusinessSyncResult:
        """创建或推送 ERP 采购申请。"""
        return self.push_business_object(
            BusinessSyncPayload(
                object_type=BusinessObjectType.PURCHASE_REQUEST,
                local_id=local_id,
                payload=payload,
                external_system=self.platform,
                idempotency_key=idempotency_key,
            )
        )

    def update_purchase_status(
        self,
        *,
        local_id: int,
        payload: dict,
        idempotency_key: str | None = None,
    ) -> BusinessSyncResult:
        """同步 ERP 采购申请状态。"""
        return self.push_business_object(
            BusinessSyncPayload(
                object_type=BusinessObjectType.PURCHASE_REQUEST,
                local_id=local_id,
                payload={"action": "update_status", **payload},
                external_system=self.platform,
                idempotency_key=idempotency_key,
            )
        )
