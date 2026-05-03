"""数据库模型包。

导入本包可以让 Alembic 或初始化脚本发现全部模型。
"""

from app.models.audit_log import AuditLog
from app.models.approval import Approval
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.purchase_request import PurchaseRequest
from app.models.task import Task
from app.models.ticket import Ticket
from app.models.user import User

__all__ = [
    "AuditLog",
    "Approval",
    "Document",
    "DocumentChunk",
    "PurchaseRequest",
    "Task",
    "Ticket",
    "User",
]

