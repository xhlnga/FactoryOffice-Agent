from app.integrations.core.schemas import BusinessObjectType, BusinessSyncPayload, BusinessSyncResult, IntegrationPlatform
from app.integrations.providers.generic_webhook import GenericBusinessWebhookProvider


class GenericWMSProvider(GenericBusinessWebhookProvider):
    """通用 WMS 适配器。

    用于后续接库存、物料、到货、出入库状态查询。当前只提供业务对象推送和状态
    同步骨架，不假设具体 WMS 的表结构。
    """

    platform = IntegrationPlatform.GENERIC_WMS
    external_system_name = "WMS"

    def query_material(self, *, material_code: str) -> BusinessSyncResult:
        """查询物料信息。

        通用适配器用 status_sync 出口表达查询请求；具体 WMS 落地时可替换为真实接口。
        """
        return self.sync_status("material", material_code)

    def query_inventory(self, *, material_code: str) -> BusinessSyncResult:
        """查询库存信息。"""
        return self.sync_status("inventory", material_code)

    def create_material_request(
        self,
        *,
        local_id: int,
        payload: dict,
        idempotency_key: str | None = None,
    ) -> BusinessSyncResult:
        """创建或推送 WMS 物料需求。"""
        return self.push_business_object(
            BusinessSyncPayload(
                object_type=BusinessObjectType.PURCHASE_REQUEST,
                local_id=local_id,
                payload={"wms_action": "material_request", **payload},
                external_system=self.platform,
                idempotency_key=idempotency_key,
            )
        )
