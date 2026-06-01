from dataclasses import dataclass, field
from typing import Any

from fastapi import status
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser
from app.core.exceptions import AppException
from app.core.permissions import DocumentPermissionAction, DocumentPrincipalType, normalize_role_codes
from app.core.security import UserRole
from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.models.user import User


@dataclass(frozen=True, slots=True)
class DocumentAccessContext:
    """文档访问上下文。

    它是 RAG 权限过滤的最小输入：用户是谁、在哪个企业、哪个部门、拥有哪些角色。
    """

    user_id: int | None = None
    username: str | None = None
    enterprise_id: int | None = None
    department_id: int | None = None
    role_codes: tuple[str, ...] = field(default_factory=tuple)
    is_admin: bool = False

    @property
    def has_user_identity(self) -> bool:
        return self.user_id is not None or bool(self.username)


def build_document_access_context(
    db: Session,
    current_user: AuthenticatedUser | None,
) -> DocumentAccessContext | None:
    """把请求身份转换为文档访问上下文。

    如果未传 current_user，表示内部服务调用，保持旧逻辑不做权限过滤。
    """
    if current_user is None:
        return None

    role_codes = set(current_user.effective_role_codes)
    user_id = current_user.user_id
    enterprise_id = current_user.enterprise_id
    department_id = current_user.department_id
    is_admin = current_user.is_admin or current_user.role == UserRole.ADMIN

    if user_id is not None and table_exists(db, "users"):
        try:
            user = db.get(User, user_id)
        except Exception:
            # 兼容未执行最新迁移的本地环境：仍使用请求头里的身份信息，不让权限增强阻断旧演示。
            db.rollback()
            user = None
        if user is not None:
            enterprise_id = enterprise_id or user.enterprise_id
            department_id = department_id or user.department_id
            is_admin = is_admin or bool(user.is_admin)
            if user.role:
                role_codes.add(str(getattr(user.role, "value", user.role)))
            if table_exists(db, "user_roles") and table_exists(db, "roles"):
                for role_link in user.role_links:
                    if role_link.role and role_link.role.code:
                        role_codes.add(role_link.role.code)

    return DocumentAccessContext(
        user_id=user_id,
        username=current_user.username,
        enterprise_id=enterprise_id,
        department_id=department_id,
        role_codes=normalize_role_codes(role_codes),
        is_admin=is_admin,
    )


def can_access_document(db: Session, document: Document, context: DocumentAccessContext | None) -> bool:
    """判断当前上下文是否可访问文档。"""
    if context is None or context.is_admin or UserRole.ADMIN.value in context.role_codes:
        return True
    if document.deleted_at is not None:
        return False
    if context.user_id is not None and document.uploaded_by == context.user_id:
        return True
    if not table_exists(db, "document_permissions"):
        return True

    permissions = db.scalars(
        select(DocumentPermission).where(DocumentPermission.document_id == document.id)
    ).all()
    if not permissions:
        # 兼容本地 demo 和历史数据：没有显式权限记录的文档视为企业内部公开。
        return True

    for permission in permissions:
        if permission.permission not in {DocumentPermissionAction.VIEW.value, DocumentPermissionAction.MANAGE.value}:
            continue
        if not _enterprise_matches(permission.enterprise_id, context.enterprise_id):
            continue
        if _principal_matches(permission, context):
            return True
    return False


def ensure_document_access(db: Session, document: Document, context: DocumentAccessContext | None) -> None:
    """无权限时抛出 403。"""
    if not can_access_document(db, document, context):
        raise AppException("无权访问该知识库文档。", status_code=status.HTTP_403_FORBIDDEN)


