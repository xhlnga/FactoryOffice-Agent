from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.approval_step import ApprovalStep
from app.models.approval_template import ApprovalTemplate
from app.models.base import ApprovalStepMode, ApproverType
from app.models.enterprise import Enterprise
from app.services.approval_engine import select_template_for_action


def test_purchase_amount_routes_to_high_amount_template() -> None:
    """采购金额应按阈值选择审批流。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Enterprise.__table__, ApprovalTemplate.__table__, ApprovalStep.__table__])
    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        session.add_all(
            [
                ApprovalTemplate(
                    enterprise_id=1,
                    name="低金额采购审批",
                    business_type="create_purchase_request",
                    max_amount=5000,
                    steps=[
                        ApprovalStep(
                            step_order=1,
                            name="主管审批",
                            approver_type=ApproverType.DEPARTMENT_MANAGER,
                            approver_value="department_manager",
                            mode=ApprovalStepMode.ANY,
                        )
                    ],
                ),
                ApprovalTemplate(
                    enterprise_id=1,
                    name="高金额采购审批",
                    business_type="create_purchase_request",
                    min_amount=5000,
                    steps=[
                        ApprovalStep(
                            step_order=1,
                            name="财务审批",
                            approver_type=ApproverType.ROLE,
                            approver_value="finance",
                            mode=ApprovalStepMode.ANY,
                        )
                    ],
                ),
            ]
        )
        session.commit()

        selected = select_template_for_action(
            session,
            business_type="create_purchase_request",
            payload={"budget": 48000},
            enterprise_id=1,
        )

        assert selected is not None
        assert selected.name == "高金额采购审批"


def test_missing_amount_routes_to_default_template_not_high_amount() -> None:
    """金额缺失时应选择默认模板，不能误走高金额审批流。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Enterprise.__table__, ApprovalTemplate.__table__, ApprovalStep.__table__])
    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        session.add_all(
            [
                ApprovalTemplate(
                    enterprise_id=1,
                    name="默认人工确认",
                    business_type="create_purchase_request",
                    is_default=True,
                    steps=[
                        ApprovalStep(
                            step_order=1,
                            name="主管审批",
                            approver_type=ApproverType.DEPARTMENT_MANAGER,
                            approver_value="department_manager",
                            mode=ApprovalStepMode.ANY,
                        )
                    ],
                ),
                ApprovalTemplate(
                    enterprise_id=1,
                    name="高金额采购审批",
                    business_type="create_purchase_request",
                    min_amount=50000,
                    steps=[
                        ApprovalStep(
                            step_order=1,
                            name="总经理审批",
                            approver_type=ApproverType.ROLE,
                            approver_value="general_manager",
                            mode=ApprovalStepMode.ANY,
                        )
                    ],
                ),
            ]
        )
        session.commit()

        selected = select_template_for_action(
            session,
            business_type="create_purchase_request",
            payload={"item_name": "温度传感器"},
            enterprise_id=1,
        )

        assert selected is not None
        assert selected.name == "默认人工确认"
