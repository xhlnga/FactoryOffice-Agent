import unittest

from sqlalchemy.orm import configure_mappers

import app.models  # noqa: F401
from app.core.database import Base


class EnterpriseModelTest(unittest.TestCase):
    """企业集成相关模型测试。"""

    def test_enterprise_integration_tables_are_registered(self) -> None:
        """新增模型应被 Base.metadata 发现，避免迁移和初始化漏表。"""
        expected_tables = {
            "approval_actions",
            "approval_instance_steps",
            "approval_instances",
            "approval_steps",
            "approval_templates",
            "enterprises",
            "integration_configs",
            "departments",
            "roles",
            "user_roles",
            "external_id_mappings",
            "integration_events",
            "notification_deliveries",
            "idempotency_keys",
            "sla_policies",
            "sla_instances",
        }

        self.assertTrue(expected_tables.issubset(Base.metadata.tables.keys()))

    def test_user_keeps_legacy_fields_and_adds_enterprise_fields(self) -> None:
        """users 兼容旧 role/department，同时具备企业集成字段。"""
        user_columns = Base.metadata.tables["users"].columns

        for column_name in ["role", "department"]:
            self.assertIn(column_name, user_columns)

        for column_name in [
            "enterprise_id",
            "external_user_id",
            "department_id",
            "position",
            "mobile_hash",
            "email",
            "status",
            "is_admin",
        ]:
            self.assertIn(column_name, user_columns)

    def test_relationships_can_be_configured(self) -> None:
        """关系映射必须能配置成功，避免运行时首次查询才暴露关系错误。"""
        configure_mappers()


if __name__ == "__main__":
    unittest.main()
