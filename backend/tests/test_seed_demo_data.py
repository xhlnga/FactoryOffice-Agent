import unittest
from datetime import date, datetime

from app.services.approval_service import EXECUTABLE_ACTION_TYPES
from scripts import seed_demo_data


EXPECTED_SEED_FILES = {
    "users.json",
    "tasks.json",
    "tickets.json",
    "purchase_requests.json",
    "approvals.json",
    "audit_logs.json",
}


class SeedDemoDataTest(unittest.TestCase):
    """演示业务数据测试。"""

    def test_all_seed_files_exist_and_have_rows(self) -> None:
        """每个 seed 文件都应存在，并且至少有一条业务数据。"""
        for filename in EXPECTED_SEED_FILES:
            rows = seed_demo_data.load_json(filename)

            self.assertTrue(rows, f"{filename} 不应为空。")
            self.assertTrue(all("id" in row for row in rows), f"{filename} 每条数据都应包含 id。")

    def test_seed_ids_are_unique_inside_each_file(self) -> None:
        """同一个 seed 文件内 ID 不能重复，避免导入时互相覆盖。"""
        for filename in EXPECTED_SEED_FILES:
            rows = seed_demo_data.load_json(filename)
            ids = [row["id"] for row in rows]

            self.assertEqual(len(ids), len(set(ids)), f"{filename} 存在重复 id。")

    def test_seed_rows_can_be_converted_to_model_values(self) -> None:
        """验证 JSON 字段可以转换成模型需要的枚举和日期类型。"""
        converter_cases = [
            ("users.json", seed_demo_data.user_converter),
            ("tasks.json", seed_demo_data.task_converter),
            ("tickets.json", seed_demo_data.ticket_converter),
            ("purchase_requests.json", seed_demo_data.purchase_converter),
            ("approvals.json", seed_demo_data.approval_converter),
            ("audit_logs.json", seed_demo_data.audit_log_converter),
        ]

        for filename, converter in converter_cases:
            with self.subTest(filename=filename):
                rows = seed_demo_data.load_json(filename)
                converted_rows = [converter(row) for row in rows]

                self.assertEqual(len(converted_rows), len(rows))
                self.assertTrue(all(isinstance(row["created_at"], datetime) for row in converted_rows))

    def test_task_due_dates_are_real_dates_when_present(self) -> None:
        """任务 seed 中的截止日期必须是可解析日期，不能写成模糊文本。"""
        rows = seed_demo_data.load_json("tasks.json")

        for row in rows:
            converted = seed_demo_data.task_converter(row)
            if row.get("due_date") is not None:
                self.assertIsInstance(converted["due_date"], date)

    def test_approval_action_types_are_executable(self) -> None:
        """审批 seed 中的动作类型必须能被审批服务执行或拒绝，不能写孤立动作。"""
        approvals = seed_demo_data.load_json("approvals.json")

        for approval in approvals:
            self.assertIn(approval["action_type"], EXECUTABLE_ACTION_TYPES)

    def test_approved_approval_has_execution_trace(self) -> None:
        """已批准 seed 审批应有审批人、审批时间和执行结果，符合企业审计常识。"""
        approvals = seed_demo_data.load_json("approvals.json")

        for approval in approvals:
            if approval["status"] != "approved":
                continue

            self.assertTrue(approval.get("reviewer"))
            self.assertTrue(approval.get("reviewed_at"))
            self.assertTrue(approval.get("executed_at"))
            self.assertIsInstance(approval.get("execution_result"), dict)

    def test_reset_id_sequences_covers_seed_tables(self) -> None:
        """导入固定 ID 的 seed 后应校准自增序列，避免后续新增记录撞主键。"""

        class FakeDbSession:
            def __init__(self) -> None:
                self.calls = []

            def execute(self, statement, params) -> None:
                self.calls.append((str(statement), params))

        db = FakeDbSession()
        seed_demo_data.reset_id_sequences(db)
        table_names = [params["table_name"] for _statement, params in db.calls]

        self.assertEqual(
            table_names,
            ["users", "tasks", "tickets", "purchase_requests", "approvals", "audit_logs"],
        )
        self.assertTrue(all("setval" in statement for statement, _params in db.calls))


if __name__ == "__main__":
    unittest.main()
