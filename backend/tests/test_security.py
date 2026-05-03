import unittest

from fastapi import HTTPException

from app.core.security import UserRole, parse_role, require_role


class SecurityPolicyTest(unittest.TestCase):
    """权限边界测试。"""

    def test_missing_role_is_employee(self) -> None:
        self.assertEqual(parse_role(None), UserRole.EMPLOYEE)

    def test_manager_can_access_manager_endpoint(self) -> None:
        dependency = require_role(UserRole.MANAGER)
        self.assertEqual(dependency("manager"), UserRole.MANAGER)

    def test_employee_cannot_access_manager_endpoint(self) -> None:
        dependency = require_role(UserRole.MANAGER)

        with self.assertRaises(HTTPException) as context:
            dependency("employee")

        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
