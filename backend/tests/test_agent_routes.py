import unittest
from unittest.mock import Mock, patch

from app.api.v1.endpoints.agent import chat_with_agent
from app.agents.factory_office_agent import run_factory_office_agent
from app.agents.graph_nodes import classify_intent
from app.schemas.agent import AgentChatRequest


class AgentRoutesTest(unittest.TestCase):
    """Agent 意图识别和路由测试。"""

    def test_policy_question_routes_to_knowledge_qa(self) -> None:
        state = run_factory_office_agent("采购超过5万需要谁审批？")

        self.assertEqual(state["intent"], "knowledge_qa")
        self.assertFalse(state["requires_approval"])

    def test_maintenance_incident_routes_to_ticket_preview(self) -> None:
        state = run_factory_office_agent("A3产线空压机E07报警，生产线暂停35分钟。")

        self.assertEqual(state["intent"], "maintenance_ticket")
        self.assertTrue(state["requires_approval"])
        self.assertEqual(state["tool_calls"][0]["tool_name"], "preview_maintenance_ticket")

    def test_maintenance_question_does_not_route_to_ticket_creation(self) -> None:
        state = run_factory_office_agent("空压机 E07 报警应该怎么处理？")

        self.assertEqual(state["intent"], "knowledge_qa")
        self.assertFalse(state["requires_approval"])

    def test_quality_issue_routes_to_quality_ticket_preview(self) -> None:
        state = run_factory_office_agent("B2批次零件抽检发现3件尺寸超差，请生成质量异常单。")

        self.assertEqual(state["intent"], "quality_issue")
        self.assertTrue(state["requires_approval"])
        self.assertEqual(state["tool_calls"][0]["tool_name"], "preview_quality_issue_ticket")

    def test_purchase_with_missing_fields_routes_to_clarification(self) -> None:
        state = run_factory_office_agent("帮我申请采购20个温度传感器，用于产线设备改造。")

        self.assertEqual(state["intent"], "purchase_request")
        self.assertEqual(state["sop_id"], "purchase_request")
        self.assertEqual(state["task_status"], "collecting_info")
        self.assertFalse(state["requires_approval"])
        self.assertIn("预算", state["tool_calls"][0]["reason"])
        self.assertTrue(any(field["label"] == "预算" for field in state["missing_fields"]))
        self.assertTrue(any(step["step"] == "slot_filling" for step in state["trace_steps"]))

    def test_purchase_context_can_continue_slot_filling(self) -> None:
        """补充信息可以沿用上一轮采购任务上下文。"""
        state = run_factory_office_agent(
            "预算48000元，供应商为华南传感器。",
            context={
                "task_status": "collecting_info",
                "active_intent": "purchase_request",
                "active_message": "帮我申请采购20个温度传感器，用于产线设备改造。",
            },
        )

        self.assertEqual(state["intent"], "purchase_request")
        self.assertEqual(state["task_status"], "waiting_approval")
        self.assertTrue(state["requires_approval"])
        self.assertEqual(state["missing_fields"], [])
        self.assertIn("补充信息", state["effective_message"])

    def test_purchase_action_with_need_keyword_is_not_misclassified_as_knowledge(self) -> None:
        """“需要采购”是业务动作，不是制度问答。"""
        state = run_factory_office_agent("产线改造需要采购20个温度传感器，预算48000元，供应商为华南传感器。")

        self.assertEqual(state["intent"], "purchase_request")
        self.assertTrue(state["requires_approval"])

    def test_weekly_report_routes_without_approval(self) -> None:
        state = run_factory_office_agent("本周完成空压机排查，下周推进滤芯更换，请生成项目周报。")

        self.assertEqual(state["intent"], "weekly_report")
        self.assertFalse(state["requires_approval"])
        self.assertEqual(state["tool_calls"][0]["tool_name"], "generate_weekly_report")

    def test_unknown_input_stays_unknown(self) -> None:
        intent = classify_intent("今天下午天气不错，大家辛苦了。")

        self.assertEqual(intent, "unknown")

    def test_agent_chat_writes_audit_log(self) -> None:
        """Agent 对话入口必须写审计日志，便于追溯意图、工具草稿和审批判断。"""
        state = {
            "intent": "purchase_request",
            "answer": "已识别为采购申请请求，系统会先生成采购申请草稿。该动作需要人工确认后才能执行。",
            "requires_approval": True,
            "tool_calls": [
                {
                    "tool_name": "preview_purchase_request",
                    "tool_args": {"purchase_description": "申请采购20个温度传感器"},
                    "requires_approval": True,
                }
            ],
            "audit_events": [{"action": "classify_intent", "status": "success", "detail": {}}],
        }

        with patch("app.api.v1.endpoints.agent.run_factory_office_agent", return_value=state):
            with patch("app.api.v1.endpoints.agent.create_audit_log") as create_audit_log_mock:
                response = chat_with_agent(
                    AgentChatRequest(message="申请采购20个温度传感器", user_id=2),
                    db=Mock(),
                )

        self.assertEqual(response.intent, "purchase_request")
        create_audit_log_mock.assert_called_once()
        audit_request = create_audit_log_mock.call_args.args[1]
        self.assertEqual(audit_request.action, "agent_chat")
        self.assertEqual(audit_request.user_id, 2)
        self.assertEqual(audit_request.tool_name, "preview_purchase_request")


if __name__ == "__main__":
    unittest.main()
