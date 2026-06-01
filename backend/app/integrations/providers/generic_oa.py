from app.integrations.core.schemas import BusinessObjectType, BusinessSyncPayload, BusinessSyncResult, IntegrationPlatform
from app.integrations.providers.generic_webhook import GenericBusinessWebhookProvider


class GenericOAProvider(GenericBusinessWebhookProvider):
    """通用 OA 适配器。

    用于把任务、审批结果、周报等办公对象推送到泛 OA 系统。真实项目中通常需要
    根据泛微、蓝凌、致远等系统字段做映射，这里只保留稳定的通用出口。
    """

    platform = IntegrationPlatform.GENERIC_OA
    external_system_name = "OA"

    def create_task(self, *, local_id: int, payload: dict, idempotency_key: str | None = None) -> BusinessSyncResult:
        """创建或推送 OA 任务。"""
        return self.push_business_object(
            BusinessSyncPayload(
                object_type=BusinessObjectType.TASK,
                local_id=local_id,
                payload=payload,
                external_system=self.platform,
                idempotency_key=idempotency_key,
            )
        )

    def update_task_status(
        self,
        *,
        local_id: int,
        payload: dict,
        idempotency_key: str | None = None,
    ) -> BusinessSyncResult:
        """同步 OA 任务状态。"""
        return self.push_business_object(
            BusinessSyncPayload(
                object_type=BusinessObjectType.TASK,
                local_id=local_id,
                payload={"action": "update_status", **payload},
                external_system=self.platform,
                idempotency_key=idempotency_key,
            )
        )
