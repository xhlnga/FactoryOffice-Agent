from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.base import TaskPriority
from app.models.department import Department
from app.models.enterprise import Enterprise
from app.models.purchase_request import PurchaseRequest
from app.models.sla import SLAInstance, SLAPolicyModel
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.purchase_request import PurchaseCreateRequest
from app.schemas.ticket import TicketCreateRequest
from app.services.purchase_service import create_purchase_request
from app.services.ticket_service import create_ticket


def test_ticket_creation_creates_sla_instance() -> None:
    """创建工单后应自动生成 SLA 实例。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Enterprise.__table__,
            Department.__table__,
            User.__table__,
            Ticket.__table__,
            SLAPolicyModel.__table__,
            SLAInstance.__table__,
        ],
    )
    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        session.add(User(id=1, username="zhang_gong", enterprise_id=1))
        session.commit()

        ticket = create_ticket(
            session,
            TicketCreateRequest(
                ticket_type="设备维修",
                title="A3 产线空压机 E07 报警",
                description="产线空压机报警，需要设备工程师确认。",
                priority=TaskPriority.HIGH,
                created_by=1,
            ),
            approved_action=True,
        )

        sla = session.scalar(select(SLAInstance).where(SLAInstance.business_id == str(ticket.id)))
        assert sla is not None
        assert sla.enterprise_id == 1
        assert sla.business_type == "ticket"
        assert sla.response_due_at is not None
        assert sla.deadline_at is not None


def test_purchase_creation_creates_sla_instance() -> None:
    """创建采购申请后应自动生成 SLA 实例。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Enterprise.__table__,
            Department.__table__,
            User.__table__,
            PurchaseRequest.__table__,
            SLAPolicyModel.__table__,
            SLAInstance.__table__,
        ],
    )
    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        session.add(User(id=1, username="wang_zhuguan", enterprise_id=1))
        session.commit()

        purchase = create_purchase_request(
            session,
            PurchaseCreateRequest(
                item_name="温度传感器",
                quantity=20,
                reason="产线急需备件，避免影响生产。",
                budget=48000,
                supplier="华南传感器",
                created_by=1,
            ),
            approved_action=True,
        )

        sla = session.scalar(select(SLAInstance).where(SLAInstance.business_id == str(purchase.id)))
        assert sla is not None
        assert sla.enterprise_id == 1
        assert sla.business_type == "purchase_request"
        assert sla.response_due_at is not None
        assert sla.deadline_at is not None
