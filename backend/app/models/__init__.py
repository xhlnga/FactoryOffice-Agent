"""数据库模型包。

导入本包可以让 Alembic 或初始化脚本发现全部模型。
"""

from app.models.audit_log import AuditLog
from app.models.approval_action import ApprovalAction
from app.models.approval_instance import ApprovalInstance
from app.models.approval_instance_step import ApprovalInstanceStep
from app.models.approval_step import ApprovalStep
from app.models.approval_template import ApprovalTemplate
from app.models.approval import Approval
from app.models.department import Department
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_permission import DocumentPermission
from app.models.enterprise import Enterprise
from app.models.external_id_mapping import ExternalIdMapping
from app.models.idempotency_key import IdempotencyKey
from app.models.integration_config import IntegrationConfig
from app.models.integration_event import IntegrationEvent
from app.models.notification_delivery import NotificationDelivery
from app.models.purchase_request import PurchaseRequest
from app.models.role import Role
from app.models.sla import SLAInstance, SLAPolicyModel
from app.models.task import Task
from app.models.ticket import Ticket
from app.models.user import User
from app.models.user_role import UserRoleBinding

__all__ = [
    "AuditLog",
    "Approval",
    "ApprovalAction",
    "ApprovalInstance",
    "ApprovalInstanceStep",
    "ApprovalStep",
    "ApprovalTemplate",
    "Department",
    "Document",
    "DocumentChunk",
    "DocumentPermission",
    "Enterprise",
    "ExternalIdMapping",
    "IdempotencyKey",
    "IntegrationConfig",
    "IntegrationEvent",
    "NotificationDelivery",
    "PurchaseRequest",
    "Role",
    "SLAInstance",
    "SLAPolicyModel",
    "Task",
    "Ticket",
    "User",
    "UserRoleBinding",
]
