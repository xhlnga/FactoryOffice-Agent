from app.integrations.core.schemas import BusinessObjectType, BusinessSyncPayload, BusinessSyncResult, IntegrationPlatform
from app.integrations.providers.generic_webhook import GenericBusinessWebhookProvider


class GenericMESProvider(GenericBusinessWebhookProvider):
    """通用 MES 适配器。

    主要用于设备维修工单、质量异常、停线影响等生产现场对象同步。MES 不同厂商
    差异较大，所以这里先保留 HTTP 出口和外部 ID 回写能力。
    """

    platform = IntegrationPlatform.GENERIC_MES
    external_system_name = "MES"

    def create_maintenance_ticket(
        self,
        *,
        local_id: int,
        payload: dict,
        idempotency_key: str | None = None,
    ) -> BusinessSyncResult:
        """创建或推送 MES 设备维修工单。"""
        return self.push_business_object(
            BusinessSyncPayload(
                object_type=BusinessObjectType.TICKET,
                local_id=local_id,
                payload=payload,
                external_system=self.platform,
                idempotency_key=idempotency_key,
            )
        )

    def create_quality_issue(
        self,
        *,
        local_id: int,
        payload: dict,
        idempotency_key: str | None = None,
    ) -> BusinessSyncResult:
        """创建或推送 MES/QMS 质量异常工单。"""
        return self.push_business_object(
            BusinessSyncPayload(
                object_type=BusinessObjectType.QUALITY_ISSUE,
                local_id=local_id,
                payload=payload,
                external_system=self.platform,
                idempotency_key=idempotency_key,
            )
        )

    def update_ticket_status(
        self,
        *,
        local_id: int,
        payload: dict,
        idempotency_key: str | None = None,
    ) -> BusinessSyncResult:
        """同步 MES 工单状态。"""
        return self.push_business_object(
            BusinessSyncPayload(
                object_type=BusinessObjectType.TICKET,
                local_id=local_id,
                payload={"action": "update_status", **payload},
                external_system=self.platform,
                idempotency_key=idempotency_key,
            )
        )
