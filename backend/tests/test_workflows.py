import unittest

from app.agents.factory_office_agent import run_factory_office_agent
from app.api.v1.endpoints.tickets import create_ticket as create_ticket_endpoint
from app.core.exceptions import AppException
from app.evaluators.workflow_eval import run_default_workflow_eval
from app.schemas.ticket import TicketCreateRequest
from app.tools.task_tools import preview_tasks_from_meeting
from app.tools.ticket_tools import preview_maintenance_ticket
from app.workflows.maintenance_ticket import generate_maintenance_ticket
from app.workflows.meeting_to_tasks import generate_task_drafts
from app.workflows.purchase_request import generate_purchase_request
from app.workflows.quality_issue import generate_quality_issue_ticket


class WorkflowTest(unittest.TestCase):
    """固定办公流程与 Agent 路由测试。"""

    def test_purchase_policy_question_routes_to_knowledge(self) -> None:
        state = run_factory_office_agent("采购超过5万需要谁审批？")

        self.assertEqual(state["intent"], "knowledge_qa")
        self.assertFalse(state["requires_approval"])

    def test_maintenance_question_does_not_create_ticket(self) -> None:
        state = run_factory_office_agent("空压机E07报警怎么处理？")

        self.assertEqual(state["intent"], "knowledge_qa")
        self.assertFalse(state["requires_approval"])

    def test_maintenance_incident_requires_ticket_approval(self) -> None:
        state = run_factory_office_agent("空压机E07报警，生产线A暂停。")

        self.assertEqual(state["intent"], "maintenance_ticket")
        self.assertTrue(state["requires_approval"])
        self.assertEqual(state["tool_calls"][0]["tool_name"], "preview_maintenance_ticket")

    def test_quality_issue_requires_quality_ticket_approval(self) -> None:
        state = run_factory_office_agent("B2批次零件抽检发现3件尺寸超差，请生成质量异常单。")

        self.assertEqual(state["intent"], "quality_issue")
        self.assertTrue(state["requires_approval"])
        self.assertEqual(state["tool_calls"][0]["tool_name"], "preview_quality_issue_ticket")

    def test_quality_issue_draft_keeps_human_confirmation(self) -> None:
        response = generate_quality_issue_ticket("B2批次零件抽检发现3件尺寸超差，影响当前批次出货。")

        self.assertEqual(response.workflow_status, "draft_ready")
        self.assertTrue(response.requires_approval)
        self.assertIsNotNone(response.quality_issue_draft)
        self.assertIn("尺寸超差", response.quality_issue_draft.abnormality_type)
        self.assertIn("隔离", response.quality_issue_draft.initial_disposition)

    def test_purchase_missing_fields_requires_clarification(self) -> None:
        response = generate_purchase_request("帮我申请采购20个温度传感器，用于产线改造。")

        self.assertEqual(response.workflow_status, "needs_clarification")
        self.assertFalse(response.requires_approval)
        self.assertIn("预算", response.missing_fields)
        self.assertIn("供应商", response.missing_fields)

    def test_purchase_policy_question_is_not_treated_as_purchase_draft(self) -> None:
        response = generate_purchase_request("采购超过5万怎么审批？")

        self.assertEqual(response.workflow_status, "needs_clarification")
        self.assertFalse(response.requires_approval)
        self.assertIn("制度", response.message)
        self.assertIsNone(response.purchase_draft.item_name)

    def test_purchase_budget_number_is_not_treated_as_quantity(self) -> None:
        response = generate_purchase_request(
            "申请采购温度传感器，预算2万元，用于产线设备改造，供应商为华南传感器。"
        )

        self.assertEqual(response.workflow_status, "needs_clarification")
        self.assertIn("数量", response.missing_fields)

    def test_maintenance_workflow_requires_clear_equipment_issue(self) -> None:
        response = generate_maintenance_ticket("申请购买过滤器滤芯 10 套，用于 A3 空压机保养。")

        self.assertEqual(response.workflow_status, "needs_clarification")
        self.assertFalse(response.requires_approval)
        self.assertIsNone(response.ticket_draft)

    def test_maintenance_preview_does_not_create_empty_approval(self) -> None:
        result = preview_maintenance_ticket("申请购买过滤器滤芯 10 套，用于 A3 空压机保养。")

        self.assertFalse(result.requires_approval)
        self.assertEqual(result.approval_payload, {})

    def test_meeting_task_extraction_avoids_common_chinese_name_error(self) -> None:
        response = generate_task_drafts(
            "今天会议确定：张工周五前完成设备巡检方案；李工下周一联系供应商确认交期。"
        )

        self.assertTrue(response.requires_approval)
        assignees = [task.assignee for task in response.tasks]
        self.assertIn("张工", assignees)
        self.assertIn("李工", assignees)
        self.assertNotIn("李工下", assignees)

    def test_meeting_task_tool_uses_controlled_source_label(self) -> None:
        result = preview_tasks_from_meeting(
            "今天会议确定：张工周五前完成设备巡检方案；李工下周一联系供应商确认交期。"
        )

        self.assertTrue(result.requires_approval)
        self.assertEqual(result.approval_payload["action_payload"]["source"], "meeting")
        self.assertIn("source_text", result.approval_payload["action_payload"])

    def test_default_workflow_eval_passes(self) -> None:
        results = run_default_workflow_eval()

        self.assertTrue(results)
        self.assertTrue(all(result.passed for result in results))

    def test_unsupported_ticket_type_is_not_silently_treated_as_maintenance(self) -> None:
        with self.assertRaises(AppException):
            create_ticket_endpoint(
                TicketCreateRequest(
                    ticket_type="IT支持",
                    title="办公电脑无法开机",
                    description="需要 IT 人员处理。",
                ),
                db=None,
            )


if __name__ == "__main__":
    unittest.main()
