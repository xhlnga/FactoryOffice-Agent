from enum import StrEnum

from app.core.security import ROLE_LEVELS, UserRole, parse_role


class DataScope(StrEnum):
    """数据范围，用于企业常见的行级权限控制。"""

    SELF = "self"
    DEPARTMENT = "department"
    DEPARTMENT_AND_CHILDREN = "department_and_children"
    FACTORY = "factory"
    ALL = "all"


class DocumentPrincipalType(StrEnum):
    """文档授权主体类型。"""

    ALL = "all"
    USER = "user"
    DEPARTMENT = "department"
    ROLE = "role"


class DocumentPermissionAction(StrEnum):
    """文档权限动作。"""

    VIEW = "view"
    MANAGE = "manage"


ROLE_DEFAULT_DATA_SCOPE: dict[str, DataScope] = {
    UserRole.ADMIN.value: DataScope.ALL,
    UserRole.MANAGER.value: DataScope.DEPARTMENT_AND_CHILDREN,
    UserRole.EMPLOYEE.value: DataScope.SELF,
    "quality_manager": DataScope.DEPARTMENT,
    "equipment_manager": DataScope.DEPARTMENT,
    "finance": DataScope.DEPARTMENT,
    "purchaser": DataScope.DEPARTMENT,
    "auditor": DataScope.ALL,
}


def role_level_at_least(current_role: UserRole | str, required_role: UserRole | str) -> bool:
    """比较内置角色等级，保留与旧 X-User-Role 权限模型兼容。"""
    current = parse_role(str(current_role))
    required = parse_role(str(required_role))
    return ROLE_LEVELS[current] >= ROLE_LEVELS[required]


def normalize_role_codes(role_codes: tuple[str, ...] | list[str] | set[str] | None) -> tuple[str, ...]:
    """清洗企业角色编码。"""
    if not role_codes:
        return ()
    return tuple(dict.fromkeys(str(code).strip() for code in role_codes if str(code).strip()))


def default_data_scope_for_roles(role_codes: tuple[str, ...]) -> DataScope:
    """根据角色推断默认数据范围，多个角色取最大范围。"""
    priority = {
        DataScope.SELF: 1,
        DataScope.DEPARTMENT: 2,
        DataScope.DEPARTMENT_AND_CHILDREN: 3,
        DataScope.FACTORY: 4,
        DataScope.ALL: 5,
    }
    scope = DataScope.SELF
    for role_code in role_codes:
        candidate = ROLE_DEFAULT_DATA_SCOPE.get(role_code, DataScope.SELF)
        if priority[candidate] > priority[scope]:
            scope = candidate
    return scope
