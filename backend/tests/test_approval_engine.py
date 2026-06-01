import unittest
from datetime import timedelta
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.approval import Approval
from app.models.approval_action import ApprovalAction
from app.models.approval_instance import ApprovalInstance
from app.models.approval_instance_step import ApprovalInstanceStep
from app.models.approval_step import ApprovalStep
from app.models.approval_template import ApprovalTemplate
from app.models.base import (
    ApprovalInstanceStatus,
    ApprovalStepMode,
    ApprovalStatus,
    ApproverType,
    utc_now,
)
from app.models.enterprise import Enterprise
from app.models.user import User
from app.schemas.approval import ApprovalCreateRequest, ApprovalDecisionRequest
from app.services.approval_engine import escalate_overdue_steps, select_template_for_action
from app.services.approval_service import approve_approval, create_approval


class ApprovalEngineTest(unittest.TestCase):
    """审批引擎测试。"""

    def setUp(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(
            engine,
            tables=[
                Enterprise.__table__,
                User.__table__,
                Approval.__table__,
                ApprovalTemplate.__table__,
                ApprovalStep.__table__,
                ApprovalInstance.__table__,
                ApprovalInstanceStep.__table__,
                ApprovalAction.__table__,
            ],
        )
        self.session = Session(engine)
        self.session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()

    def test_amount_threshold_selects_matching_template(self) -> None:
        """采购金额应匹配对应审批模板。"""
        low_template = ApprovalTemplate(
            enterprise_id=1,
            name="低金额采购",
            business_type="create_purchase_request",
            max_amount=5000,
        )
        high_template = ApprovalTemplate(
            enterprise_id=1,
            name="高金额采购",
            business_type="create_purchase_request",
            min_amount=5000,
        )
        self.session.add_all([low_template, high_template])
        self.session.commit()

        selected = select_template_for_action(
            self.session,
            business_type="create_purchase_request",
            payload={"budget": 48000},
            enterprise_id=1,
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected.name, "高金额采购")

    def test_approval_service_uses_engine_before_business_execution(self) -> None:
        """多级审批未完成前，不应执行业务动作。"""
        self._create_purchase_template()
        approval = create_approval(
            self.session,
            ApprovalCreateRequest(
                action_type="create_purchase_request",
                action_payload={
                    "item_name": "温度传感器",
                    "quantity": 20,
                    "reason": "产线改造",
                    "budget": 48000,
                    "supplier": "华南传感器",
                },
            ),
        )
        instance = self.session.scalars(
            select(ApprovalInstance).where(ApprovalInstance.approval_id == approval.id)
        ).one()
        self.assertEqual(len(instance.steps), 2)

        with patch("app.services.approval_service.execute_approved_action") as execute_mock:
            first_result = approve_approval(
                self.session,
                approval.id,
                ApprovalDecisionRequest(reviewer="部门主管", comment="同意"),
            )

        execute_mock.assert_not_called()
        self.assertEqual(first_result.status, ApprovalStatus.PENDING)
        self.assertEqual(instance.status, ApprovalInstanceStatus.PENDING)
        self.assertEqual(instance.current_step_order, 2)

        with patch(
            "app.services.approval_service.execute_approved_action",
            return_value={"purchase_request_id": 100},
        ) as execute_mock:
            second_result = approve_approval(
                self.session,
                approval.id,
                ApprovalDecisionRequest(reviewer="财务经理", comment="同意"),
            )

        execute_mock.assert_called_once()
        self.assertEqual(second_result.status, ApprovalStatus.APPROVED)
        self.assertEqual(second_result.execution_result, {"purchase_request_id": 100})

    def test_overdue_step_can_be_escalated(self) -> None:
        """超时步骤应按模板配置升级到指定角色。"""
        self._create_purchase_template()
        approval = create_approval(
            self.session,
            ApprovalCreateRequest(
                action_type="create_purchase_request",
                action_payload={
                    "item_name": "温度传感器",
                    "quantity": 20,
                    "reason": "产线改造",
                    "budget": 48000,
                    "supplier": "华南传感器",
                },
            ),
        )
        instance = self.session.scalars(
            select(ApprovalInstance).where(ApprovalInstance.approval_id == approval.id)
        ).one()
        first_step = instance.steps[0]
        first_step.timeout_hours = 1
        first_step.escalate_to = "admin"
        first_step.created_at = utc_now() - timedelta(hours=2)
        self.session.commit()

        escalated = escalate_overdue_steps(self.session)

        self.assertEqual([step.id for step in escalated], [first_step.id])
        self.assertEqual(first_step.assigned_to, "admin")

    def test_all_mode_waits_for_same_step_approvers(self) -> None:
        """会签模式下，同一步多个审批人都通过后才进入执行。"""
        template = ApprovalTemplate(
            enterprise_id=1,
            name="采购申请会签",
            business_type="create_purchase_request",
            min_amount=5000,
            max_amount=50000,
        )
        template.steps = [
            ApprovalStep(
                step_order=1,
                name="财务与部门会签",
                approver_type=ApproverType.ROLE,
                approver_value="finance,department_manager",
                mode=ApprovalStepMode.ALL,
            )
        ]
        self.session.add(template)
        self.session.commit()
        approval = create_approval(
            self.session,
            ApprovalCreateRequest(
                action_type="create_purchase_request",
                action_payload={
                    "item_name": "温度传感器",
                    "quantity": 20,
                    "reason": "产线改造",
                    "budget": 48000,
                    "supplier": "华南传感器",
                },
            ),
        )
        instance = self.session.scalars(
            select(ApprovalInstance).where(ApprovalInstance.approval_id == approval.id)
        ).one()
        self.assertEqual(len(instance.steps), 2)

        with patch("app.services.approval_service.execute_approved_action") as execute_mock:
            first_result = approve_approval(
                self.session,
                approval.id,
                ApprovalDecisionRequest(reviewer="财务经理", comment="同意"),
            )

        execute_mock.assert_not_called()
        self.assertEqual(first_result.status, ApprovalStatus.PENDING)

        with patch(
            "app.services.approval_service.execute_approved_action",
            return_value={"purchase_request_id": 200},
        ) as execute_mock:
            second_result = approve_approval(
                self.session,
                approval.id,
                ApprovalDecisionRequest(reviewer="部门主管", comment="同意"),
            )

        execute_mock.assert_called_once()
        self.assertEqual(second_result.status, ApprovalStatus.APPROVED)

    def _create_purchase_template(self) -> ApprovalTemplate:
        template = ApprovalTemplate(
            enterprise_id=1,
            name="采购申请两级审批",
            business_type="create_purchase_request",
            min_amount=5000,
            max_amount=50000,
        )
        template.steps = [
            ApprovalStep(
                step_order=1,
                name="部门主管审批",
                approver_type=ApproverType.DEPARTMENT_MANAGER,
                approver_value="department_manager",
                mode=ApprovalStepMode.ANY,
                timeout_hours=24,
                escalate_to="manager",
            ),
            ApprovalStep(
                step_order=2,
                name="财务审核",
                approver_type=ApproverType.ROLE,
                approver_value="finance",
                mode=ApprovalStepMode.ANY,
                timeout_hours=24,
                escalate_to="admin",
            ),
        ]
        self.session.add(template)
        self.session.commit()
        return template


if __name__ == "__main__":
    unittest.main()
