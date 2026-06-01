import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser
from app.core.database import Base
from app.core.exceptions import AppException
from app.core.security import UserRole as RequestUserRole
from app.models.base import UserRole
from app.models.department import Department
from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.models.enterprise import Enterprise
from app.models.user import User
from app.services.permission_service import (
    build_document_access_context,
    build_document_permission_sql,
    can_access_document,
    ensure_document_access,
)


class DocumentPermissionTest(unittest.TestCase):
    """文档权限与 RAG 数据边界测试。"""

    def setUp(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(
            engine,
            tables=[
                Enterprise.__table__,
                Department.__table__,
                User.__table__,
                Document.__table__,
                DocumentPermission.__table__,
            ],
        )
        self.session = Session(engine)
        self.session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        self.session.add(Department(id=10, enterprise_id=1, name="质量部"))
        self.session.add(Department(id=20, enterprise_id=1, name="采购部"))
        self.session.add(
            User(
                id=1,
                username="quality_user",
                role=UserRole.EMPLOYEE,
                enterprise_id=1,
                department_id=10,
            )
        )
        self.session.add(
            User(
                id=2,
                username="purchase_user",
                role=UserRole.EMPLOYEE,
                enterprise_id=1,
                department_id=20,
            )
        )
        self.session.add(
            User(
                id=99,
                username="admin_user",
                role=UserRole.ADMIN,
                enterprise_id=1,
                is_admin=True,
            )
        )
        self.session.add(
            Document(
                id=100,
                filename="质量异常处理流程.md",
                title="质量异常处理流程",
                category="质量流程",
                uploaded_by=1,
            )
        )
        self.session.add(
            Document(
                id=101,
                filename="公开制度.md",
                title="公开制度",
                category="制度",
            )
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()

    def test_document_permission_allows_matching_department(self) -> None:
        """部门授权后，只有同部门用户可访问。"""
        self.session.add(
            DocumentPermission(
                document_id=100,
                enterprise_id=1,
                principal_type="department",
                principal_id="10",
                permission="view",
            )
        )
        self.session.commit()

        quality_context = build_document_access_context(
            self.session,
            AuthenticatedUser(user_id=1, role=RequestUserRole.EMPLOYEE, enterprise_id=1, department_id=10),
        )
        purchase_context = build_document_access_context(
            self.session,
            AuthenticatedUser(user_id=2, role=RequestUserRole.EMPLOYEE, enterprise_id=1, department_id=20),
        )
        document = self.session.get(Document, 100)

        self.assertTrue(can_access_document(self.session, document, quality_context))
        self.assertFalse(can_access_document(self.session, document, purchase_context))
        with self.assertRaises(AppException):
            ensure_document_access(self.session, document, purchase_context)

    def test_document_without_explicit_permission_stays_compatible(self) -> None:
        """历史 demo 文档没有权限记录时，仍按企业内部公开处理。"""
        context = build_document_access_context(
            self.session,
            AuthenticatedUser(user_id=2, role=RequestUserRole.EMPLOYEE, enterprise_id=1, department_id=20),
        )
        document = self.session.get(Document, 101)

        self.assertTrue(can_access_document(self.session, document, context))

    def test_admin_can_access_restricted_document(self) -> None:
        """管理员可访问显式授权文档。"""
        self.session.add(
            DocumentPermission(
                document_id=100,
                enterprise_id=1,
                principal_type="department",
                principal_id="10",
                permission="view",
            )
        )
        self.session.commit()

        admin_context = build_document_access_context(
            self.session,
            AuthenticatedUser(user_id=99, role=RequestUserRole.ADMIN, enterprise_id=1, is_admin=True),
        )
        document = self.session.get(Document, 100)

        self.assertTrue(can_access_document(self.session, document, admin_context))

    def test_permission_sql_contains_rag_filters(self) -> None:
        """RAG 向量检索 SQL 必须带文档权限过滤条件。"""
        context = build_document_access_context(
            self.session,
            AuthenticatedUser(user_id=2, role=RequestUserRole.EMPLOYEE, enterprise_id=1, department_id=20),
        )

        sql, params = build_document_permission_sql(context)

        self.assertIn("document_permissions", sql)
        self.assertIn("dp.principal_type = 'department'", sql)
        self.assertEqual(params["permission_department_id"], "20")


if __name__ == "__main__":
    unittest.main()
