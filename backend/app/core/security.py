from enum import StrEnum
from typing import Annotated

from fastapi import Header, HTTPException, status


class UserRole(StrEnum):
    """系统内置角色。"""

    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


ROLE_LABELS: dict[UserRole, str] = {
    UserRole.ADMIN: "系统管理员",
    UserRole.MANAGER: "部门负责人",
    UserRole.EMPLOYEE: "普通员工",
}


ROLE_LEVELS: dict[UserRole, int] = {
    UserRole.EMPLOYEE: 1,
    UserRole.MANAGER: 2,
    UserRole.ADMIN: 3,
}


def parse_role(role: str | None) -> UserRole:
    """把请求中的角色字符串转换为系统角色。"""
    if not role:
        return UserRole.EMPLOYEE

    try:
        return UserRole(role)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的用户角色：{role}",
        ) from exc


def has_role_level(current_role: UserRole, required_role: UserRole) -> bool:
    """判断当前角色是否满足最低权限要求。"""
    return ROLE_LEVELS[current_role] >= ROLE_LEVELS[required_role]


def get_request_role(
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
) -> UserRole:
    """从请求头读取模拟角色，未提供时默认为普通员工。"""
    return parse_role(x_user_role)


def require_role(required_role: UserRole):
    """生成 FastAPI 权限依赖函数。

    示例：Depends(require_role(UserRole.MANAGER))
    """

    def dependency(
        x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    ) -> UserRole:
        role = parse_role(x_user_role)
        if not has_role_level(role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"当前角色权限不足，需要至少为：{ROLE_LABELS[required_role]}",
            )
        return role

    return dependency
