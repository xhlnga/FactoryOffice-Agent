import unittest
from unittest.mock import patch

from app.core.exceptions import AppException
from app.models.approval import Approval
from app.models.base import ApprovalStatus, PurchaseStatus
from app.schemas.approval import ApprovalDecisionRequest
from app.schemas.purchase_request import PurchaseCreateRequest
from app.services.approval_service import _execute_action
from app.services.approval_service import approve_approval
from app.services.purchase_service import create_purchase_request
from app.tools.base import classify_action_risk, requires_human_approval


class FakeDbSession:
    """审批服务单元测试使用的轻量数据库替身。"""

    def __init__(self, approval: Approval):
        self.approval = approval
        self.commit_count = 0
        self.refresh_count = 0

    def get(self, model, item_id: int):
        if model is Approval and item_id == self.approval.id:
            return self.approval
        return None

    def commit(self) -> None:
        self.commit_count += 1

    def refresh(self, _item) -> None:
        self.refresh_count += 1


class FakeWriteDbSession:
    """业务写入服务测试使用的轻量数据库替身。"""

    def __init__(self):
        self.record = None
        self.commit_count = 0
        self.refresh_count = 0

    def add(self, record) -> None:
        self.record = record

    def commit(self) -> None:
        self.commit_count += 1

    def refresh(self, _item) -> None:
        self.refresh_count += 1


class ApprovalFlowTest(unittest.TestCase):
    """审批流程测试。"""

    def test_purchase_request_is_high_or_medium_risk_but_always_needs_approval(self) -> None:
        low_budget_policy = classify_action_risk("create_purchase_request", {"budget": 20000})
        high_budget_policy = classify_action_risk("create_purchase_request", {"budget": 50000})

        self.assertEqual(low_budget_policy.risk_level, "medium")
        self.assertEqual(high_budget_policy.risk_level, "high")
        self.assertTrue(requires_human_approval("create_purchase_request", {"budget": 20000}))
        self.assertTrue(requires_human_approval("create_purchase_request", {"budget": 50000}))

    def test_business_write_is_blocked_without_approved_action(self) -> None:
        with self.assertRaises(AppException) as context:
            create_purchase_request(
                None,
                PurchaseCreateRequest(item_name="温度传感器", quantity=20),
            )

        self.assertEqual(context.exception.status_code, 403)

    def test_approved_purchase_request_enters_pending_approval_status(self) -> None:
        db = FakeWriteDbSession()

        record = create_purchase_request(
            db,
            PurchaseCreateRequest(
                item_name="温度传感器",
                quantity=20,
                reason="产线设备改造",
                budget=48000,
                supplier="华南传感器",
            ),
            approved_action=True,
        )

        self.assertIs(record, db.record)
        self.assertEqual(record.status, PurchaseStatus.PENDING_APPROVAL)
        self.assertEqual(db.commit_count, 1)

    def test_approve_marks_approved_only_after_action_success(self) -> None:
        approval = Approval(
            id=1,
            action_type="create_purchase_request",
            action_payload={"item_name": "温度传感器", "quantity": 20},
            status=ApprovalStatus.PENDING,
        )
        db = FakeDbSession(approval)

        with patch(
            "app.services.approval_service.execute_approved_action",
            return_value={"purchase_request_id": 100},
        ):
            result = approve_approval(
                db,
                1,
                ApprovalDecisionRequest(reviewer="王经理", comment="同意"),
            )

        self.assertEqual(result.status, ApprovalStatus.APPROVED)
        self.assertEqual(result.execution_result, {"purchase_request_id": 100})
        self.assertIsNotNone(result.reviewed_at)
        self.assertIsNotNone(result.executed_at)

    def test_approve_marks_execution_failed_when_action_fails(self) -> None:
        approval = Approval(
            id=1,
            action_type="create_purchase_request",
            action_payload={"item_name": "温度传感器"},
            status=ApprovalStatus.PENDING,
        )
        db = FakeDbSession(approval)

        with patch(
            "app.services.approval_service.execute_approved_action",
            side_effect=AppException("审批动作参数不完整。", status_code=400),
        ):
            with self.assertRaises(AppException):
                approve_approval(
                    db,
                    1,
                    ApprovalDecisionRequest(reviewer="王经理", comment="同意"),
                )

        self.assertEqual(approval.status, ApprovalStatus.EXECUTION_FAILED)

    def test_quality_issue_ticket_action_is_executable(self) -> None:
        with patch("app.services.approval_service.create_ticket") as create_ticket_mock:
            create_ticket_mock.return_value.id = 88

            result = _execute_action(
                None,
                "create_quality_issue_ticket",
                {
                    "ticket_type": "质量异常",
                    "title": "B2批次尺寸超差质量异常",
                    "description": "抽检发现尺寸超差。",
                    "priority": "high",
                },
            )

        self.assertEqual(result, {"ticket_id": 88})

    def test_quality_ticket_action_rejects_wrong_ticket_type(self) -> None:
        with self.assertRaises(AppException):
            _execute_action(
                None,
                "create_quality_issue_ticket",
                {
                    "ticket_type": "设备维修",
                    "title": "B2批次尺寸超差质量异常",
                    "description": "抽检发现尺寸超差。",
                    "priority": "high",
                },
            )

    def test_create_tasks_requires_non_empty_task_list(self) -> None:
        with self.assertRaises(AppException):
            _execute_action(None, "create_tasks", {"source": "meeting", "tasks": []})

    def test_create_tasks_keeps_payload_source(self) -> None:
        created_sources: list[str | None] = []

        def fake_create_task(_db, data, *, approved_action: bool, commit: bool):
            created_sources.append(data.source)
            task = type("TaskRecord", (), {})()
            task.id = 101
            return task

        with patch("app.services.approval_service.create_task", side_effect=fake_create_task):
            result = _execute_action(
                None,
                "create_tasks",
                {
                    "source": "manual",
                    "tasks": [
                        {
                            "title": "确认供应商交期",
                            "description": "联系供应商确认滤芯交付时间。",
                            "priority": "medium",
                        }
                    ],
                },
            )

        self.assertEqual(result, {"task_ids": [101]})
        self.assertEqual(created_sources, ["manual"])


if __name__ == "__main__":
    unittest.main()
