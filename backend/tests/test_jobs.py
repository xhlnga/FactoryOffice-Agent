from datetime import timedelta
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.integrations.core.schemas import BusinessObjectType, IntegrationPlatform, NotificationDeliveryResult
from app.jobs.business_sync_jobs import retry_business_sync_mapping
from app.jobs.notification_jobs import retry_notification_delivery
from app.jobs.org_sync_jobs import sync_organization_for_config
from app.jobs.sla_jobs import scan_active_sla_instances
from app.models.base import (
    IntegrationConfigStatus,
    IntegrationEventStatus,
    NotificationDeliveryStatus,
    SLAStatus,
    utc_now,
)
from app.models.department import Department
from app.models.enterprise import Enterprise
from app.models.external_id_mapping import ExternalIdMapping
from app.models.integration_config import IntegrationConfig
from app.models.integration_event import IntegrationEvent
from app.models.notification_delivery import NotificationDelivery
from app.models.sla import SLAInstance
from app.models.task import Task
from app.models.user import User


def _session_factory(*tables):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=list(tables))
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_retry_business_sync_mapping_updates_failed_mapping() -> None:
    """失败的外部业务同步记录应能被后台任务重试。"""
    SessionFactory = _session_factory(
        Enterprise.__table__,
        IntegrationConfig.__table__,
        ExternalIdMapping.__table__,
        Task.__table__,
    )
    with SessionFactory() as session:
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
        session.add(Task(id=10, title="同步 OA 任务"))
        session.add(
            ExternalIdMapping(
                id=100,
                enterprise_id=1,
                object_type=BusinessObjectType.TASK.value,
                local_id="10",
                external_system=IntegrationPlatform.LOCAL.value,
                sync_status=IntegrationEventStatus.FAILED.value,
                retry_count=0,
            )
        )
        session.commit()

    with patch("app.jobs.business_sync_jobs.SessionLocal", SessionFactory):
        result = retry_business_sync_mapping(100)

    with SessionFactory() as session:
        mapping = session.get(ExternalIdMapping, 100)
        assert result["status"] == "success"
        assert mapping is not None
        assert mapping.sync_status == "success"
        assert mapping.external_id == "LOCAL-TASK-10"


def test_retry_notification_delivery_updates_existing_record() -> None:
    """通知重试任务应更新原通知记录，不创建新的业务依赖。"""
    SessionFactory = _session_factory(
        Enterprise.__table__,
        IntegrationConfig.__table__,
        NotificationDelivery.__table__,
    )
    with SessionFactory() as session:
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
        session.add(
            NotificationDelivery(
                id=200,
                enterprise_id=1,
                platform=IntegrationPlatform.LOCAL.value,
                message_type="message",
                title="审批待办",
                business_type="approval",
                business_id="1",
                action_url="http://localhost:3000/mobile/approvals/1?token=signed",
                payload_snapshot={"content": "原审批待办内容", "action_url": "http://localhost:3000/mobile/approvals/1?token=signed"},
                status=NotificationDeliveryStatus.RETRYING,
                retryable=True,
                retry_count=0,
                last_error="上次发送失败",
            )
        )
        session.commit()

    with (
        patch("app.jobs.notification_jobs.SessionLocal", SessionFactory),
        patch("app.jobs.notification_jobs.NotificationService") as notification_service_cls,
    ):
        notification_service_cls.return_value.send_message.return_value = NotificationDeliveryResult(
            success=True,
            retryable=False,
            response_code=200,
        )
        result = retry_notification_delivery(200)
        sent_kwargs = notification_service_cls.return_value.send_message.call_args.kwargs

    with SessionFactory() as session:
        delivery = session.get(NotificationDelivery, 200)
        assert result["status"] == "success"
        assert delivery is not None
        assert delivery.status == NotificationDeliveryStatus.SUCCESS
        assert delivery.retry_count == 1
        assert delivery.delivered_at is not None
        assert sent_kwargs["content"] == "原审批待办内容"
        assert sent_kwargs["action_url"] == "http://localhost:3000/mobile/approvals/1?token=signed"


def test_org_sync_job_records_integration_event() -> None:
    """组织同步任务应记录集成事件，方便后续排查。"""
    SessionFactory = _session_factory(
        Enterprise.__table__,
        IntegrationConfig.__table__,
        IntegrationEvent.__table__,
    )
    with SessionFactory() as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        session.add(
            IntegrationConfig(
                id=300,
                enterprise_id=1,
                platform=IntegrationPlatform.LOCAL.value,
                name="local",
                status=IntegrationConfigStatus.ACTIVE,
                encrypted_config={},
            )
        )
        session.commit()

    with patch("app.jobs.org_sync_jobs.SessionLocal", SessionFactory):
        result = sync_organization_for_config(300)

    with SessionFactory() as session:
        event = session.scalar(select(IntegrationEvent).where(IntegrationEvent.event_type == "org_sync"))
        assert result["status"] == "success"
        assert event is not None
        assert event.status == IntegrationEventStatus.SUCCESS
        assert event.payload["user_count"] >= 1


def test_sla_scan_marks_response_and_breach() -> None:
    """SLA 扫描应能标记提醒和超时。"""
    SessionFactory = _session_factory(SLAInstance.__table__)
    now = utc_now()
    with SessionFactory() as session:
        session.add(
            SLAInstance(
                id=1,
                business_type="ticket",
                business_id="T-1",
                status=SLAStatus.ACTIVE,
                response_due_at=now - timedelta(minutes=5),
                deadline_at=now + timedelta(minutes=30),
            )
        )
        session.add(
            SLAInstance(
                id=2,
                business_type="ticket",
                business_id="T-2",
                status=SLAStatus.ACTIVE,
                response_due_at=now - timedelta(minutes=60),
                deadline_at=now - timedelta(minutes=1),
            )
        )
        session.commit()

    with patch("app.jobs.sla_jobs.SessionLocal", SessionFactory):
        result = scan_active_sla_instances()

    with SessionFactory() as session:
        reminding = session.get(SLAInstance, 1)
        breached = session.get(SLAInstance, 2)
        assert result["changed"] == 2
        assert reminding is not None
        assert reminding.first_remind_at is not None
        assert breached is not None
        assert breached.status == SLAStatus.BREACHED
        assert breached.breached_at is not None


def test_sla_scan_writes_notification_delivery_when_configured() -> None:
    """SLA 超时后应通过通知服务写入通知投递记录。"""
    SessionFactory = _session_factory(
        Enterprise.__table__,
        Department.__table__,
        User.__table__,
        IntegrationConfig.__table__,
        NotificationDelivery.__table__,
        SLAInstance.__table__,
    )
    now = utc_now()
    with SessionFactory() as session:
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
        session.add(
            SLAInstance(
                id=3,
                enterprise_id=1,
                business_type="ticket",
                business_id="T-3",
                status=SLAStatus.ACTIVE,
                response_due_at=now - timedelta(minutes=60),
                deadline_at=now - timedelta(minutes=1),
            )
        )
        session.commit()

    with patch("app.jobs.sla_jobs.SessionLocal", SessionFactory):
        result = scan_active_sla_instances()

    with SessionFactory() as session:
        delivery = session.scalar(select(NotificationDelivery).where(NotificationDelivery.business_type == "sla"))
        breached = session.get(SLAInstance, 3)
        assert result["notified"] == 1
        assert delivery is not None
        assert delivery.status == NotificationDeliveryStatus.SUCCESS
        assert breached is not None
        assert breached.status == SLAStatus.BREACHED
