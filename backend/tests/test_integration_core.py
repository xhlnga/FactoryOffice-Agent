import unittest

from app.integrations.core.base import NotificationProvider
from app.integrations.core.exceptions import IntegrationCapabilityError, IntegrationNotImplementedError
from app.integrations.core.idempotency import (
    InMemoryIdempotencyStore,
    build_business_idempotency_key,
    build_idempotency_key,
)
from app.integrations.core.registry import IntegrationProviderRegistry
from app.integrations.core.schemas import (
    IntegrationCapability,
    IntegrationPlatform,
    NotificationMessage,
    ProviderContext,
)


class DemoNotificationProvider(NotificationProvider):
    """测试用通知 Provider。"""

    platform = IntegrationPlatform.GENERIC_WEBHOOK


class IntegrationCoreTest(unittest.TestCase):
    """企业集成核心抽象测试。"""

    def test_registry_returns_provider_by_platform(self) -> None:
        registry = IntegrationProviderRegistry()
        context = ProviderContext(platform=IntegrationPlatform.GENERIC_WEBHOOK, enterprise_id=1)
        registry.register(IntegrationPlatform.GENERIC_WEBHOOK, DemoNotificationProvider)

        provider = registry.get(IntegrationPlatform.GENERIC_WEBHOOK, context)

        self.assertIsInstance(provider, DemoNotificationProvider)
        self.assertEqual(provider.enterprise_id, 1)

    def test_provider_capability_check_is_explicit(self) -> None:
        provider = DemoNotificationProvider(
            ProviderContext(platform=IntegrationPlatform.GENERIC_WEBHOOK),
        )

        self.assertTrue(provider.supports(IntegrationCapability.NOTIFICATION))
        with self.assertRaises(IntegrationCapabilityError):
            provider.ensure_capability(IntegrationCapability.ORG)

    def test_unimplemented_provider_action_raises_clear_error(self) -> None:
        provider = DemoNotificationProvider(
            ProviderContext(platform=IntegrationPlatform.GENERIC_WEBHOOK),
        )

        with self.assertRaises(IntegrationNotImplementedError):
            provider.send_message(NotificationMessage(title="待审批", content="有新的采购申请待审批。"))

    def test_idempotency_key_is_stable_for_same_payload(self) -> None:
        first = build_idempotency_key(
            provider="generic_webhook",
            event_type="approval_callback",
            payload={"approval_id": 1, "action": "approve"},
        )
        second = build_idempotency_key(
            provider="generic_webhook",
            event_type="approval_callback",
            payload={"action": "approve", "approval_id": 1},
        )

        self.assertEqual(first, second)

    def test_in_memory_idempotency_store_marks_duplicate(self) -> None:
        store = InMemoryIdempotencyStore()
        key = build_business_idempotency_key(
            provider="generic_erp",
            object_type="purchase_request",
            local_id=12,
            action="push",
        )

        first = store.mark_processed(key, {"external_id": "ERP-12"})
        second = store.check(key)

        self.assertFalse(first.duplicated)
        self.assertTrue(second.duplicated)
        self.assertEqual(second.previous_result, {"external_id": "ERP-12"})


if __name__ == "__main__":
    unittest.main()
