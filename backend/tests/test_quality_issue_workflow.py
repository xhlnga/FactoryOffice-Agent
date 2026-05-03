import unittest

from app.models.base import TaskPriority
from app.tools.ticket_tools import preview_quality_issue_ticket
from app.workflows.quality_issue import generate_quality_issue_ticket


class QualityIssueWorkflowTest(unittest.TestCase):
    """质量异常工作流测试。"""

    def test_dimension_deviation_generates_quality_ticket_draft(self) -> None:
        """尺寸超差应生成质量异常工单草稿，并要求人工确认。"""
        response = generate_quality_issue_ticket("B2批次零件抽检发现3件尺寸超差，影响当前批次出货。")

        self.assertEqual(response.workflow_status, "draft_ready")
        self.assertTrue(response.requires_approval)
        self.assertIsNotNone(response.quality_issue_draft)
        self.assertEqual(response.quality_issue_draft.ticket_type, "质量异常")
        self.assertEqual(response.quality_issue_draft.abnormality_type, "尺寸超差")
        self.assertIn("隔离", response.quality_issue_draft.initial_disposition)

    def test_customer_complaint_adds_8d_action(self) -> None:
        """客户投诉类异常应提示必要时启动 8D 分析。"""
        response = generate_quality_issue_ticket("客户反馈A12批次产品装配后泄漏，要求提交原因分析。")

        self.assertIsNotNone(response.quality_issue_draft)
        self.assertIn("8D", "；".join(response.quality_issue_draft.required_actions))

    def test_unclear_quality_input_requires_clarification(self) -> None:
        """没有明确质量异常信号时，不应强行生成正式草稿。"""
        response = generate_quality_issue_ticket("帮我整理一下昨天的项目沟通记录。")

        self.assertEqual(response.workflow_status, "needs_clarification")
        self.assertFalse(response.requires_approval)
        self.assertIsNone(response.quality_issue_draft)

    def test_quality_ticket_preview_requires_approval_only_when_draft_ready(self) -> None:
        """工具层应只返回待审批动作，不直接创建质量工单。"""
        result = preview_quality_issue_ticket("B2批次零件抽检发现3件尺寸超差，影响当前批次出货。")

        self.assertTrue(result.requires_approval)
        self.assertEqual(result.approval_payload["action_type"], "create_quality_issue_ticket")
        self.assertEqual(result.approval_payload["action_payload"]["ticket_type"], "质量异常")

    def test_quality_ticket_preview_does_not_create_empty_approval(self) -> None:
        """信息不足时，工具层也不能生成空审批动作。"""
        result = preview_quality_issue_ticket("帮我整理一下昨天的项目沟通记录。")

        self.assertFalse(result.requires_approval)
        self.assertEqual(result.approval_payload, {})

    def test_quality_priority_escalates_for_batch_or_customer_impact(self) -> None:
        """批量、客诉、退货等场景应提升优先级。"""
        response = generate_quality_issue_ticket("客户退货，批量产品存在尺寸超差和装配干涉。")

        self.assertIsNotNone(response.quality_issue_draft)
        self.assertEqual(response.quality_issue_draft.priority, TaskPriority.URGENT)


if __name__ == "__main__":
    unittest.main()
