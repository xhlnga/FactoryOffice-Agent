from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.integrations.core.base import NotificationProvider
from app.integrations.core.registry import IntegrationProviderRegistry
from app.integrations.core.schemas import IntegrationPlatform, NotificationSeverity
from app.integrations.services.notification_service import NotificationService
from app.models.base import NotificationDeliveryStatus
from app.models.enterprise import Enterprise
from app.models.notification_delivery import NotificationDelivery


class BrokenNotificationProvider(NotificationProvider):
    """测试用 Provider：模拟外部平台临时不可用。"""

    platform = IntegrationPlatform.LOCAL

    def send_message(self, message):  # noqa: ANN001
        raise RuntimeError("外部通知平台连接失败")


def test_notification_service_records_delivery_result() -> None:
    """发送通知时应落库投递记录，便于失败重试和审计排查。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Enterprise.__table__, NotificationDelivery.__table__])
    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        session.commit()

        result = NotificationService().send_message(
            db=session,
            platform=IntegrationPlatform.LOCAL,
            title="采购审批提醒",
            content="有一条采购申请待审批。",
            config={},
            enterprise_id=1,
            severity=NotificationSeverity.WARNING,
            business_type="approval",
            business_id=10,
            action_url="http://localhost:3000/mobile/approvals/10?token=signed",
        )

        delivery = session.scalar(select(NotificationDelivery))
        assert result.success is True
        assert delivery is not None
        assert delivery.status == NotificationDeliveryStatus.SUCCESS
        assert delivery.business_type == "approval"
        assert delivery.action_url is not None
        assert delivery.payload_snapshot["content"] == "有一条采购申请待审批。"


def test_notification_service_records_provider_exception() -> None:
    """Provider 抛异常时不能让通知记录停在 pending，必须留下失败原因。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Enterprise.__table__, NotificationDelivery.__table__])
    registry = IntegrationProviderRegistry()
    registry.register(IntegrationPlatform.LOCAL, lambda context: BrokenNotificationProvider(context))

    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        session.commit()

        result = NotificationService(registry=registry).send_message(
            db=session,
            platform=IntegrationPlatform.LOCAL,
            title="维修工单超时提醒",
            content="A3 产线空压机工单已超时。",
            enterprise_id=1,
            business_type="ticket",
            business_id=20,
        )

        delivery = session.scalar(select(NotificationDelivery))
        assert result.success is False
        assert result.retryable is True
        assert delivery is not None
        assert delivery.status == NotificationDeliveryStatus.RETRYING
        assert "外部通知平台连接失败" in (delivery.last_error or "")
