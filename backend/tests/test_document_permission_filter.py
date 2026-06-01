from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.permissions import DocumentPermissionAction, DocumentPrincipalType
from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.models.enterprise import Enterprise
from app.models.user import User
from app.services.permission_service import DocumentAccessContext, can_access_document


def test_document_permission_blocks_other_department() -> None:
    """有显式部门权限时，其他部门用户不能访问文档。"""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Enterprise.__table__, User.__table__, Document.__table__, DocumentPermission.__table__])
    with Session(engine) as session:
        session.add(Enterprise(id=1, name="测试制造企业", code="test_factory"))
        document = Document(id=1, filename="采购制度.md", title="采购制度", category="制度")
        session.add(document)
        session.add(
            DocumentPermission(
                document_id=1,
                enterprise_id=1,
                principal_type=DocumentPrincipalType.DEPARTMENT.value,
                principal_id="10",
                permission=DocumentPermissionAction.VIEW.value,
            )
        )
        session.commit()

        allowed = DocumentAccessContext(enterprise_id=1, department_id=10)
        denied = DocumentAccessContext(enterprise_id=1, department_id=20)

        assert can_access_document(session, document, allowed) is True
        assert can_access_document(session, document, denied) is False

