import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.integrations.core.schemas import BusinessObjectType, IntegrationPlatform
from app.models.base import IntegrationConfigStatus
from app.models.enterprise import Enterprise
from app.models.external_id_mapping import ExternalIdMapping
from app.models.integration_config import IntegrationConfig
from app.services.business_sync_service import BusinessSyncRequest, sync_business_object


class BusinessSyncRecordTest(unittest.TestCase):
    """外部业务系统同步记录测试。"""

    def setUp(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(
            engine,
            tables=[
                Enterprise.__table__,
                IntegrationConfig.__table__,
                ExternalIdMapping.__table__,
            ],
        )
        self.session = Session(engine)
        self.session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()

    def test_successful_local_sync_writes_external_mapping(self) -> None:
        """同步成功时，应记录外部系统、外部 ID、状态和同步时间。"""
        self.session.add(
            IntegrationConfig(
                enterprise_id=1,
                platform=IntegrationPlatform.LOCAL.value,
                name="local-demo",
                status=IntegrationConfigStatus.ACTIVE,
                encrypted_config={},
            )
        )
        self.session.commit()

        record = sync_business_object(
            self.session,
            BusinessSyncRequest(
                enterprise_id=1,
                object_type=BusinessObjectType.TASK,
                local_id=10,
                target_system=IntegrationPlatform.GENERIC_OA,
                payload={"title": "同步 OA 任务"},
            ),
        )

        self.assertIsNotNone(record)
        self.assertEqual(record.external_system, "local")
        self.assertEqual(record.external_id, "LOCAL-TASK-10")
        self.assertEqual(record.sync_status, "success")
        self.assertIsNone(record.last_error)
        self.assertEqual(record.retry_count, 0)
        self.assertIsNotNone(record.last_sync_at)

    def test_failed_sync_is_recorded_without_external_id(self) -> None:
        """外部系统失败时，也要记录失败原因和重试次数。"""
        self.session.add(
            IntegrationConfig(
                enterprise_id=1,
                platform=IntegrationPlatform.GENERIC_ERP.value,
                name="erp-without-webhook",
                status=IntegrationConfigStatus.ACTIVE,
                encrypted_config={},
            )
        )
        self.session.commit()

        record = sync_business_object(
            self.session,
            BusinessSyncRequest(
                enterprise_id=1,
                object_type=BusinessObjectType.PURCHASE_REQUEST,
                local_id=20,
                target_system=IntegrationPlatform.GENERIC_ERP,
                payload={"item_name": "温度传感器"},
            ),
        )

        self.assertIsNotNone(record)
        self.assertEqual(record.external_system, "generic_erp")
        self.assertIsNone(record.external_id)
        self.assertEqual(record.sync_status, "failed")
        self.assertIn("webhook_url", record.last_error)
        self.assertEqual(record.retry_count, 1)

        mapping_count = self.session.scalar(select(ExternalIdMapping).where(ExternalIdMapping.local_id == "20"))
        self.assertIsNotNone(mapping_count)

    def test_real_external_config_requires_enterprise_context(self) -> None:
        """没有企业上下文时，不能误用真实外部系统配置。"""
        self.session.add(
            IntegrationConfig(
                enterprise_id=1,
                platform=IntegrationPlatform.GENERIC_ERP.value,
                name="erp-config",
                status=IntegrationConfigStatus.ACTIVE,
                encrypted_config={"webhook_url": "https://erp.example.test/hook"},
            )
        )
        self.session.commit()

        record = sync_business_object(
            self.session,
            BusinessSyncRequest(
                object_type=BusinessObjectType.PURCHASE_REQUEST,
                local_id=30,
                target_system=IntegrationPlatform.GENERIC_ERP,
                payload={"item_name": "温度传感器"},
            ),
        )

        self.assertIsNone(record)
        mapping = self.session.scalar(select(ExternalIdMapping).where(ExternalIdMapping.local_id == "30"))
        self.assertIsNone(mapping)


if __name__ == "__main__":
    unittest.main()
