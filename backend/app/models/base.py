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


class AuditStatus(StrEnum):
    """审计记录中的执行状态。"""

    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
