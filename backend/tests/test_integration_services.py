from datetime import timedelta
import unittest

from app.integrations.core.schemas import (
    BusinessObjectType,
    IntegrationPlatform,
    NotificationSeverity,
)
from app.integrations.providers.generic_webhook import utc_now
from app.integrations.services.approval_bridge_service import ApprovalBridgeService
from app.integrations.services.business_sync_service import BusinessSyncService
from app.integrations.services.notification_service import NotificationService
from app.integrations.services.org_sync_service import OrgSyncService
from app.integrations.services.sla_escalation_service import SLAEscalationService, SLAStatus
from app.integrations.services.sso_service import SSOService
from app.models.base import ApprovalStatus


class IntegrationServiceTest(unittest.TestCase):
    """企业集成服务层测试。"""

    def test_notification_service_sends_local_message(self) -> None:
        config: dict = {}
        result = NotificationService().send_message(
            platform=IntegrationPlatform.LOCAL,
            title="审批提醒",
            content="有新的采购申请待审批。",
            config=config,
            enterprise_id=1,
            severity=NotificationSeverity.WARNING,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.metadata["outbox_size"], 1)

    def test_org_sync_service_returns_local_snapshot(self) -> None:
        result = OrgSyncService().sync(platform=IntegrationPlatform.LOCAL, config={}, enterprise_id=1)

        self.assertGreaterEqual(result.department_count, 1)
        self.assertGreaterEqual(result.user_count, 1)
        self.assertIn("departments", result.metadata)

    def test_sso_service_exchanges_local_code(self) -> None:
        profile = SSOService().exchange_code(
            platform=IntegrationPlatform.LOCAL,
            code="local-user-002",
            config={},
            enterprise_id=1,
        )
        claims = SSOService().build_session_claims(profile)

        self.assertEqual(profile.external_user_id, "local-user-002")
        self.assertEqual(profile.name, "李经理")
        self.assertEqual(claims["role"], "employee")

    def test_approval_bridge_creates_and_deduplicates_callback(self) -> None:
        config: dict = {}
        service = ApprovalBridgeService()
        created = service.create_external_approval(
            platform=IntegrationPlatform.LOCAL,
            approval_id=20,
            title="采购审批",
            summary="采购温度传感器。",
            business_type="purchase_request",
            config=config,
            enterprise_id=1,
        )
        event, first_check = service.parse_callback_once(
            platform=IntegrationPlatform.LOCAL,
            raw_payload={"approval_id": 20, "action": "approve"},
            config=config,
            enterprise_id=1,
            external_event_id="evt-20",
        )
        duplicated_event, duplicated_check = service.parse_callback_once(
            platform=IntegrationPlatform.LOCAL,
            raw_payload={"approval_id": 20, "action": "approve"},
            config=config,
            enterprise_id=1,
            external_event_id="evt-20",
        )

        self.assertTrue(created.success)
        self.assertIsNotNone(event)
        self.assertFalse(first_check.duplicated)
        self.assertIsNone(duplicated_event)
        self.assertTrue(duplicated_check.duplicated)
        self.assertEqual(service.map_callback_to_local_status(event), ApprovalStatus.APPROVED)

    def test_business_sync_service_pushes_local_object(self) -> None:
        config: dict = {}
        result = BusinessSyncService().push_object(
            platform=IntegrationPlatform.LOCAL,
            object_type=BusinessObjectType.PURCHASE_REQUEST,
            local_id=33,
            payload={"item_name": "温度传感器"},
            config=config,
            enterprise_id=1,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.external_id, "LOCAL-PURCHASE_REQUEST-33")
        self.assertEqual(result.raw_response["business_event_count"], 1)

    def test_sla_service_evaluates_and_notifies_breach(self) -> None:
        config: dict = {}
        created_at = utc_now() - timedelta(hours=8)
        service = SLAEscalationService()
        evaluation = service.evaluate(
            business_type="ticket",
            priority="high",
            created_at=created_at,
            now=utc_now(),
        )
        delivery = service.notify_if_needed(
            platform=IntegrationPlatform.LOCAL,
            business_type="ticket",
            business_id=101,
            title="A3 产线空压机 E07 报警",
            priority="high",
            created_at=created_at,
            config=config,
            enterprise_id=1,
            now=utc_now(),
        )

        self.assertIn(evaluation.status, {SLAStatus.BREACHED, SLAStatus.ESCALATED})
        self.assertIsNotNone(delivery)
        self.assertTrue(delivery.success)
        self.assertEqual(delivery.metadata["outbox_size"], 1)


if __name__ == "__main__":
    unittest.main()
