from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.integrations.core.schemas import BusinessObjectType, IntegrationPlatform
from app.models.base import IntegrationConfigStatus
from app.models.enterprise import Enterprise
from app.models.external_id_mapping import ExternalIdMapping
from app.models.integration_config import IntegrationConfig
from app.services.business_sync_service import BusinessSyncRequest, sync_business_object


def test_business_sync_service_records_successful_external_mapping() -> None:
    """外部业务同步成功后应写 external_id_mappings。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Enterprise.__table__, IntegrationConfig.__table__, ExternalIdMapping.__table__])
    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        session.add(
            IntegrationConfig(
                enterprise_id=1,
                platform=IntegrationPlatform.LOCAL.value,
                name="local",
                status=IntegrationConfigStatus.ACTIVE,
                encrypted_config={},
            )
        )
        session.commit()

        record = sync_business_object(
            session,
            BusinessSyncRequest(
                enterprise_id=1,
                object_type=BusinessObjectType.TASK,
                local_id=99,
                target_system=IntegrationPlatform.GENERIC_OA,
                payload={"title": "同步 OA 任务"},
            ),
        )

        mapping = session.scalar(select(ExternalIdMapping).where(ExternalIdMapping.local_id == "99"))
        assert record is not None
        assert record.sync_status == "success"
        assert mapping is not None
        assert mapping.external_id == "LOCAL-TASK-99"

