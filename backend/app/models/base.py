from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.utils.time_utils import utc_now


class TimestampMixin:
    """通用创建时间字段。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        comment="创建时间",
    )


class UserRole(StrEnum):
    """用户角色。"""

    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class EnterpriseStatus(StrEnum):
    """企业/租户状态。"""

    ACTIVE = "active"
    DISABLED = "disabled"


class DepartmentStatus(StrEnum):
    """部门状态。"""

    ACTIVE = "active"
    DISABLED = "disabled"


class UserStatus(StrEnum):
    """用户账号状态。"""

    ACTIVE = "active"
    DISABLED = "disabled"
    LEFT = "left"
    LOCKED = "locked"


class IntegrationConfigStatus(StrEnum):
    """企业集成配置状态。"""

    ACTIVE = "active"
    DISABLED = "disabled"


class IntegrationEventStatus(StrEnum):
    """外部回调事件处理状态。"""

    RECEIVED = "received"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    DUPLICATED = "duplicated"


class NotificationDeliveryStatus(StrEnum):
    """通知发送状态。"""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class SLAStatus(StrEnum):
    """SLA 实例状态。"""

    ACTIVE = "active"
    PAUSED = "paused"
    BREACHED = "breached"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    """任务、工单等业务对象的优先级。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(StrEnum):
    """任务状态。"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TicketStatus(StrEnum):
    """工单状态。"""

    OPEN = "open"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    CLOSED = "closed"


class PurchaseStatus(StrEnum):
    """采购申请状态。"""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalStatus(StrEnum):
    """审批状态。"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTION_FAILED = "execution_failed"


class ApprovalTemplateStatus(StrEnum):
    """审批模板状态。"""

    ENABLED = "enabled"
    DISABLED = "disabled"


class ApprovalStepMode(StrEnum):
    """审批步骤处理模式。"""

    ANY = "any"
    ALL = "all"


class ApproverType(StrEnum):
    """审批人选择方式。"""

    USER = "user"
    ROLE = "role"
    DEPARTMENT_MANAGER = "department_manager"
    EXPRESSION = "expression"


class ApprovalInstanceStatus(StrEnum):
    """审批实例状态。"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    TRANSFERRED = "transferred"
    ESCALATED = "escalated"


class ApprovalStepStatus(StrEnum):
    """审批实例步骤状态。"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TRANSFERRED = "transferred"
    SKIPPED = "skipped"
    ESCALATED = "escalated"


class ApprovalActionType(StrEnum):
    """审批动作类型。"""

    APPROVE = "approve"
    REJECT = "reject"
    TRANSFER = "transfer"
    WITHDRAW = "withdraw"
    COMMENT = "comment"
    ESCALATE = "escalate"


class AuditStatus(StrEnum):
    """审计记录中的执行状态。"""

    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
