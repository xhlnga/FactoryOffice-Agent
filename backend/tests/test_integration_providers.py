import unittest

from app.integrations.core.exceptions import IntegrationConfigError
from app.integrations.core.registry import IntegrationProviderRegistry
from app.integrations.core.schemas import (
    ApprovalCallbackAction,
    ApprovalTaskPayload,
    BusinessObjectType,
    BusinessSyncPayload,
    IntegrationCapability,
    IntegrationPlatform,
    NotificationMessage,
    ProviderContext,
)
from app.integrations.providers import register_builtin_providers
from app.integrations.providers.dingtalk import DingTalkProvider
from app.integrations.providers.feishu import FeishuProvider
from app.integrations.providers.generic_erp import GenericERPProvider
from app.integrations.providers.generic_webhook import GenericWebhookProvider
from app.integrations.providers.local import LocalIntegrationProvider
from app.integrations.providers.wecom import WeComProvider


class IntegrationProviderTest(unittest.TestCase):
    """企业集成 Provider 测试。"""

    def test_builtin_providers_can_be_registered(self) -> None:
        registry = IntegrationProviderRegistry()
        original_register = register_builtin_providers.__globals__["register_provider"]
        try:
            register_builtin_providers.__globals__["register_provider"] = registry.register
            register_builtin_providers()
        finally:
            register_builtin_providers.__globals__["register_provider"] = original_register

        self.assertEqual(
            set(registry.registered_platforms()),
            {
                IntegrationPlatform.LOCAL,
                IntegrationPlatform.GENERIC_WEBHOOK,
                IntegrationPlatform.WECOM,
                IntegrationPlatform.DINGTALK,
                IntegrationPlatform.FEISHU,
                IntegrationPlatform.GENERIC_OA,
                IntegrationPlatform.GENERIC_ERP,
                IntegrationPlatform.GENERIC_MES,
                IntegrationPlatform.GENERIC_WMS,
            },
        )

    def test_local_provider_supports_demo_closed_loop(self) -> None:
        context = ProviderContext(platform=IntegrationPlatform.LOCAL, enterprise_id=1, config={})
        provider = LocalIntegrationProvider(context)

        delivery = provider.send_message(NotificationMessage(title="审批提醒", content="有一条采购申请待审批。"))
        org_result = provider.sync_all()
        approval_result = provider.create_approval_task(
            ApprovalTaskPayload(
                approval_id=10,
                title="采购申请审批",
                summary="采购 20 个温度传感器。",
                business_type="purchase_request",
            )
        )
        callback = provider.parse_callback({"approval_id": 10, "action": "approve"})
        sync_result = provider.push_business_object(
            BusinessSyncPayload(
                object_type=BusinessObjectType.PURCHASE_REQUEST,
                local_id=10,
                payload={"item_name": "温度传感器"},
                external_system=IntegrationPlatform.LOCAL,
            )
        )

        self.assertTrue(delivery.success)
        self.assertGreaterEqual(org_result.department_count, 1)
        self.assertGreaterEqual(org_result.user_count, 1)
        self.assertTrue(approval_result.success)
        self.assertEqual(callback.action, ApprovalCallbackAction.APPROVE)
        self.assertTrue(sync_result.success)
        self.assertEqual(len(context.config["local_outbox"]), 1)

    def test_generic_webhook_requires_url_before_sending(self) -> None:
        provider = GenericWebhookProvider(ProviderContext(platform=IntegrationPlatform.GENERIC_WEBHOOK))

        with self.assertRaises(IntegrationConfigError):
            provider.send_message(NotificationMessage(title="测试", content="缺少 webhook_url 时不能发送。"))

    def test_generic_webhook_rejects_unsafe_url_scheme(self) -> None:
        provider = GenericWebhookProvider(
            ProviderContext(platform=IntegrationPlatform.GENERIC_WEBHOOK, config={"webhook_url": "file:///tmp/a"})
        )

        with self.assertRaises(IntegrationConfigError):
            provider.send_message(NotificationMessage(title="测试", content="不能调用非 HTTP webhook。"))

    def test_generic_webhook_rejects_localhost_by_default(self) -> None:
        provider = GenericWebhookProvider(
            ProviderContext(platform=IntegrationPlatform.GENERIC_WEBHOOK, config={"webhook_url": "http://localhost:8000"})
        )

        with self.assertRaises(IntegrationConfigError):
            provider.send_message(NotificationMessage(title="测试", content="生产默认不调用 localhost。"))

    def test_platform_notification_providers_report_missing_webhook_as_unhealthy(self) -> None:
        for provider_class, platform in [
            (WeComProvider, IntegrationPlatform.WECOM),
            (DingTalkProvider, IntegrationPlatform.DINGTALK),
            (FeishuProvider, IntegrationPlatform.FEISHU),
        ]:
            provider = provider_class(ProviderContext(platform=platform))
            health = provider.health_check()
            self.assertFalse(health.healthy)
            self.assertTrue(provider.supports(IntegrationCapability.NOTIFICATION))

    def test_generic_business_provider_only_claims_business_capability(self) -> None:
        provider = GenericERPProvider(ProviderContext(platform=IntegrationPlatform.GENERIC_ERP))

        self.assertTrue(provider.supports(IntegrationCapability.BUSINESS))
        self.assertFalse(provider.supports(IntegrationCapability.NOTIFICATION))
        health = provider.health_check()
        self.assertFalse(health.healthy)


if __name__ == "__main__":
    unittest.main()
