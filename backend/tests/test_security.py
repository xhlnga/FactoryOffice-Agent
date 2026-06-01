import unittest
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException

from app.api.v1.endpoints.mobile_approvals import _verify_mobile_approval_access
from app.core.auth import AuthenticatedUser, create_session_token, get_current_user_optional
from app.core.security import UserRole, parse_role, require_role
from app.models.approval import Approval
from app.services.approval_service import _build_mobile_approval_url


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

    def test_bearer_token_can_satisfy_required_role(self) -> None:
        """登录 token 应该能访问受保护接口，不能只依赖演示请求头。"""
        dependency = require_role(UserRole.MANAGER)
        token = create_session_token({"username": "manager_demo", "role": "manager"})

        self.assertEqual(dependency(None, f"Bearer {token}"), UserRole.MANAGER)

    def test_auth_me_reads_bearer_token(self) -> None:
        token = create_session_token(
            {
                "user_id": 2,
                "username": "manager_demo",
                "role": "manager",
                "department": "设备部",
            }
        )

        current_user = get_current_user_optional(authorization=f"Bearer {token}")

        self.assertEqual(current_user.username, "manager_demo")
        self.assertEqual(current_user.role, UserRole.MANAGER)
        self.assertEqual(current_user.department, "设备部")
        self.assertEqual(current_user.auth_source, "token")

    def test_mobile_approval_link_contains_signed_token(self) -> None:
        """移动审批链接不能只暴露审批 ID，必须带签名 token。"""
        approval = Approval(id=15, action_type="create_task", action_payload={})

        url = _build_mobile_approval_url(approval)
        token = parse_qs(urlparse(url).query)["token"][0]

        _verify_mobile_approval_access(15, token=token, current_user=AuthenticatedUser())
        with self.assertRaises(HTTPException):
            _verify_mobile_approval_access(16, token=token, current_user=AuthenticatedUser())

    def test_mobile_approval_requires_token_for_anonymous_user(self) -> None:
        with self.assertRaises(HTTPException) as context:
            _verify_mobile_approval_access(15, token=None, current_user=AuthenticatedUser())

        self.assertEqual(context.exception.status_code, 401)

    def test_manager_can_open_mobile_approval_without_link_token(self) -> None:
        current_user = AuthenticatedUser(role=UserRole.MANAGER, auth_source="local-header")

        _verify_mobile_approval_access(15, token=None, current_user=current_user)


if __name__ == "__main__":
    unittest.main()