def create_default_document_permissions(
    db: Session,
    document: Document,
    context: DocumentAccessContext | None,
    *,
    commit: bool = False,
) -> None:
    """上传文档后创建默认权限。

    默认策略贴近企业实际：上传人可管理；上传人所在部门可查看；没有身份时保持旧演示公开。
    """
    if context is None or not context.has_user_identity or not table_exists(db, "document_permissions"):
        return

    records: list[DocumentPermission] = []
    if context.user_id is not None:
        records.append(
            DocumentPermission(
                document_id=document.id,
                enterprise_id=context.enterprise_id,
                principal_type=DocumentPrincipalType.USER.value,
                principal_id=str(context.user_id),
                permission=DocumentPermissionAction.MANAGE.value,
                created_by=context.user_id,
            )
        )
    if context.department_id is not None:
        records.append(
            DocumentPermission(
                document_id=document.id,
                enterprise_id=context.enterprise_id,
                principal_type=DocumentPrincipalType.DEPARTMENT.value,
                principal_id=str(context.department_id),
                permission=DocumentPermissionAction.VIEW.value,
                created_by=context.user_id,
            )
        )

    if not records:
        return

    for record in records:
        existing = db.scalar(
            select(DocumentPermission)
            .where(DocumentPermission.document_id == record.document_id)
            .where(DocumentPermission.principal_type == record.principal_type)
            .where(DocumentPermission.principal_id == record.principal_id)
            .where(DocumentPermission.permission == record.permission)
            .limit(1)
        )
        if existing is None:
            db.add(record)
    if commit:
        db.commit()
    else:
        db.flush()


def build_document_permission_sql(context: DocumentAccessContext | None) -> tuple[str, dict[str, Any]]:
    """构造 RAG 检索使用的文档权限 SQL 片段。

    返回的 SQL 依赖 documents 表别名 d。
    """
    if context is None or context.is_admin or UserRole.ADMIN.value in context.role_codes:
        return "", {}

    params: dict[str, Any] = {}
    principal_conditions = ["dp.principal_type = 'all'"]

    if context.user_id is not None:
        params["permission_user_id"] = str(context.user_id)
        principal_conditions.append(
            "(dp.principal_type = 'user' AND dp.principal_id = :permission_user_id)"
        )

    if context.department_id is not None:
        params["permission_department_id"] = str(context.department_id)
        principal_conditions.append(
            "(dp.principal_type = 'department' AND dp.principal_id = :permission_department_id)"
        )

    role_placeholders: list[str] = []
    for index, role_code in enumerate(context.role_codes):
        key = f"permission_role_{index}"
        params[key] = role_code
        role_placeholders.append(f":{key}")
    if role_placeholders:
        principal_conditions.append(
            f"(dp.principal_type = 'role' AND dp.principal_id IN ({', '.join(role_placeholders)}))"
        )

    if context.enterprise_id is None:
        enterprise_clause = "dp.enterprise_id IS NULL"
    else:
        params["permission_enterprise_id"] = context.enterprise_id
        enterprise_clause = "(dp.enterprise_id IS NULL OR dp.enterprise_id = :permission_enterprise_id)"

    uploader_clause = ""
    if context.user_id is not None:
        params["permission_uploader_id"] = context.user_id
        uploader_clause = "d.uploaded_by = :permission_uploader_id OR "

    principal_clause = " OR ".join(principal_conditions)
    sql = f"""
      AND (
        {uploader_clause}
        NOT EXISTS (
          SELECT 1 FROM document_permissions dp_none
          WHERE dp_none.document_id = d.id
        )
        OR EXISTS (
          SELECT 1 FROM document_permissions dp
          WHERE dp.document_id = d.id
            AND dp.permission IN ('view', 'manage')
            AND {enterprise_clause}
            AND ({principal_clause})
        )
      )
    """
    return sql, params


def table_exists(db: Session, table_name: str) -> bool:
    """判断表是否存在；测试 Mock 或未迁移环境下返回 False。"""
    try:
        return bool(inspect(db.connection()).has_table(table_name))
    except Exception:
        return False


def _enterprise_matches(permission_enterprise_id: int | None, context_enterprise_id: int | None) -> bool:
    if permission_enterprise_id is None:
        return True
    if context_enterprise_id is None:
        return False
    return permission_enterprise_id == context_enterprise_id


def _principal_matches(permission: DocumentPermission, context: DocumentAccessContext) -> bool:
    if permission.principal_type == DocumentPrincipalType.ALL.value:
        return True
    if permission.principal_type == DocumentPrincipalType.USER.value:
        return context.user_id is not None and permission.principal_id == str(context.user_id)
    if permission.principal_type == DocumentPrincipalType.DEPARTMENT.value:
        return context.department_id is not None and permission.principal_id == str(context.department_id)
    if permission.principal_type == DocumentPrincipalType.ROLE.value:
        return permission.principal_id in context.role_codes
    return False
