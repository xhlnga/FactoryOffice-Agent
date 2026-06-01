import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.api.v1.endpoints.integrations import run_org_sync
from app.integrations.core.schemas import IntegrationPlatform
from app.models.base import IntegrationConfigStatus
from app.models.department import Department
from app.models.enterprise import Enterprise
from app.models.external_id_mapping import ExternalIdMapping
from app.models.integration_config import IntegrationConfig
from app.models.user import User
from app.schemas.integration import IntegrationConfigCreateRequest


def test_webhook_platform_requires_webhook_url() -> None:
    """Webhook 类平台必须配置发送地址，避免创建不可用配置。"""
    with pytest.raises(ValidationError):
        IntegrationConfigCreateRequest(
            enterprise_id=1,
            platform=IntegrationPlatform.DINGTALK,
            name="dingtalk",
            enabled=True,
        )


def test_integration_config_keeps_secret_in_encrypted_config() -> None:
    """模型只保存密钥引用或加密配置，不要求把明文密钥散落到业务字段。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Enterprise.__table__, IntegrationConfig.__table__])
    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        config = IntegrationConfig(
            enterprise_id=1,
            platform=IntegrationPlatform.WECOM.value,
            name="wecom",
            status=IntegrationConfigStatus.ACTIVE,
            corp_id="corp-id",
            agent_id="agent-id",
            encrypted_config={"secret_ref": "vault://factory/wecom"},
            webhook_url="https://example.com/wecom",
        )
        session.add(config)
        session.commit()
        session.refresh(config)

        assert config.status == IntegrationConfigStatus.ACTIVE
        assert config.encrypted_config["secret_ref"].startswith("vault://")


def test_org_sync_endpoint_persists_snapshot() -> None:
    """接口层执行组织同步时必须传入 db，不能只返回预览快照。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Enterprise.__table__,
            IntegrationConfig.__table__,
            Department.__table__,
            User.__table__,
            ExternalIdMapping.__table__,
        ],
    )
    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        config = IntegrationConfig(
            enterprise_id=1,
            platform=IntegrationPlatform.LOCAL.value,
            name="local",
            status=IntegrationConfigStatus.ACTIVE,
            encrypted_config={},
        )
        session.add(config)
        session.commit()
        session.refresh(config)

        response = run_org_sync(config.id, db=session)

        assert response["result"]["metadata"]["persisted"] is True
        assert session.query(Department).count() >= 1
        assert session.query(User).count() >= 1
        assert session.query(ExternalIdMapping).count() >= 1
