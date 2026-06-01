from app.integrations.core.schemas import IntegrationPlatform
from app.integrations.services.org_sync_service import OrgSyncService
from app.models.base import DepartmentStatus, UserStatus
from app.models.department import Department
from app.models.enterprise import Enterprise
from app.models.external_id_mapping import ExternalIdMapping
from app.models.user import User
from app.core.database import Base
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


def test_org_sync_service_returns_normalized_local_snapshot() -> None:
    """组织同步服务应返回规范化部门和人员快照。"""
    result = OrgSyncService().sync(platform=IntegrationPlatform.LOCAL, config={}, enterprise_id=1)

    assert result.department_count >= 1
    assert result.user_count >= 1
    assert result.metadata["platform"] == "local"
    assert result.metadata["departments"][0]["external_department_id"]


def test_org_sync_service_upserts_departments_users_and_external_mappings() -> None:
    """组织同步传入数据库后，应真正落库部门、用户和外部 ID 映射。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Enterprise.__table__,
            Department.__table__,
            User.__table__,
            ExternalIdMapping.__table__,
        ],
    )

    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        session.commit()

        result = OrgSyncService().sync(
            platform=IntegrationPlatform.LOCAL,
            config={},
            enterprise_id=1,
            db=session,
        )

        departments = session.scalars(select(Department).order_by(Department.external_department_id)).all()
        users = session.scalars(select(User).order_by(User.external_user_id)).all()
        mappings = session.scalars(select(ExternalIdMapping)).all()

        assert result.metadata["persisted"] is True
        assert len(departments) >= 4
        assert len(users) >= 3
        assert departments[0].status == DepartmentStatus.ACTIVE
        assert users[0].status == UserStatus.ACTIVE
        assert any(item.object_type == "department" for item in mappings)
        assert any(item.object_type == "user" for item in mappings)
