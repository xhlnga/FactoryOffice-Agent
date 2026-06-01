from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.integrations.core.schemas import BusinessObjectType, IntegrationPlatform
from app.models.enterprise import Enterprise
from app.models.external_id_mapping import ExternalIdMapping


def test_external_id_mapping_allows_failed_record_without_external_id() -> None:
    """外部同步失败时通常拿不到 external_id，因此映射表必须能记录失败状态。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Enterprise.__table__, ExternalIdMapping.__table__])
    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        mapping = ExternalIdMapping(
            enterprise_id=1,
            object_type=BusinessObjectType.PURCHASE_REQUEST.value,
            local_id="20",
            external_system=IntegrationPlatform.GENERIC_ERP.value,
            external_id=None,
            sync_status="failed",
            last_error="ERP webhook_url 缺失",
            retry_count=1,
        )
        session.add(mapping)
        session.commit()
        session.refresh(mapping)

        assert mapping.id is not None
        assert mapping.external_id is None
        assert mapping.sync_status == "failed"

